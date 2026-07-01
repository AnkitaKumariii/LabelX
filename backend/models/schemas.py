from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid


class UserProfileRequest(BaseModel):
    name: str = Field(..., min_length=1)
    health_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    expertise_level: str = Field(default="beginner", pattern="^(beginner|expert)$")


class UserProfileResponse(BaseModel):
    profile_id: str
    name: str
    health_conditions: List[str]
    allergies: List[str]
    expertise_level: str


class AnalyzeRequest(BaseModel):
    profile_id: str
    ingredients: Optional[List[str]] = Field(default_factory=list)
    raw_text: Optional[str] = None   # for OCR-extracted or pasted text


class IngredientReportItem(BaseModel):
    name: str
    safety_rating: str
    explanation: str
    personalized_note: Optional[str] = None
    banned_in: List[str] = []
    daily_limit_mg: Optional[float] = None
    source: str = "qdrant"
    is_veg: bool = True
    is_vegan: bool = True
    ingredient_source: str = "unknown"
    processing_level: str = "unknown"


class ReportSummary(BaseModel):
    safe_count: int
    caution_count: int
    harmful_count: int
    other_count: int
    health_score: int
    top_warnings: List[str]
    allergen_alerts: List[str]
    personalized_summary: str
    has_disclaimer: bool = False
    product_veg_status: str = "veg"
    processing_level: str = "unknown"


class AnalysisReportResponse(BaseModel):
    analysis_id: str
    profile_id: str
    ingredients: List[IngredientReportItem]
    summary: ReportSummary
    disclaimer: Optional[str] = None
    expertise_level: str


class HistoryItem(BaseModel):
    analysis_id: str
    created_at: str
    health_score: int
    ingredient_count: int
    summary_snippet: str
