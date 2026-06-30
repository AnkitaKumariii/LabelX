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
    safety_rating: str     # "safe" | "caution" | "harmful" | "unknown"
    health_impact: str
    conditions_affected: List[str]
    banned_in: List[str]
    daily_limit_mg: Optional[float]
    source: str            # "qdrant" | "tavily" | "llm"
    confidence: float


class IngredientReport(TypedDict, total=False):
    name: str
    safety_rating: str
    explanation: str
    personalized_note: Optional[str]
    banned_in: List[str]
    daily_limit_mg: Optional[float]
    source: str


class ReportSummary(TypedDict, total=False):
    safe_count: int
    caution_count: int
    harmful_count: int
    unknown_count: int
    health_score: int
    top_warnings: List[str]
    allergen_alerts: List[str]
    personalized_summary: str
    has_disclaimer: bool


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
