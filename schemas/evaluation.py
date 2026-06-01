from pydantic import BaseModel
from typing import List, Dict, Any

class EvaluationResult(BaseModel):
    id: str
    letter_id: int
    base_letter: str
    harakat: str
    arabic_script: str
    accuracy_score: float
    top_prediction: str
    is_correct: bool
    status_label: str    # "Tepat ✓" atau "Kurang Tepat ✗"
    feedback: str        # pesan umpan balik
    tajweed_grade: str
    top3_predictions: List[Dict[str, Any]]
