from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class FrequencyEnum(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class ThresholdEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class SourceEnum(str, Enum):
    user = "user"
    arxiv = "arxiv"

class ModeEnum(str, Enum):
    abstract = "abstract"
    full = "full"

class TypeEnum(str, Enum):
    abstract = "abstract"
    section = "section"

class StatusEnum(str, Enum):
    sent = "sent"
    failed = "failed"

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    created_at: datetime

# Profile Schemas
class ProfileCreate(BaseModel):
    user_id: int
    name: str
    keywords: List[str]
    email_notify: bool = True
    frequency: FrequencyEnum
    threshold: ThresholdEnum = ThresholdEnum.medium
    top_x: Optional[int] = None

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    email_notify: Optional[bool] = None
    frequency: Optional[FrequencyEnum] = None
    threshold: Optional[ThresholdEnum] = None
    top_x: Optional[int] = None

class ProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    keywords: List[str]
    email_notify: bool
    frequency: str
    threshold: str
    top_x: Optional[int]
    created_at: datetime
    updated_at: datetime

# Corpus Schemas
class CorpusCreate(BaseModel):
    user_id: int
    name: str
    description: Optional[str] = None

class CorpusUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CorpusResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    created_at: datetime

# ProfileCorpus Schemas
class ProfileCorpusCreate(BaseModel):
    profile_id: int
    corpus_id: int

class ProfileCorpusResponse(BaseModel):
    profile_id: int
    corpus_id: int

# Paper Schemas
class PaperCreate(BaseModel):
    corpus_id: int
    arxiv_id: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    metadata: Optional[dict] = None
    file_path: Optional[str] = None
    source: SourceEnum

class PaperUpdate(BaseModel):
    arxiv_id: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    metadata: Optional[dict] = None
    file_path: Optional[str] = None
    source: Optional[SourceEnum] = None

class PaperResponse(BaseModel):
    id: int
    corpus_id: int
    arxiv_id: Optional[str]
    title: str
    abstract: Optional[str]
    metadata: Optional[dict]
    file_path: Optional[str]
    source: str
    created_at: datetime

# Section Schemas
class SectionCreate(BaseModel):
    paper_id: int
    header: Optional[str] = None
    text: Optional[str] = None

class SectionUpdate(BaseModel):
    header: Optional[str] = None
    text: Optional[str] = None

class SectionResponse(BaseModel):
    id: int
    paper_id: int
    header: Optional[str]
    text: Optional[str]
    created_at: datetime

# Summary Schemas
class SummaryCreate(BaseModel):
    paper_id: int
    mode: ModeEnum
    summary_text: Optional[str] = None
    summarizer: Optional[str] = None

class SummaryUpdate(BaseModel):
    summary_text: Optional[str] = None
    summarizer: Optional[str] = None

class SummaryResponse(BaseModel):
    id: int
    paper_id: int
    mode: str
    summary_text: Optional[str]
    summarizer: Optional[str]
    created_at: datetime

# Embedding Schemas
class EmbeddingCreate(BaseModel):
    paper_id: int
    section_id: Optional[int] = None
    embedding: List[float]
    type: TypeEnum
    model_name: str

class EmbeddingUpdate(BaseModel):
    embedding: Optional[List[float]] = None

class EmbeddingResponse(BaseModel):
    id: int
    paper_id: int
    section_id: Optional[int]
    type: str
    model_name: str
    created_at: datetime

# RecommendationRun Schemas
class RecommendationRunCreate(BaseModel):
    profile_id: int
    user_id: int
    user_corpus_id: int
    ref_corpus_id: int
    threshold: Optional[str] = None
    method: Optional[str] = None

class RecommendationRunResponse(BaseModel):
    id: int
    profile_id: int
    user_id: int
    user_corpus_id: int
    ref_corpus_id: int
    threshold: Optional[str]
    method: Optional[str]
    created_at: datetime

# Recommendation Schemas
class RecommendationCreate(BaseModel):
    run_id: int
    paper_id: int
    score: float
    rank: int
    summary: Optional[str] = None

class RecommendationUpdate(BaseModel):
    score: Optional[float] = None
    rank: Optional[int] = None
    summary: Optional[str] = None

class RecommendationResponse(BaseModel):
    id: int
    run_id: int
    paper_id: int
    score: float
    rank: int
    summary: Optional[str]
    created_at: datetime

# ProfileRecommendation Schemas
class ProfileRecommendationCreate(BaseModel):
    profile_id: int
    recommendation_id: int

class ProfileRecommendationResponse(BaseModel):
    id: int
    profile_id: int
    recommendation_id: int
    created_at: datetime

# EmailLog Schemas
class EmailLogCreate(BaseModel):
    user_id: int
    profile_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    status: StatusEnum = StatusEnum.sent

class EmailLogResponse(BaseModel):
    id: int
    user_id: int
    profile_id: Optional[int]
    subject: Optional[str]
    body: Optional[str]
    sent_at: datetime
    status: str
