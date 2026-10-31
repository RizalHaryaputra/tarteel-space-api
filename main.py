from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from core.config import (
    MODEL_PATH, LABEL_MAP_PATH, NORM_MEAN_PATH, NORM_STD_PATH, SESSION_SECRET_KEY, CORS_ORIGINS
)
from services.ml_service import ml_state, reload_and_warmup_model
from api.routers import auth, letters, evaluate, sessions, history, oauth, feedback, admin, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Memuat model TFLite dan melakukan warm-up...")

    # Siapkan direktori dan berkas log benchmark sejak startup
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "benchmark_latency.csv"
    if not log_file.exists() or log_file.stat().st_size == 0:
        log_file.write_text("timestamp,evaluation_id,device_type,client_e2e_ms,inference_ms\n", encoding="utf-8")

    try:
        reload_and_warmup_model(
            model_path=str(MODEL_PATH),
            mean_path=str(NORM_MEAN_PATH),
            std_path=str(NORM_STD_PATH),
            label_path=str(LABEL_MAP_PATH)
        )
    except Exception as e:
        print(f"[Startup] Peringatan: Memuat model gagal ({e})")

    print(f"[Startup] Model siap! Total kelas: {len(ml_state['idx2label'])}")

    yield

    print("[Shutdown] Membersihkan resource...")
    ml_state.clear()


app = FastAPI(
    title="Tarteel Space API",
    description="Backend API untuk evaluasi pelafalan huruf hijaiyah",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(profile.router)


@app.get("/")
def root():
    return {
        "app": "Tarteel Space API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
