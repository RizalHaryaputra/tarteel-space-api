import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
_raw_frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
FRONTEND_URL = _raw_frontend.split(",")[0].strip().rstrip("/")
_raw_origins = [u.strip().rstrip("/") for u in _raw_frontend.split(",") if u.strip()]
CORS_ORIGINS = list(set(_raw_origins + ["http://localhost:3000", "http://127.0.0.1:3000"]))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "fallback_session_secret")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "db_tarteel_space"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    "ssl_disabled": os.getenv("DB_SSL_DISABLED", "False").lower() in ("true", "1", "yes"),
}

MODEL_PATH = os.getenv("MODEL_PATH", "./model/hijaiyah_model.tflite")
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH", "./model/label_mapping.json")
NORM_MEAN_PATH = os.getenv("NORM_MEAN_PATH", "./model/norm_mean.npy")
NORM_STD_PATH = os.getenv("NORM_STD_PATH", "./model/norm_std.npy")

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "22050"))
DURATION = float(os.getenv("DURATION", "2.0"))
MAX_LEN = int(SAMPLE_RATE * DURATION)
N_MFCC = int(os.getenv("N_MFCC", "40"))
N_FFT = int(os.getenv("N_FFT", "2048"))
HOP_LEN = int(os.getenv("HOP_LEN", "512"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "2.0"))
