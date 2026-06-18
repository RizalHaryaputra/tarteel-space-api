import uuid
import time
import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks

from api.deps import get_db, get_current_user
from db.database import get_db_connection
from core.config import THRESHOLD, UPLOAD_DIR, GEMINI_API_KEY
from schemas.evaluation import EvaluationResult
from services.ml_service import preprocess_and_extract_mfcc, run_inference
from services.cloudinary_service import upload_audio_to_cloudinary

router = APIRouter(prefix="/evaluate", tags=["Evaluasi Pelafalan"])

def get_tajweed_grade(score: float) -> str:
    if score >= 90:
        return "Mumtaz (Istimewa)"
    elif score >= 75:
        return "Jayyid Jiddan (Sangat Baik)"
    elif score >= 60:
        return "Jayyid (Baik)"
    else:
        return "Dhaif (Kurang)"

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
    top_label, top_confidence, top3, expected_confidence, top5 = run_inference(mfcc_feature, expected_label)

    is_correct = (top_label == expected_label) and (top_confidence >= THRESHOLD)
    accuracy_score = round(expected_confidence, 2)
    tajweed_grade = get_tajweed_grade(accuracy_score)
    top3_json = json.dumps(top3)
    top5_json = json.dumps(top5)
    
    eval_id = str(uuid.uuid4())
    audio_filename = f"{current_user['id']}_{letter_id}_{eval_id[:8]}.wav"
    initial_audio_path = "uploading..."

    cursor.execute(
        """
        INSERT INTO evaluations
            (id, user_id, session_id, letter_id, audio_path, accuracy_score, top_prediction, is_correct, top3_predictions, tajweed_grade, top5_predictions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (eval_id, current_user["id"], session_id, letter_id,
         initial_audio_path, accuracy_score, top_label, int(is_correct), top3_json, tajweed_grade, top5_json)
    )
    db.commit()

    # Schedule the upload to happen in the background
    background_tasks.add_task(upload_audio_background_task, eval_id, audio_bytes, audio_filename)

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
        id=eval_id,
        letter_id=letter_id,
        base_letter=letter["base_letter"],
        harakat=letter["harakat"],
        arabic_script=letter["arabic_script"],
        accuracy_score=accuracy_score,
        top_prediction=top_label,
        is_correct=is_correct,
        status_label=status_label,
        feedback=feedback,
        tajweed_grade=tajweed_grade,
        top3_predictions=top3,
        top5_predictions=top5,
    )

@router.get("/{eval_id}/explain")
async def explain_pronunciation(
    eval_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "Kunci API Gemini (GEMINI_API_KEY) belum dikonfigurasi di server")

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT e.accuracy_score, e.top_prediction, e.top3_predictions, e.is_correct, e.ai_explanation,
               h.base_letter, h.harakat, h.arabic_script, h.pronunciation, e.user_id
        FROM evaluations e
        JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.id = %s
        """,
        (eval_id,)
    )
    eval_data = cursor.fetchone()
    if not eval_data:
        raise HTTPException(404, "Hasil evaluasi tidak ditemukan")

    if eval_data["user_id"] != current_user["id"]:
        raise HTTPException(403, "Anda tidak memiliki akses ke evaluasi ini")

    # 1. Jika penjelasan AI sudah ada di database, langsung kembalikan (Lazy Loading)
    if eval_data["ai_explanation"]:
        return {"explanation": eval_data["ai_explanation"]}

    # Parse top3_predictions
    top3_raw = eval_data["top3_predictions"]
    top3_list = []
    if top3_raw:
        try:
            top3_list = json.loads(top3_raw)
        except Exception:
            pass

    # Format top3 list for prompt
    top3_formatted = ", ".join([f"'{item['label']}' ({item['score']:.1f}%)" for item in top3_list]) if top3_list else "-"

    # Prompt construction
    prompt = (
        "Anda adalah seorang Ustadz ahli Tajwid dan Makharijul Huruf. Seorang murid sedang belajar melafalkan huruf Hijaiyah berikut:\n"
        f"- Target Huruf: {eval_data['base_letter']} ({eval_data['arabic_script']} - {eval_data['harakat']}) yang seharusnya dilafalkan sebagai '{eval_data['pronunciation']}'.\n"
        "- Hasil Evaluasi Model AI CNN:\n"
        f"  * Skor Akurasi Target Huruf: {float(eval_data['accuracy_score'])}%\n"
        f"  * Prediksi Teratas AI: '{eval_data['top_prediction']}'\n"
        f"  * Alternatif Tebakan Terdekat AI: {top3_formatted}\n\n"
        "PENTING: \n"
        "1. Berikan analisis makhraj yang langsung pada intinya, sangat singkat, padat, dan tanpa basa-basi.\n"
        "2. Sertakan satu tips praktis cara memperbaikinya.\n"
        "3. JANGAN menggunakan format markdown sama sekali (seperti tanda *, #, bold, dll). Gunakan teks biasa saja agar mudah dibaca.\n"
    )

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-3.1-flash-lite")
        response = model.generate_content(prompt)
        explanation_text = response.text.strip()
    except Exception as e:
        raise HTTPException(500, f"Gagal mendapatkan penjelasan dari Gemini: {str(e)}")

    # 2. Simpan penjelasan yang baru di-generate ke database
    cursor.execute("UPDATE evaluations SET ai_explanation = %s WHERE id = %s", (explanation_text, eval_id))
    db.commit()

    return {"explanation": explanation_text}
