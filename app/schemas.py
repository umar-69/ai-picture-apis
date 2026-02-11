from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any, List
from datetime import datetime

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    metadata: Optional[dict[str, Any]] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: Optional[str] = None
    created_at: Optional[Any] = None
    last_sign_in_at: Optional[Any] = None
    app_metadata: Optional[dict] = None
    user_metadata: Optional[dict] = None

class BusinessProfileBase(BaseModel):
    business_name: str
    theme: Optional[str] = None
    target_audience: Optional[str] = None
    vibes: Optional[str] = None
    logo_url: Optional[str] = None

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileResponse(BusinessProfileBase):
    id: str
    created_at: str

class DatasetBase(BaseModel):
    name: str
    master_prompt: Optional[str] = None

class DatasetCreate(DatasetBase):
    pass

class DatasetResponse(DatasetBase):
    id: str
    user_id: str
    created_at: str

class GenerateImageRequest(BaseModel):
    prompt: str
    style: Optional[str] = None
    image_style: Optional[str] = None  # Visual production style: photorealistic, cinematic, illustration, etc.
    aspect_ratio: Optional[str] = "1:1"
    quality: Optional[str] = "standard"
    format: Optional[str] = "png"
    dataset_id: Optional[str] = None
    environment_id: Optional[str] = None  # UUID of @-mentioned environment
    folder_id: Optional[str] = None       # UUID of @-mentioned folder (maps to datasets.id)

class AnalyzeImageRequest(BaseModel):
    image_urls: List[str]

class AnalyzeDatasetRequest(BaseModel):
    dataset_id: str
    image_urls: List[str]

class UpdateDatasetTrainingStatusRequest(BaseModel):
    dataset_id: str
    training_status: str  # "trained" or "not_trained"


# ─── User Profile ───────────────────────────────────────────────

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    creative_type: Optional[str] = None  # photographer, designer, marketer, artist, etc.
    use_case: Optional[str] = None
    avatar_url: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    creative_type: Optional[str] = None
    use_case: Optional[str] = None
    avatar_url: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


# ─── Plans ───────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    id: str
    name: str
    credit_limit: int
    price_monthly: float
    features: Optional[List[str]] = None
    created_at: Optional[str] = None


# ─── Subscriptions ───────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str
    stripe_subscription_id: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    created_at: Optional[str] = None
    plan: Optional[PlanResponse] = None  # joined plan details


# ─── Credit Balance ──────────────────────────────────────────────

class CreditBalanceResponse(BaseModel):
    user_id: str
    total_credits: int
    used_credits: int
    remaining_credits: int
    last_reset_at: Optional[str] = None
    updated_at: Optional[str] = None


# ─── Credit Transactions ────────────────────────────────────────

class CreditTransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: int
    type: str
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


# ─── Usage Logs ──────────────────────────────────────────────────

class UsageLogResponse(BaseModel):
    id: str
    user_id: str
    action_type: str
    prompt: Optional[str] = None
    credits_used: int
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


# ─── Account Summary (combined dashboard view) ──────────────────

class AccountSummaryResponse(BaseModel):
    profile: Optional[UserProfileResponse] = None
    subscription: Optional[SubscriptionResponse] = None
    credits: Optional[CreditBalanceResponse] = None
    recent_usage: Optional[List[UsageLogResponse]] = None


# ─── Environments ────────────────────────────────────────────────

class EnvironmentCreate(BaseModel):
    name: str

class EnvironmentUpdate(BaseModel):
    name: str

class EnvironmentResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: Optional[str] = None


# ─── Folders (Datasets within Environments) ──────────────────────

class FolderCreate(BaseModel):
    name: str

class FolderUpdate(BaseModel):
    name: str

class FolderResponse(BaseModel):
    id: str
    name: str
    environment_id: Optional[str] = None
    user_id: Optional[str] = None
    training_status: Optional[str] = None
    master_prompt: Optional[str] = None
    created_at: Optional[str] = None
