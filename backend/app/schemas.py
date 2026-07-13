from datetime import datetime
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"


class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    role: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: EmailStr
    role: str


class UserProfileOut(BaseModel):
    id: int
    email: EmailStr
    role: str


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str


class DataSourceOut(BaseModel):
    id: int
    file_path: str
    display_name: str
    source_type: str
    owner_user_id: int | None
    visibility: str
    metadata_json: str
    status: str
    progress_percent: int
    stage: str
    telemetry_json: str
    version: int
    is_deleted: bool
    task_id: str
    last_error: str
    updated_at: datetime


class RetryIngestRequest(BaseModel):
    datasource_id: int


class Citation(BaseModel):
    source: str
    chunk_id: str


class FeedbackRequest(BaseModel):
    message_id: int
    rating: int
    comment: str = ""


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations_json: str
    metadata_json: str
    created_at: datetime


class SessionOut(BaseModel):
    id: int
    title: str
    updated_at: datetime


class EvalResult(BaseModel):
    total: int
    answer_relevancy: float
    faithfulness: float
    context_precision: float
