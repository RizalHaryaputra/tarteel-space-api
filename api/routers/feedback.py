import uuid
from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_db, get_current_user
from schemas.feedback import FeedbackCreate

router = APIRouter(prefix="/feedback", tags=["User Feedback"])

@router.post("/", status_code=201)
def create_feedback(
    feedback: FeedbackCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    
    # Verifikasi bahwa evaluasi ada dan dimiliki oleh user yang sedang login
    cursor.execute(
        "SELECT id, user_id FROM evaluations WHERE id = %s",
        (feedback.evaluation_id,)
    )
    evaluation = cursor.fetchone()
    if not evaluation:
        raise HTTPException(404, "Evaluasi tidak ditemukan")
        
    if evaluation["user_id"] != current_user["id"]:
        raise HTTPException(403, "Anda tidak berwenang memberikan feedback untuk evaluasi ini")
        
    feedback_id = str(uuid.uuid4())
    cursor.execute(
        """
        INSERT INTO user_feedbacks (id, evaluation_id, user_id, comment)
        VALUES (%s, %s, %s, %s)
        """,
        (feedback_id, feedback.evaluation_id, current_user["id"], feedback.comment)
    )
    db.commit()
    
    return {"message": "Feedback Anda berhasil dikirim, terima kasih!", "feedback_id": feedback_id}
