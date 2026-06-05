import uuid
import time
import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException

from api.deps import get_db, get_current_user
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

    expected_label = letter["model_label"]
    top_label, top_confidence, top3, expected_confidence, top5 = run_inference(mfcc_feature, expected_label)

    is_correct = (top_label == expected_label) and (top_confidence >= THRESHOLD)
    accuracy_score = round(expected_confidence, 2)

    # Cloudinary upload fallback to local storage
    audio_path = None
    audio_filename = f"{current_user['id']}_{letter_id}_{uuid.uuid4().hex[:8]}.wav"
    try:
        audio_path = upload_audio_to_cloudinary(audio_bytes, audio_filename, folder="evaluations")
        print(f"[Cloudinary] Audio berhasil diunggah ke cloud: {audio_path}")
    except ValueError:
        # Fallback local file storage
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        audio_path_obj = UPLOAD_DIR / audio_filename
        audio_path_obj.write_bytes(audio_bytes)
        audio_path = str(audio_path_obj)
        print(f"[Local Storage] Cloudinary belum diset, menyimpan secara lokal di: {audio_path}")

    eval_id = str(uuid.uuid4())
    tajweed_grade = get_tajweed_grade(accuracy_score)
    top3_json = json.dumps(top3)
    top5_json = json.dumps(top5)

    cursor.execute(
        """
        INSERT INTO evaluations
            (id, user_id, session_id, letter_id, audio_path, accuracy_score, top_prediction, is_correct, top3_predictions, tajweed_grade, top5_predictions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (eval_id, current_user["id"], session_id, letter_id,
         audio_path, accuracy_score, top_label, int(is_correct), top3_json, tajweed_grade, top5_json)
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
        SELECT e.accuracy_score, e.top_prediction, e.top3_predictions, e.is_correct,
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
        f"  * 3 Alternatif Tebakan Terdekat AI: {top3_formatted}\n\n"
        "Berdasarkan data di atas, tolong berikan analisis makhraj dan sifat huruf yang kemungkinan terjadi kesalahan jika pelafalan murid tersebut kurang tepat, "
        "atau berikan pujian yang hangat dan tips mempertahankan pelafalan jika pelafalan murid sudah tepat.\n"
        "Susun penjelasan Anda secara singkat, jelas, ramah, dan memotivasi menggunakan bahasa Indonesia yang baik, dengan format:\n"
        "1. Analisis Kesalahan / Keunggulan Pelafalan (bandingkan letak makhraj huruf target dengan huruf tebakan terdekat jika salah)\n"
        "2. Tips Praktis Latihan untuk murid."
    )

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-3.1-flash-lite")
        response = model.generate_content(prompt)
        explanation_text = response.text.strip()
    except Exception as e:
        raise HTTPException(500, f"Gagal mendapatkan penjelasan dari Gemini: {str(e)}")

    return {"explanation": explanation_text}
