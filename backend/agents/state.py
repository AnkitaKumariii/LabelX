from typing import TypedDict, List, Optional, Any, Dict


class UserProfile(TypedDict, total=False):
    profile_id: str
    name: str
    health_conditions: List[str]
    allergies: List[str]
    expertise_level: str   # "beginner" | "expert"


class IngredientResearch(TypedDict, total=False):
    name: str
    aliases: List[str]
    safety_rating: str     # "safe" | "caution" | "harmful" | "other"
    health_impact: str
    conditions_affected: List[str]
    banned_in: List[str]
    daily_limit_mg: Optional[float]
    source: str            # "qdrant" | "tavily" | "llm"
    confidence: float
    is_veg: bool
    is_vegan: bool
    ingredient_source: str # animal/plant/synthetic/mineral
    processing_level: str  # ultra_processed/processed/minimally_processed/raw


class IngredientReport(TypedDict, total=False):
    name: str
    safety_rating: str
    explanation: str
    personalized_note: Optional[str]
    banned_in: List[str]
    daily_limit_mg: Optional[float]
    source: str
    is_veg: bool
    is_vegan: bool
    ingredient_source: str
    processing_level: str


class ReportSummary(TypedDict, total=False):
    safe_count: int
    caution_count: int
    harmful_count: int
    other_count: int
    health_score: int
    top_warnings: List[str]
    allergen_alerts: List[str]
    personalized_summary: str
    has_disclaimer: bool
    product_veg_status: str
    processing_level: str


class AnalysisReport(TypedDict, total=False):
    ingredients: List[IngredientReport]
    summary: ReportSummary
    disclaimer: Optional[str]
    expertise_level: str


class AnalysisState(TypedDict, total=False):
    # Inputs
    ingredients: List[str]
    user_profile: Dict[str, Any]
    
    # Internal State
    invalid_product: bool
    invalid_reason: str
    product_veg_status: str
    non_veg_ingredients: List[Dict[str, str]]
    processing_level: str
    research_results: List[IngredientResearch]
    report: Optional[Dict[str, Any]]
    score: Optional[int]

    # Critic loop
    feedback: Optional[str]
    retry_count: int
    validated: bool

    # SSE streaming
    status_updates: List[Dict[str, Any]]
    event_queue: Any   # asyncio.Queue — not serialized, lives in memory only

    # Error
    error: Optional[str]
