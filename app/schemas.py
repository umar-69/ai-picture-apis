from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    metadata: Optional[dict[str, Any]] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    created_at: Optional[str] = None
    last_sign_in_at: Optional[str] = None
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
    aspect_ratio: Optional[str] = "1:1"
    quality: Optional[str] = "standard"
    format: Optional[str] = "png"
    dataset_id: Optional[str] = None

class AnalyzeImageRequest(BaseModel):
    image_urls: List[str]

class AnalyzeDatasetRequest(BaseModel):
    dataset_id: str
    image_urls: List[str]
