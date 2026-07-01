import os
import json
import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None


import asyncio
from google.api_core import exceptions

def get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        _model = genai.GenerativeModel("gemini-3.1-flash-lite")
    return _model


async def _safe_generate(model, prompt, max_retries=3):
    """Wraps Gemini API calls with rate-limit retry logic."""
    for attempt in range(max_retries):
        try:
            return await model.generate_content_async(prompt)
        except exceptions.ResourceExhausted as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = 35 + (attempt * 10)
            logger.warning(f"Gemini Rate Limit (429) hit. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                if attempt == max_retries - 1:
                    raise e
                wait_time = 35 + (attempt * 10)
                logger.warning(f"Gemini Rate Limit hit. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                await asyncio.sleep(wait_time)
            else:
                raise e


async def parse_ingredients_from_text(raw_text: str) -> List[str]:
    """
    Use Gemini to parse raw OCR/pasted text into a clean list of ingredient names.
    """
    model = get_model()
    prompt = f"""You are a food label parsing expert.
Extract only the ingredient names from the following text.
Return a JSON array of ingredient name strings only — no quantities, no percentages, no extra text.
If the text does not contain ingredients, return an empty array [].

Raw text:
{raw_text}

Respond with ONLY a valid JSON array, example: ["Water", "Sugar", "Salt"]"""

    response = await _safe_generate(model, prompt)
    raw = response.text.strip()
    # Clean markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        ingredients = json.loads(raw)
        return [str(i).strip() for i in ingredients if i]
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Gemini ingredient response: {raw}")
        return []


async def parse_ingredient_from_web(
    ingredient: str, tavily_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Use Gemini to extract structured safety data from Tavily search results.
    """
    model = get_model()
    results_text = "\n\n".join(
        [f"Title: {r.get('title','')}\nContent: {r.get('content','')[:500]}"
         for r in tavily_results[:3]]
    )
    prompt = f"""You are a food safety expert. Based on the web search results below,
extract structured safety information for the food ingredient: "{ingredient}".

Search results:
{results_text}

Return a JSON object with exactly these fields:
{{
  "name": "canonical name",
  "aliases": ["alias1", "alias2"],
  "safety_rating": "safe|caution|harmful|other",
  "health_impact": "concise description of health effects",
  "conditions_affected": ["condition1", "condition2"],
  "banned_in": ["country1"],
  "daily_limit_mg": null or number
}}

If data is insufficient, use "other" for safety_rating and empty arrays.
Respond with ONLY the JSON object."""

    response = await _safe_generate(model, prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "name": ingredient,
            "aliases": [],
            "safety_rating": "other",
            "health_impact": "Unable to determine from available data.",
            "conditions_affected": [],
            "banned_in": [],
            "daily_limit_mg": None,
        }


async def generate_analysis_report(
    ingredients: List[str],
    research_results: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
    product_veg_status: str = "veg",
    processing_level: str = "unknown",
    feedback: Optional[str] = None,
    retry_count: int = 0,
) -> Dict[str, Any]:
    """
    Generate a personalized food safety report using Gemini.
    Adapts language to expertise level and prioritizes warnings for user conditions.
    """
    model = get_model()

    expertise = user_profile.get("expertise_level", "beginner")
    conditions = user_profile.get("health_conditions", [])
    allergies = user_profile.get("allergies", [])

    # Build condition-specific guidance
    condition_notes = []
    if "diabetes" in [c.lower() for c in conditions]:
        condition_notes.append(
            "Flag all hidden sugars (HFCS, maltodextrin, dextrose, glucose syrup, "
            "corn syrup, fructose, lactose, sucrose, treacle, barley malt)."
        )
    if any(c.lower() in ["hypertension", "high blood pressure", "bp"] for c in conditions):
        condition_notes.append(
            "Flag all sodium sources (MSG, sodium benzoate, sodium nitrite, "
            "disodium phosphate, sodium bicarbonate, salt)."
        )
    if "celiac" in [c.lower() for c in conditions]:
        condition_notes.append("Flag any gluten-containing ingredients or derivatives.")
    if "pku" in [c.lower() for c in conditions]:
        condition_notes.append(
            "Strongly flag aspartame and any phenylalanine-containing ingredients — DANGEROUS for PKU."
        )

    dietary_pref = user_profile.get("dietary_preference", "").lower()
    is_user_veg = "veg" in dietary_pref or "vegan" in dietary_pref or "vegetarian" in dietary_pref
    if is_user_veg and product_veg_status in ["non-veg", "veg" if "vegan" in dietary_pref else ""]:
        condition_notes.append(
            f"CRITICAL WARNING: The user is {dietary_pref} but the product contains non-compliant ingredients! You MUST add a critical warning in top_warnings and clearly state this in the personalized_summary."
        )

    language_instruction = (
        "Use plain, everyday language. Avoid technical jargon. "
        "Explain what each ingredient IS and WHY it matters in simple terms."
        if expertise == "beginner"
        else "Use precise scientific/technical language. Include E-numbers, "
             "biochemical effects, and regulatory classifications where relevant."
    )

    feedback_section = ""
    if feedback and retry_count > 0:
        feedback_section = f"\n\nPREVIOUS VALIDATION FEEDBACK (must address):\n{feedback}"

    research_json = json.dumps(research_results, indent=2)
    allergies_str = ", ".join(allergies) if allergies else "None"
    conditions_str = ", ".join(conditions) if conditions else "None"
    condition_guidance = "\n".join(condition_notes) if condition_notes else "No special conditions."

    prompt = f"""You are an expert food safety analyst providing a personalized report.
THINKING LEVEL: MEDIUM. Reason carefully to adapt to the user's specific health profile.

USER PROFILE:
- Health Conditions: {conditions_str}
- Allergies: {allergies_str}
- Expertise Level: {expertise}

LANGUAGE STYLE: {language_instruction}

CONDITION-SPECIFIC GUIDANCE:
{condition_guidance}

INGREDIENT RESEARCH DATA:
{research_json}
{feedback_section}

Generate a comprehensive, personalized food safety report. Return ONLY a valid JSON object:
{{
  "ingredients": [
    {{
      "name": "ingredient name",
      "safety_rating": "safe|caution|harmful|other",
      "explanation": "explanation in the appropriate language style",
      "personalized_note": "specific note for THIS user's conditions/allergies, or null",
      "banned_in": ["country"],
      "daily_limit_mg": null or number,
      "source": "qdrant|tavily|llm",
      "is_veg": true/false,
      "is_vegan": true/false,
      "ingredient_source": "animal|plant|synthetic|mineral",
      "processing_level": "ultra_processed|processed|minimally_processed|raw"
    }}
  ],
  "summary": {{
    "safe_count": 0,
    "caution_count": 0,
    "harmful_count": 0,
    "other_count": 0,
    "health_score": 0,
    "top_warnings": ["warning1", "warning2"],
    "allergen_alerts": ["allergen found"],
    "personalized_summary": "2-3 sentence summary specific to this user's health profile",
    "has_disclaimer": false,
    "product_veg_status": "{product_veg_status}",
    "processing_level": "{processing_level}"
  }},
  "disclaimer": null,
  "expertise_level": "{expertise}"
}}

SCORING RULES:
- Start at 100. Each harmful ingredient: -20. Each caution: -8. Each other: -3.
- Minimum score: 0. Never exceed 100.
- If 3+ harmful ingredients, score MUST be below 40.

Ensure ALL {len(ingredients)} ingredients are covered. Flag ALL user allergens if present.
Respond with ONLY the JSON object, no markdown."""

    response = await _safe_generate(model, prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    report = json.loads(raw)
    return report


async def check_relevance(text: str) -> tuple[bool, str]:
    """
    Relevance Gate: Ensure the input is actually a food product ingredient list.
    """
    model = get_model()
    prompt = f"""You are a relevance filter for a food label analyzer.
Determine if the following text represents a valid list of food ingredients (or a single food ingredient).
If it is clearly NOT food (e.g., shampoo ingredients, random code, a poem, toxic chemicals not used in food), reject it.

Text:
{text}

Respond with ONLY a JSON object:
{{
  "is_food": true/false,
  "reason": "Brief explanation if false, otherwise empty string"
}}"""
    response = await _safe_generate(model, prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw.strip())
        return data.get("is_food", True), data.get("reason", "")
    except Exception as e:
        logger.error(f"Relevance check failed: {e}")
        return True, ""


async def validate_report_with_critic(
    ingredients: List[str],
    report: Dict[str, Any],
    user_profile: Dict[str, Any]
) -> tuple[bool, Dict[str, bool], List[str]]:
    """
    Use Gemini 3.1 Flash-Lite (low thinking) to validate 6 Critic gates.
    """
    model = get_model()
    
    ingredients_str = ", ".join(ingredients)
    allergies_str = ", ".join(user_profile.get("allergies", []))
    conditions_str = ", ".join(user_profile.get("health_conditions", []))
    report_json = json.dumps(report, indent=2)
    
    prompt = f"""You are the Critic Agent. Your job is to strictly validate a food safety report.
THINKING LEVEL: LOW. Perform these 6 simple validation checks quickly and strictly.

INPUTS:
Ingredients: {ingredients_str}
User Allergies: {allergies_str}
User Conditions: {conditions_str}

REPORT TO VALIDATE:
{report_json}

Validate the following 6 gates (yes/no):
1. Completeness: Does the report address every single ingredient in the input list?
2. Allergen Check: Are all user allergies clearly flagged if they match any ingredient?
3. Score Consistency: If there are 3+ harmful ingredients, is the health_score < 40?
4. Personalization: Does the summary or personalized_note explicitly mention/address the user's health conditions?
5. Relevance: Is this report actually evaluating food? (Confirm it's not analyzing shampoo, etc.)
6. Clarity: Is the report free of overly complex, unexplained scientific jargon (suitable for beginner)?
7. Dietary Compliance Check: If the user's profile indicates they are vegetarian or vegan, AND the product_veg_status or any ingredient is non-veg/non-vegan, is there a CRITICAL WARNING in the top_warnings or personalized_summary about this? (If user is not veg/vegan, or product is compliant, return true).

Respond with ONLY a JSON object exactly like this:
{{
  "gates": {{
    "completeness": true/false,
    "allergen_check": true/false,
    "score_consistency": true/false,
    "personalization": true/false,
    "relevance": true/false,
    "clarity": true/false,
    "dietary_compliance": true/false
  }},
  "failures": ["If any gate is false, list the specific reason why it failed here"]
}}"""

    response = await _safe_generate(model, prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw.strip())
        gates = data.get("gates", {})
        failures = data.get("failures", [])
        passed = all(gates.values())
        return passed, gates, failures
    except Exception as e:
        logger.error(f"Critic validation failed: {e}")
        return False, {}, ["Failed to parse Critic response."]
