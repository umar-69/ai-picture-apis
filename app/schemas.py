from pydantic import BaseModel, EmailStr
from typing import Optional, Any

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
