from pydantic import BaseModel
from typing import Optional

class HistoryItem(BaseModel):
    id: str
    base_letter: str
    harakat: str
    arabic_script: str
    accuracy_score: float
    is_correct: bool
    created_at: str

class DashboardStats(BaseModel):
    total_latihan: int
    rata_rata_akurasi: float
    streak_hari: int
    huruf_terlemah: Optional[str]
    huruf_terkuat: Optional[str]
