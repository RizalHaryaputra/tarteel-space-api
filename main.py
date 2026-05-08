# ============================================================
#  TARTEEL SPACE — Backend FastAPI (main.py)
#  Rizal Haryaputra | Teknologi Informasi UNY | 2026
#
#  Jalankan:
#    uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================================

import os, io, uuid, json
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import librosa
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import mysql.connector
from mysql.connector import pooling
from passlib.context import CryptContext
from jose import JWTError, jwt
import tensorflow as tf
from tensorflow import keras



# ============================================================
# KONFIGURASI  (simpan di .env untuk production)
# ============================================================
SECRET_KEY      = "asdfnjwnfifujonwruncoewi902unfwkkwe"   
ALGORITHM       = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 hari

DB_CONFIG = {
    "host"    : "localhost",
    "user"    : "root",
    "password": "",               
    "database": "db_tarteel_space",
    "charset" : "utf8mb4",
}

MODEL_PATH       = "./model/hijaiyah_model_final.keras"  # file .keras dari Google Drive
LABEL_MAP_PATH   = "./model/label_mapping.json"
NORM_MEAN_PATH   = "./model/norm_mean.npy"
NORM_STD_PATH    = "./model/norm_std.npy"
UPLOAD_DIR       = Path("./uploads/audio")

# Parameter MFCC — harus sama persis dengan saat training!
SAMPLE_RATE = 22050
DURATION    = 2.0
MAX_LEN     = int(SAMPLE_RATE * DURATION)
N_MFCC      = 40
N_FFT       = 2048
HOP_LEN     = 512
THRESHOLD   = 70.0  # skor minimal (%) untuk dinyatakan "Tepat"


# ============================================================
# STARTUP & SHUTDOWN — load model sekali saja
# ============================================================
ml_state = {}   # menyimpan interpreter + label map + norm stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────
    print("🚀 [Startup] Memuat model CNN...")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    model = keras.models.load_model(MODEL_PATH)
    ml_state["model"] = model

    with open(LABEL_MAP_PATH) as f:
        mapping = json.load(f)
    ml_state["idx2label"] = {int(k): v for k, v in mapping["idx2label"].items()}
    ml_state["label2idx"] = mapping["label2idx"]

    ml_state["norm_mean"] = float(np.load(NORM_MEAN_PATH))
    ml_state["norm_std"]  = float(np.load(NORM_STD_PATH))

    print(f"✅ [Startup] Model siap! Total kelas: {len(ml_state['idx2label'])}")

    yield   # aplikasi berjalan di sini

    # ── Shutdown ─────────────────────────────────────────
    print("🛑 [Shutdown] Membersihkan resource...")
    ml_state.clear()


# ============================================================
# APP INSTANCE
# ============================================================
app = FastAPI(
    title       = "Tarteel Space API",
    description = "Backend API untuk evaluasi pelafalan huruf hijaiyah",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000"],  # URL frontend Nuxt.js
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ============================================================
# DATABASE — connection pool
# ============================================================
db_pool = pooling.MySQLConnectionPool(
    pool_name="tarteel_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_db():
    """Dependency: ambil koneksi dari pool, kembalikan setelah selesai."""
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()


# ============================================================
# AUTH — password hashing & JWT
# ============================================================
pwd_ctx   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2    = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2), db=Depends(get_db)) -> dict:
    """Dependency: validasi JWT dan kembalikan data user."""
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Token tidak valid atau sudah kadaluarsa",
        headers     = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user is None:
        raise credentials_exception
    return user


# ============================================================
# SCHEMAS — Pydantic models
# ============================================================
class RegisterRequest(BaseModel):
    name    : str
    email   : EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type  : str = "bearer"
    user_name   : str
    user_id     : str

class EvaluationResult(BaseModel):
    letter_id      : int
    base_letter    : str
    harakat        : str
    arabic_script  : str
    accuracy_score : float
    top_prediction : str
    is_correct     : bool
    status_label   : str    # "Tepat ✓" atau "Kurang Tepat ✗"
    feedback       : str    # pesan umpan balik

class HistoryItem(BaseModel):
    id             : str
    base_letter    : str
    harakat        : str
    arabic_script  : str
    accuracy_score : float
    is_correct     : bool
    created_at     : str

class DashboardStats(BaseModel):
    total_latihan      : int
    rata_rata_akurasi  : float
    streak_hari        : int
    huruf_terlemah     : Optional[str]
    huruf_terkuat      : Optional[str]


# ============================================================
# HELPER — Audio preprocessing + MFCC extraction
# ============================================================
def load_audio_robust(audio_bytes: bytes) -> tuple:
    """
    Load audio bytes → numpy array float32 [-1, 1] pada SAMPLE_RATE.

    Urutan prioritas:
      1. PyAV  — bekerja untuk WebM/Opus langsung dari browser (terbukti)
      2. soundfile — cepat untuk WAV bersih
      3. librosa   — last resort

    PyAV normalisasi:
      - Format fltp (float planar) → nilai sudah [-1,1], tidak perlu dibagi
      - Format s16p (int16 planar) → dibagi 32768.0
      - Deteksi otomatis dari dtype hasil to_ndarray()
    """
    import av
    import soundfile as sf

    buf = io.BytesIO(audio_bytes)

    # ── Strategi 1: PyAV — handle WebM/Opus dari browser ──────────────
    try:
        buf.seek(0)
        container   = av.open(buf)
        stream      = container.streams.audio[0]
        orig_sr     = stream.sample_rate

        frames_data = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray()   # shape: (channels, samples)

            # Normalisasi berdasarkan dtype ASLI frame (bukan setelah konversi)
            if arr.dtype == np.int16:
                # s16/s16p: range [-32768, 32767] → bagi 32768
                arr = arr.astype(np.float32) / 32768.0
            elif arr.dtype == np.float32:
                # fltp: sudah [-1,1], tidak perlu apa-apa
                pass
            else:
                # Format lain (s32, dll): normalisasi ke [-1,1] berdasarkan max
                arr = arr.astype(np.float32)
                mx  = np.abs(arr).max()
                if mx > 0:
                    arr = arr / mx

            frames_data.append(arr)

        if not frames_data:
            raise ValueError("Tidak ada frame audio")

        y = np.concatenate(frames_data, axis=1)          # (channels, total_samples)
        y = y.mean(axis=0) if y.shape[0] > 1 else y[0]  # → mono (total_samples,)
        y = np.clip(y, -1.0, 1.0)

        if orig_sr != SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=orig_sr, target_sr=SAMPLE_RATE)

        print(f"[Audio] PyAV OK | sr={orig_sr} | samples={len(y)} | peak={np.abs(y).max():.3f}")
        return y, SAMPLE_RATE

    except Exception as e:
        print(f"[Audio] PyAV gagal: {e}")

    # ── Strategi 2: soundfile — untuk WAV bersih ───────────────────────
    try:
        buf.seek(0)
        y, orig_sr = sf.read(buf, dtype='float32', always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        if orig_sr != SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=orig_sr, target_sr=SAMPLE_RATE)
        print(f"[Audio] soundfile OK | sr={orig_sr} | samples={len(y)}")
        return y, SAMPLE_RATE
    except Exception as e:
        print(f"[Audio] soundfile gagal: {e}")

    # ── Strategi 3: librosa fallback ───────────────────────────────────
    try:
        buf.seek(0)
        y, sr = librosa.load(buf, sr=SAMPLE_RATE, mono=True)
        print(f"[Audio] librosa OK | sr={sr} | samples={len(y)}")
        return y, sr
    except Exception as e:
        raise ValueError(
            f"Format audio tidak dikenali. Detail: {e}"
        )


def preprocess_and_extract_mfcc(audio_bytes: bytes) -> np.ndarray:
    """
    Proses audio bytes → MFCC 3-channel siap inferensi.
    Audio dari browser sudah WAV 22050 Hz mono (konversi via Web Audio API).
    Alur: load → validasi → trim silence → pad/truncate → normalisasi → MFCC+Δ+ΔΔ
    """
    # 1. Load audio dengan fallback yang aman
    y, sr = load_audio_robust(audio_bytes)

    # 2. Validasi: audio tidak kosong dan cukup keras
    if len(y) == 0:
        raise ValueError("Audio kosong. Coba rekam ulang.")

    peak = np.max(np.abs(y))
    if peak < 0.015:
        raise ValueError("Suara tidak terdeteksi atau terlalu pelan. Bicara lebih dekat ke mikrofon.")

    # 3. Normalisasi amplitudo ke [-1, 1] SEBELUM trim
    #    Ini penting agar top_db trim konsisten di semua kondisi mikrofon
    y = y / peak

    # 4. Trim silence
    y, _ = librosa.effects.trim(y, top_db=20)

    if len(y) == 0:
        raise ValueError("Audio hanya berisi keheningan setelah diproses.")

    # 5. Pad atau truncate ke panjang tetap (sama persis dengan training)
    if len(y) < MAX_LEN:
        y = np.pad(y, (0, MAX_LEN - len(y)), mode="constant")
    else:
        y = y[:MAX_LEN]

    # 6. Ekstraksi MFCC + Delta + Delta² — parameter HARUS identik dengan training
    mfcc        = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LEN)
    delta_mfcc  = librosa.feature.delta(mfcc)
    delta2_mfcc = librosa.feature.delta(mfcc, order=2)

    # 7. Stack 3 channel → transpose ke (mfcc, time, channel) untuk Keras
    combined = np.stack([mfcc, delta_mfcc, delta2_mfcc], axis=0)  # (3, 40, T)
    combined = np.transpose(combined, (1, 2, 0))                  # (40, T, 3)

    # 8. Normalisasi Z-score — WAJIB pakai mean & std dari data TRAINING
    mean = ml_state["norm_mean"]
    std  = ml_state["norm_std"]
    combined = (combined - mean) / (std + 1e-8)

    return combined.astype(np.float32)


# Suhu softmax — nilai > 1 membuat distribusi lebih "lunak"/tidak terlalu yakin.
# Ini kompensasi sementara untuk model yang overfitting.
# Nilai ideal: cari dengan cara validasi manual (biasanya 1.5–3.0)
TEMPERATURE = 2.0


def softmax_with_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    """Terapkan temperature scaling pada logits sebelum softmax."""
    logits = logits / temperature
    logits = logits - np.max(logits)   # numerical stability
    exp    = np.exp(logits)
    return exp / np.sum(exp)


def run_inference(mfcc_feature: np.ndarray) -> tuple[str, float, list]:
    """
    Jalankan model Keras → kembalikan (label, confidence, top3).

    Menggunakan temperature scaling untuk mengurangi overconfidence.
    Model yang overfitting cenderung memproduksi softmax mendekati 100%
    meski inputnya salah — temperature > 1 menyebarkan probabilitas lebih merata.
    """
    model     = ml_state["model"]
    idx2label = ml_state["idx2label"]

    # Tambahkan dimensi batch: (40, T, 3) → (1, 40, T, 3)
    input_data = np.expand_dims(mfcc_feature, axis=0)

    # Ambil output SEBELUM softmax (logits) jika memungkinkan,
    # atau pakai raw softmax output jika model tidak expose logits
    raw_output = model.predict(input_data, verbose=0)[0]   # shape: (84,)

    # Jika output sudah softmax (sum ≈ 1), konversi balik ke log-space (logit proxy)
    # agar temperature scaling bermakna
    if abs(raw_output.sum() - 1.0) < 0.01:
        # Output adalah probabilitas → ubah ke log agar temperature bisa diterapkan
        logit_proxy = np.log(np.clip(raw_output, 1e-9, 1.0))
        output = softmax_with_temperature(logit_proxy, TEMPERATURE)
    else:
        output = softmax_with_temperature(raw_output, TEMPERATURE)

    top_idx   = int(np.argmax(output))
    top_label = idx2label[top_idx]
    confidence= float(output[top_idx]) * 100.0

    # Top-3 prediksi
    top3_idx  = np.argsort(output)[::-1][:3]
    top3      = [{"label": idx2label[i], "score": round(float(output[i])*100, 2)} for i in top3_idx]

    # Debug log — lihat distribusi probabilitas top-5
    top5_idx = np.argsort(output)[::-1][:5]
    print(f"[Inference] Top-5: " +
          " | ".join(f"{idx2label[i]}={output[i]*100:.1f}%" for i in top5_idx))

    return top_label, confidence, top3


# ============================================================
# ROUTER — Auth
# ============================================================
from fastapi import APIRouter
auth_router = APIRouter(prefix="/auth", tags=["Autentikasi"])

@auth_router.post("/register", status_code=201)
def register(req: RegisterRequest, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    if cursor.fetchone():
        raise HTTPException(400, "Email sudah terdaftar")

    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (id, name, email, password_hash) VALUES (%s, %s, %s, %s)",
        (user_id, req.name, req.email, hash_password(req.password))
    )
    db.commit()
    return {"message": "Akun berhasil dibuat", "user_id": user_id}


@auth_router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (form.username,))
    user = cursor.fetchone()

    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )

    token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(
        access_token=token,
        user_name   =user["name"],
        user_id     =user["id"]
    )


# ============================================================
# ROUTER — Hijaiyah Letters (master data)
# ============================================================
letter_router = APIRouter(prefix="/letters", tags=["Huruf Hijaiyah"])

@letter_router.get("/")
def get_all_letters(db=Depends(get_db)):
    """Ambil semua 84 huruf untuk ditampilkan di halaman latihan."""
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, base_letter, harakat, pronunciation, arabic_script "
        "FROM hijaiyah_letters ORDER BY id"
    )
    return cursor.fetchall()


@letter_router.get("/{letter_id}")
def get_letter(letter_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,)
    )
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")
    return letter


# ============================================================
# ROUTER — Evaluasi (inti sistem AI)
# ============================================================
eval_router = APIRouter(prefix="/evaluate", tags=["Evaluasi Pelafalan"])

@eval_router.post("/{letter_id}", response_model=EvaluationResult)
async def evaluate_pronunciation(
    letter_id  : int,
    audio      : UploadFile = File(...),
    session_id : Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db         = Depends(get_db),
):
    """
    Endpoint utama: terima file audio → preprocessing MFCC → inferensi CNN
    → simpan hasil ke DB → kembalikan skor ke frontend.
    """
    # 1. Validasi format audio — browser bisa kirim "audio/webm;codecs=opus" dll
    ALLOWED_TYPES = ("audio/wav", "audio/wave", "audio/webm", "audio/ogg", "audio/mp4")
    content_type  = (audio.content_type or "").lower()
    if not any(content_type.startswith(t) for t in ALLOWED_TYPES):
        raise HTTPException(400, f"Format tidak didukung: {audio.content_type}")

    # 2. Validasi letter_id
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")

    # 3. Baca bytes audio
    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(400, "Audio terlalu pendek, mohon rekam ulang")

    # 4. Preprocessing → ekstraksi MFCC
    try:
        mfcc_feature = preprocess_and_extract_mfcc(audio_bytes)
    except Exception as e:
        raise HTTPException(422, f"Gagal memproses audio: {str(e)}")

    # 5. Inferensi model CNN
    top_label, confidence, top3 = run_inference(mfcc_feature)

    # 6. Tentukan apakah prediksi benar
    expected_label = letter["model_label"]
    is_correct     = (top_label == expected_label) and (confidence >= THRESHOLD)
    accuracy_score = round(confidence, 2)

    # 7. Simpan file audio (opsional — bisa dinonaktifkan)
    audio_path = None
    save_audio = True
    if save_audio:
        audio_filename = f"{current_user['id']}_{letter_id}_{uuid.uuid4().hex[:8]}.wav"
        audio_path_obj = UPLOAD_DIR / audio_filename
        audio_path_obj.write_bytes(audio_bytes)
        audio_path = str(audio_path_obj)

    # 8. Simpan hasil ke database
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

    # 9. Bangun respons
    status_label = "Tepat ✓" if is_correct else "Kurang Tepat ✗"
    if is_correct:
        feedback = f"Bagus! Pelafalan {letter['base_letter']} {letter['harakat']} Anda sudah benar."
    elif accuracy_score >= 50:
        feedback = f"Hampir benar! Perhatikan makhraj huruf {letter['base_letter']}, skor Anda {accuracy_score:.1f}%."
    else:
        feedback = f"Perlu latihan lagi. Dengarkan contoh pelafalan {letter['base_letter']} dan coba ulangi."

    return EvaluationResult(
        letter_id     = letter_id,
        base_letter   = letter["base_letter"],
        harakat       = letter["harakat"],
        arabic_script = letter["arabic_script"],
        accuracy_score= accuracy_score,
        top_prediction= top_label,
        is_correct    = is_correct,
        status_label  = status_label,
        feedback      = feedback,
    )


# ============================================================
# ROUTER — Sessions (kelompok latihan)
# ============================================================
session_router = APIRouter(prefix="/sessions", tags=["Sesi Latihan"])

@session_router.post("/start")
def start_session(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    session_id = str(uuid.uuid4())
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, user_id) VALUES (%s, %s)",
        (session_id, current_user["id"])
    )
    db.commit()
    return {"session_id": session_id, "started_at": datetime.utcnow().isoformat()}


@session_router.post("/{session_id}/end")
def end_session(session_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE sessions SET ended_at = NOW() WHERE id = %s AND user_id = %s",
        (session_id, current_user["id"])
    )
    db.commit()
    return {"message": "Sesi selesai"}


# ============================================================
# ROUTER — Riwayat & Dashboard
# ============================================================
history_router = APIRouter(prefix="/history", tags=["Riwayat & Dashboard"])

@history_router.get("/", response_model=List[HistoryItem])
def get_history(
    limit  : int  = 20,
    offset : int  = 0,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Riwayat evaluasi terbaru pengguna."""
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT e.id, h.base_letter, h.harakat, h.arabic_script,
               e.accuracy_score, e.is_correct,
               CAST(e.created_at AS CHAR) AS created_at
        FROM evaluations e
        JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        ORDER BY e.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (current_user["id"], limit, offset)
    )
    return cursor.fetchall()


@history_router.get("/weekly")
def get_weekly_scores(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Grafik akurasi 7 hari terakhir untuk halaman Riwayat."""
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            DATE(created_at)       AS tanggal,
            ROUND(AVG(accuracy_score), 2) AS rata_rata,
            COUNT(*)               AS jumlah_latihan
        FROM evaluations
        WHERE user_id = %s
          AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at)
        ORDER BY tanggal ASC
        """,
        (current_user["id"],)
    )
    return cursor.fetchall()


@history_router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Statistik ringkas untuk halaman Dashboard."""
    cursor = db.cursor(dictionary=True)
    uid = current_user["id"]

    # Total latihan & rata-rata akurasi
    cursor.execute(
        "SELECT COUNT(*) AS total, ROUND(AVG(accuracy_score),2) AS avg_score FROM evaluations WHERE user_id=%s",
        (uid,)
    )
    stats = cursor.fetchone()

    # Huruf terlemah (rata-rata akurasi terendah, min 3 percobaan)
    cursor.execute(
        """
        SELECT h.base_letter, ROUND(AVG(e.accuracy_score),2) AS avg_score
        FROM evaluations e JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        GROUP BY h.base_letter
        HAVING COUNT(*) >= 3
        ORDER BY avg_score ASC LIMIT 1
        """, (uid,)
    )
    lemah = cursor.fetchone()

    # Huruf terkuat
    cursor.execute(
        """
        SELECT h.base_letter, ROUND(AVG(e.accuracy_score),2) AS avg_score
        FROM evaluations e JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        GROUP BY h.base_letter
        HAVING COUNT(*) >= 3
        ORDER BY avg_score DESC LIMIT 1
        """, (uid,)
    )
    kuat = cursor.fetchone()

    # Streak (jumlah hari berturut-turut latihan — sederhana)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT DATE(created_at)) AS streak
        FROM evaluations
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (uid,)
    )
    streak_row = cursor.fetchone()

    return DashboardStats(
        total_latihan     = stats["total"] or 0,
        rata_rata_akurasi = stats["avg_score"] or 0.0,
        streak_hari       = streak_row["streak"] or 0,
        huruf_terlemah    = lemah["base_letter"] if lemah else None,
        huruf_terkuat     = kuat["base_letter"]  if kuat  else None,
    )


# ============================================================
# MOUNT ROUTERS
# ============================================================
app.include_router(auth_router)
app.include_router(letter_router)
app.include_router(eval_router)
app.include_router(session_router)
app.include_router(history_router)


# ============================================================
# ROOT ENDPOINT
# ============================================================
@app.get("/")
def root():
    return {
        "app"    : "Tarteel Space API",
        "version": "1.0.0",
        "status" : "running",
        "docs"   : "/docs",
    }