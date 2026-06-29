import os
import json
import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        _model = genai.GenerativeModel("gemini-3.1-flash-lite")
    return _model


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

    response = model.generate_content(prompt)
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
  "safety_rating": "safe|caution|harmful|unknown",
  "health_impact": "concise description of health effects",
  "conditions_affected": ["condition1", "condition2"],
  "banned_in": ["country1"],
  "daily_limit_mg": null or number
}}

If data is insufficient, use "unknown" for safety_rating and empty arrays.
Respond with ONLY the JSON object."""

    response = model.generate_content(prompt)
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
            "safety_rating": "unknown",
            "health_impact": "Unable to determine from available data.",
            "conditions_affected": [],
            "banned_in": [],
            "daily_limit_mg": None,
        }


async def generate_analysis_report(
    ingredients: List[str],
    research_results: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
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
      "safety_rating": "safe|caution|harmful|unknown",
      "explanation": "explanation in the appropriate language style",
      "personalized_note": "specific note for THIS user's conditions/allergies, or null",
      "banned_in": ["country"],
      "daily_limit_mg": null or number,
      "source": "qdrant|tavily|llm"
    }}
  ],
  "summary": {{
    "safe_count": 0,
    "caution_count": 0,
    "harmful_count": 0,
    "unknown_count": 0,
    "health_score": 0,
    "top_warnings": ["warning1", "warning2"],
    "allergen_alerts": ["allergen found"],
    "personalized_summary": "2-3 sentence summary specific to this user's health profile",
    "has_disclaimer": false
  }},
  "disclaimer": null,
  "expertise_level": "{expertise}"
}}

SCORING RULES:
- Start at 100. Each harmful ingredient: -20. Each caution: -8. Each unknown: -3.
- Minimum score: 0. Never exceed 100.
- If 3+ harmful ingredients, score MUST be below 40.

Ensure ALL {len(ingredients)} ingredients are covered. Flag ALL user allergens if present.
Respond with ONLY the JSON object, no markdown."""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    report = json.loads(raw)
    return report
