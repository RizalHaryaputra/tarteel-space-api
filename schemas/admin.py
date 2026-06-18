from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserRoleUpdate(BaseModel):
    role: str

class LetterCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    base_letter: str
    harakat: str
    pronunciation: str
    arabic_script: str
    model_label: str

class LetterUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    base_letter: Optional[str] = None
    harakat: Optional[str] = None
    pronunciation: Optional[str] = None
    arabic_script: Optional[str] = None
    model_label: Optional[str] = None

class DatasetPoolCreate(BaseModel):
    evaluation_id: str
    verified_label: str
    is_verified_correct: bool = True
    admin_notes: Optional[str] = None

class MarkTrainedRequest(BaseModel):
    dataset_ids: list[int]
    is_trained: bool = True
