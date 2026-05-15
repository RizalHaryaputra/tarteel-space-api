import json
from contextlib import asynccontextmanager
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tensorflow import keras

from core.config import (
    MODEL_PATH, LABEL_MAP_PATH, NORM_MEAN_PATH, NORM_STD_PATH, UPLOAD_DIR
)
from services.ml_service import ml_state
from api.routers import auth, letters, evaluate, sessions, history

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [Startup] Memuat model CNN...")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    model = keras.models.load_model(MODEL_PATH)
    ml_state["model"] = model

    with open(LABEL_MAP_PATH) as f:
        mapping = json.load(f)
    ml_state["idx2label"] = {int(k): v for k, v in mapping["idx2label"].items()}
    ml_state["label2idx"] = mapping["label2idx"]

    ml_state["norm_mean"] = float(np.load(NORM_MEAN_PATH))
    ml_state["norm_std"] = float(np.load(NORM_STD_PATH))

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
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