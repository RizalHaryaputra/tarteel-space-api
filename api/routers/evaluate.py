import uuid
import time
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse

from api.deps import get_db, get_current_user
from db.database import get_db_connection
from core.limiter import limiter
from schemas.evaluation import EvaluationResult, EvaluationMetricPayload
from services.ml_service import preprocess_and_extract_mfcc, run_inference, convert_to_normalized_wav_bytes
from services.cloudinary_service import upload_audio_to_cloudinary

router = APIRouter(prefix="/evaluate", tags=["Evaluasi Pelafalan"])

# Cache sementara waktu inferensi model berdasarkan evaluation_id
SERVER_BENCHMARK_CACHE: Dict[str, Dict[str, Any]] = {}


def upload_audio_background_task(eval_id: str, audio_bytes: bytes, audio_filename: str):
    """Background task to upload audio to Cloudinary and update the database."""
    try:
        wav_bytes = convert_to_normalized_wav_bytes(audio_bytes)
        audio_path = upload_audio_to_cloudinary(wav_bytes, audio_filename, folder="evaluations")
        print(f"[Cloudinary-BG] Audio berhasil diunggah ke cloud: {audio_path}")

        db = get_db_connection()
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE evaluations SET audio_path = %s WHERE id = %s", (audio_path, eval_id))
            db.commit()
            cursor.close()
        finally:
            db.close()

    except Exception as e:
        print(f"[Cloudinary-BG] Gagal mengunggah audio ke Cloudinary ({e})")


@router.post("/metrics")
async def record_evaluation_metric(
    payload: EvaluationMetricPayload,
    current_user: dict = Depends(get_current_user),
):
    """
    Mencatat waktu respons end-to-end klien dan waktu inferensi model
    ke berkas log benchmark (logs/benchmark_latency.csv).
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "benchmark_latency.csv"

    # Ambil catatan waktu inferensi model dari cache
    server_data = SERVER_BENCHMARK_CACHE.pop(payload.evaluation_id, None)
    inference_ms = server_data["inference_ms"] if server_data else 0.0

    # Gunakan zona waktu Indonesia Barat (WIB / UTC+7) secara eksplisit
    wib_tz = timezone(timedelta(hours=7))
    now_iso = datetime.now(wib_tz).strftime("%Y-%m-%d %H:%M:%S")
    device = (payload.device_type or "desktop").lower()

    file_exists = log_file.exists() and log_file.stat().st_size > 0
    with open(log_file, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("timestamp,evaluation_id,device_type,client_e2e_ms,inference_ms\n")
        f.write(f"{now_iso},{payload.evaluation_id},{device},{payload.client_e2e_ms:.2f},{inference_ms:.2f}\n")

    print(f"[Benchmark-Log] {device.upper()} | E2E: {payload.client_e2e_ms:.2f}ms | Inferensi: {inference_ms:.2f}ms")

    return {
        "status": "success",
        "message": "Metrik waktu respons berhasil dicatat",
        "evaluation_id": payload.evaluation_id,
        "device_type": device,
        "client_e2e_ms": payload.client_e2e_ms,
        "inference_ms": inference_ms
    }


@router.get("/benchmark-log/download")
def download_benchmark_log(current_user: dict = Depends(get_current_user)):
    """Mengunduh berkas log benchmark_latency.csv langsung dari server."""
    log_file = Path("logs") / "benchmark_latency.csv"
    if not log_file.exists():
        raise HTTPException(404, "Berkas log benchmark belum ditemukan di server.")
    return FileResponse(
        path=str(log_file),
        filename="benchmark_latency.csv",
        media_type="text/csv"
    )


@router.post("/{letter_id}", response_model=EvaluationResult)
@limiter.limit("30/minute")
async def evaluate_pronunciation(
    request: Request,
    letter_id: int,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    session_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    ALLOWED_TYPES = (
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/webm", "audio/ogg", "audio/mp4",
        "audio/aac", "audio/mpeg", "audio/x-m4a",
        "video/webm", "video/mp4", "application/octet-stream"
    )
    content_type = (audio.content_type or "").lower()
    if content_type and not any(content_type.startswith(t) for t in ALLOWED_TYPES):
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
        raise HTTPException(422, str(e))

    expected_label = letter["model_label"]

    # Catat waktu inferensi model murni
    t_inf_start = time.perf_counter()
    top_label, top_confidence, top3, expected_confidence = run_inference(mfcc_feature, expected_label)
    inference_ms = (time.perf_counter() - t_inf_start) * 1000

    accuracy_score = round(expected_confidence, 2)

    # Format label prediksi teratas agar ramah dibaca (misal: 'ain_fathah' -> 'Ain Fathah')
    formatted_top_label = " ".join(p.capitalize() for p in top_label.split("_")) if top_label else ""

    # Ambang batas pengenalan suara huruf hijaiyah (Lapisan 3)
    # Jika keyakinan huruf target < 40% DAN keyakinan prediksi teratas model juga < 40%,
    # maka suara dianggap tidak dikenali sebagai pelafalan huruf hijaiyah (noise / batuk / suara acak).
    if accuracy_score < 40.0 and top_confidence < 40.0:
        status_label = "Tidak Dikenali"
        accuracy_score = 0.0
        top_label = ""
        top3 = []
        feedback = (
            f"Suara tidak dikenali sebagai pelafalan huruf hijaiyah. Pastikan Anda melafalkan huruf target "
            f"({letter['base_letter']} {letter['harakat']}) secara jelas dan hindari suara bising atau batuk di sekitar mikrofon."
        )
    elif accuracy_score < 40.0:
        # Suara terdeteksi sebagai huruf hijaiyah lain (top_confidence >= 40%) namun bukan huruf target
        status_label = "Perlu Latihan"
        feedback = (
            f"Pelafalan belum tepat untuk target {letter['base_letter']} {letter['harakat']}. "
            f"Sistem lebih mendeteksi kemiripan dengan huruf '{formatted_top_label}' ({top_confidence:.1f}%). "
            f"Dengarkan kembali contoh audio ustadz dan coba ulangi perlahan."
        )
    elif accuracy_score >= 80.0:
        status_label = "Sangat Baik"
        feedback = f"Luar biasa! Pelafalan {letter['base_letter']} {letter['harakat']} Anda sudah sangat tepat dan artikulasi makhrajnya terdengar jelas."
    elif accuracy_score >= 60.0:
        status_label = "Cukup Baik"
        feedback = f"Cukup baik! Pelafalan {letter['base_letter']} {letter['harakat']} sudah mendekati tepat, latih kembali kejelasan artikulasi makhrajnya."
    else:  # 40.0 <= accuracy_score < 60.0
        status_label = "Perlu Latihan"
        feedback = f"Pelafalan {letter['base_letter']} {letter['harakat']} sudah mengarah ke huruf target, namun artikulasi makhraj masih perlu dilatih kembali agar lebih jelas."

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

    print(f"[Evaluate] {letter['base_letter']} | Inferensi: {inference_ms:.2f} ms")

    # Simpan waktu inferensi ke cache sementara untuk dikaitkan dengan metrik E2E dari klien
    SERVER_BENCHMARK_CACHE[eval_id] = {
        "inference_ms": round(inference_ms, 2),
        "created_at": time.time()
    }

    # Jaga agar memory cache tidak membengkak
    if len(SERVER_BENCHMARK_CACHE) > 200:
        oldest_keys = sorted(SERVER_BENCHMARK_CACHE.keys(), key=lambda k: SERVER_BENCHMARK_CACHE[k]["created_at"])[:50]
        for k in oldest_keys:
            SERVER_BENCHMARK_CACHE.pop(k, None)

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
        inference_ms=round(inference_ms, 2),
    )
