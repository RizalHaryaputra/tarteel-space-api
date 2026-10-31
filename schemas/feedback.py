from pydantic import BaseModel

class FeedbackCreate(BaseModel):
    evaluation_id: str
    comment: str
