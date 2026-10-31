from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class EvaluationResult(BaseModel):
    id: str
    letter_id: int
    base_letter: str
    harakat: str
    arabic_script: str
    accuracy_score: float
    top_prediction: str
    status_label: Optional[str] = None
    feedback: str
    top3_predictions: List[Dict[str, Any]]
    inference_ms: Optional[float] = None

class EvaluationMetricPayload(BaseModel):
    evaluation_id: str
    client_e2e_ms: float
    device_type: Optional[str] = "desktop"
