import json
from contextlib import asynccontextmanager
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        import tensorflow.lite as tflite
        Interpreter = tflite.Interpreter

from core.config import (
    MODEL_PATH, LABEL_MAP_PATH, NORM_MEAN_PATH, NORM_STD_PATH, UPLOAD_DIR, SESSION_SECRET_KEY, FRONTEND_URL
)
from services.ml_service import ml_state
from api.routers import auth, letters, evaluate, sessions, history, oauth

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [Startup] Memuat model TFLite...")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    interpreter = Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()
    ml_state["interpreter"] = interpreter
    ml_state["input_details"] = interpreter.get_input_details()
    ml_state["output_details"] = interpreter.get_output_details()

    with open(LABEL_MAP_PATH) as f:
        mapping = json.load(f)
    ml_state["idx2label"] = {int(k): v for k, v in mapping["idx2label"].items()}
    ml_state["label2idx"] = mapping["label2idx"]

    ml_state["norm_mean"] = float(np.load(NORM_MEAN_PATH)[0])
    ml_state["norm_std"] = float(np.load(NORM_STD_PATH)[0])

    print("🔥 [Startup] Melakukan warm-up model dan seluruh pipeline audio...")
    try:
        import io
        import soundfile as sf
        from services.ml_service import preprocess_and_extract_mfcc, run_inference
        
        # 1. Buat dummy audio (sine wave) agar melewati batas silence/trim
        sr = 22050
        t = np.linspace(0, 1, sr, endpoint=False)
        dummy_audio = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        buf = io.BytesIO()
        sf.write(buf, dummy_audio, sr, format='WAV')
        wav_bytes = buf.getvalue()
        
        # 2. Jalankan seluruh pipeline preprocessing (Numba JIT komplit: resample, trim, mfcc, delta)
        dummy_mfcc = preprocess_and_extract_mfcc(wav_bytes)
        
        # 3. Jalankan inferensi (TensorFlow graph)
        run_inference(dummy_mfcc)
        print("✅ [Startup] Warm-up selesai secara menyeluruh!")
    except Exception as e:
        print(f"⚠️ [Startup] Peringatan: Warm-up gagal ({e})")

    print(f"✅ [Startup] Model siap! Total kelas: {len(ml_state['idx2label'])}")

    yield

    print("🛑 [Shutdown] Membersihkan resource...")
    ml_state.clear()


app = FastAPI(
    title="Tarteel Space API",
    description="Backend API untuk evaluasi pelafalan huruf hijaiyah",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set([FRONTEND_URL, "http://localhost:3000"])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(letters.router)
app.include_router(evaluate.router)
app.include_router(sessions.router)
app.include_router(history.router)

@app.get("/")
def root():
    return {
        "app": "Tarteel Space API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }