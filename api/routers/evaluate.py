import uuid
import time
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException

from api.deps import get_db, get_current_user
from core.config import THRESHOLD, UPLOAD_DIR
from schemas.evaluation import EvaluationResult
from services.ml_service import preprocess_and_extract_mfcc, run_inference

router = APIRouter(prefix="/evaluate", tags=["Evaluasi Pelafalan"])

@router.post("/{letter_id}", response_model=EvaluationResult)
async def evaluate_pronunciation(
    letter_id: int,
    audio: UploadFile = File(...),
    session_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    start_time = time.time()
    ALLOWED_TYPES = ("audio/wav", "audio/wave", "audio/webm", "audio/ogg", "audio/mp4")
    content_type = (audio.content_type or "").lower()
    if not any(content_type.startswith(t) for t in ALLOWED_TYPES):
        raise HTTPException(400, f"Format tidak didukung: {audio.content_type}")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")

    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(400, "Audio terlalu pendek, mohon rekam ulang")

    try:
        mfcc_feature = preprocess_and_extract_mfcc(audio_bytes)
    except Exception as e:
        raise HTTPException(422, f"Gagal memproses audio: {str(e)}")

    top_label, confidence, top3 = run_inference(mfcc_feature)

    expected_label = letter["model_label"]
    is_correct = (top_label == expected_label) and (confidence >= THRESHOLD)
    accuracy_score = round(confidence, 2)

    save_audio = True
    audio_path = None
    if save_audio:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        audio_filename = f"{current_user['id']}_{letter_id}_{uuid.uuid4().hex[:8]}.wav"
        audio_path_obj = UPLOAD_DIR / audio_filename
        audio_path_obj.write_bytes(audio_bytes)
        audio_path = str(audio_path_obj)

    eval_id = str(uuid.uuid4())
    cursor.execute(
        """
        INSERT INTO evaluations
            (id, user_id, session_id, letter_id, audio_path, accuracy_score, top_prediction, is_correct)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (eval_id, current_user["id"], session_id, letter_id,
         audio_path, accuracy_score, top_label, int(is_correct))
    )
    db.commit()

    status_label = "Tepat ✓" if is_correct else "Kurang Tepat ✗"
    if is_correct:
        feedback = f"Bagus! Pelafalan {letter['base_letter']} {letter['harakat']} Anda sudah benar."
    elif accuracy_score >= 50:
        feedback = f"Hampir benar! Perhatikan makhraj huruf {letter['base_letter']}, skor Anda {accuracy_score:.1f}%."
    else:
        feedback = f"Perlu latihan lagi. Dengarkan contoh pelafalan {letter['base_letter']} dan coba ulangi."

    elapsed_time = time.time() - start_time
    print(f"[Evaluate] {letter['base_letter']} dievaluasi dalam {elapsed_time:.3f} detik")

    return EvaluationResult(
        letter_id=letter_id,
        base_letter=letter["base_letter"],
        harakat=letter["harakat"],
        arabic_script=letter["arabic_script"],
        accuracy_score=accuracy_score,
        top_prediction=top_label,
        is_correct=is_correct,
        status_label=status_label,
        feedback=feedback,
    )
