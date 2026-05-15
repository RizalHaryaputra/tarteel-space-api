import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from api.deps import get_db, get_current_user

router = APIRouter(prefix="/sessions", tags=["Sesi Latihan"])

@router.post("/start")
def start_session(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    session_id = str(uuid.uuid4())
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, user_id) VALUES (%s, %s)",
        (session_id, current_user["id"])
    )
    db.commit()
    return {"session_id": session_id, "started_at": datetime.utcnow().isoformat()}

@router.post("/{session_id}/end")
def end_session(session_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE sessions SET ended_at = NOW() WHERE id = %s AND user_id = %s",
        (session_id, current_user["id"])
    )
    db.commit()
    return {"message": "Sesi selesai"}
