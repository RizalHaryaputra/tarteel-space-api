from pydantic import BaseModel, EmailStr
from typing import Optional

class ProfileResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    auth_provider: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    name: str
    email: EmailStr
    bio: Optional[str] = None

class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str
