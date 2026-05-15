from pydantic import BaseModel

class EvaluationResult(BaseModel):
    letter_id: int
    base_letter: str
    harakat: str
    arabic_script: str
    accuracy_score: float
    top_prediction: str
    is_correct: bool
    status_label: str    # "Tepat ✓" atau "Kurang Tepat ✗"
    feedback: str        # pesan umpan balik
