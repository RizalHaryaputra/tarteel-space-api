import uuid
import time
import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks

from api.deps import get_db, get_current_user
from db.database import get_db_connection
from core.config import UPLOAD_DIR
from schemas.evaluation import EvaluationResult
from services.ml_service import preprocess_and_extract_mfcc, run_inference
from services.cloudinary_service import upload_audio_to_cloudinary

router = APIRouter(prefix="/evaluate", tags=["Evaluasi Pelafalan"])

def upload_audio_background_task(eval_id: str, audio_bytes: bytes, audio_filename: str):
    """Background task to upload audio to Cloudinary and update the database."""
    try:
        audio_path = upload_audio_to_cloudinary(audio_bytes, audio_filename, folder="evaluations")
        print(f"[Cloudinary-BG] Audio berhasil diunggah ke cloud: {audio_path}")
        
        # Update database with the Cloudinary URL
        db = get_db_connection() 
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE evaluations SET audio_path = %s WHERE id = %s", (audio_path, eval_id))
            db.commit()
            cursor.close()
        finally:
            db.close()
            
    except Exception as e:
        # Fallback local file storage if Cloudinary fails
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        audio_path_obj = UPLOAD_DIR / audio_filename
        audio_path_obj.write_bytes(audio_bytes)
        audio_path = str(audio_path_obj)
        print(f"[Local Storage-BG] Cloudinary gagal/belum diset ({e}), menyimpan secara lokal di: {audio_path}")
        
        # Update database with the local path
        db = get_db_connection()
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE evaluations SET audio_path = %s WHERE id = %s", (audio_path, eval_id))
            db.commit()
            cursor.close()
        finally:
            db.close()

@router.post("/{letter_id}", response_model=EvaluationResult)
async def evaluate_pronunciation(
    letter_id: int,
    background_tasks: BackgroundTasks,
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

    expected_label = letter["model_label"]
    top_label, top_confidence, top3, expected_confidence = run_inference(mfcc_feature, expected_label)

    accuracy_score = round(expected_confidence, 2)
    top3_json = json.dumps(top3)
    
    eval_id = str(uuid.uuid4())
    audio_filename = f"{current_user['id']}_{letter_id}_{eval_id[:8]}.wav"
    initial_audio_path = "uploading..."

    cursor.execute(
        """
        INSERT INTO evaluations
            (id, user_id, session_id, letter_id, audio_path, accuracy_score, top_prediction, top3_predictions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (eval_id, current_user["id"], session_id, letter_id,
         initial_audio_path, accuracy_score, top_label, top3_json)
    )
    db.commit()

    # Schedule the upload to happen in the background
    background_tasks.add_task(upload_audio_background_task, eval_id, audio_bytes, audio_filename)

    # Feedback dinamis berbasis persentase akurasi
    if accuracy_score >= 80:
        status_label = "Sangat Baik"
        feedback = f"Luar biasa! Pelafalan {letter['base_letter']} {letter['harakat']} Anda sudah sangat tepat dan artikulasi makhrajnya terdengar jelas."
    elif accuracy_score >= 60:
        status_label = "Cukup Baik"
        feedback = f"Cukup baik! Pelafalan {letter['base_letter']} {letter['harakat']} sudah mendekati tepat, latih kembali kejelasan artikulasi makhrajnya."
    else:
        status_label = "Perlu Latihan"
        feedback = f"Perlu latihan lagi. Dengarkan kembali contoh pelafalan referensi untuk huruf {letter['base_letter']} {letter['harakat']} dan coba ulangi perlahan."

    elapsed_time = time.time() - start_time
    print(f"[Evaluate] {letter['base_letter']} dievaluasi dalam {elapsed_time:.3f} detik")

    return EvaluationResult(
        id=eval_id,
        letter_id=letter_id,
        base_letter=letter["base_letter"],
        harakat=letter["harakat"],
        arabic_script=letter["arabic_script"],
        accuracy_score=accuracy_score,
        top_prediction=top_label,
        status_label=status_label,
        feedback=feedback,
        top3_predictions=top3,
    )
