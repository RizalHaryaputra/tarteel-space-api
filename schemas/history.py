from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class HistoryItem(BaseModel):
    id: str
    base_letter: str
    harakat: str
    arabic_script: str
    accuracy_score: float
    is_correct: bool
    created_at: str
    tajweed_grade: Optional[str] = None
    ai_explanation: Optional[str] = None
    user_audio: Optional[str] = None
    ustadz_audio: Optional[str] = None
    top3_predictions: Optional[List[Dict[str, Any]]] = None
    top5_predictions: Optional[List[Dict[str, Any]]] = None

class LetterRecommendation(BaseModel):
    base_letter: str
    arabic_script: str
    avg_score: float
    total_trials: int

class DashboardStats(BaseModel):
    total_latihan: int
    rata_rata_akurasi: float
    streak_hari: int
    huruf_terlemah: List[LetterRecommendation]
    huruf_terkuat: List[LetterRecommendation]
