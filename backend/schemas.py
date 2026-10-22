from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
import datetime as dt

class UserBase(BaseModel):
    username: str
    role: str

class UserOut(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RequestCreate(BaseModel):
    submitter_id: Optional[int] = None
    type: str
    expense_amount: Optional[float] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[dt.date] = None
    category: Optional[str] = None
    description: Optional[str] = None

class RequestUpdate(BaseModel):
    expense_amount: Optional[float] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[dt.date] = None
    category: Optional[str] = None
    description: Optional[str] = None

class RequestOut(BaseModel):
    id: int
    submitter_id: int
    assigned_reviewer_id: Optional[int]
    type: str
    status: str
    expense_amount: Optional[float]
    merchant_name: Optional[str] = None
    expense_date: Optional[dt.date] = None
    category: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MissingField(BaseModel):
    field_name: str
    count: int
    request_ids: List[int]

class DashboardOut(BaseModel):
    pending_count: int
    approved_count: int
    rejected_count: int
    correction_required_count: int
    frequent_missing_fields: List[MissingField]
    average_review_turnaround_hours: Optional[float]

class ReviewAction(BaseModel):
    reviewer_id: Optional[int] = None
    action: str  # approve, reject, request_correction
    reason: Optional[str] = None

class AskQuestion(BaseModel):
    user_id: Optional[int] = None
    question: str


class CorrectionSuggestion(BaseModel):
    field_name: str
    extracted_value: Optional[str] = None
    corrected_value: Optional[str] = None
    evidence: str

class CorrectionAssistanceOut(BaseModel):
    request_id: int
    suggestions: List[CorrectionSuggestion]
    message: str
    model_config = ConfigDict(from_attributes=True)
