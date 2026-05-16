import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),               
    "database": os.getenv("DB_DATABASE", "db_tarteel_space"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
}

MODEL_PATH = os.getenv("MODEL_PATH", "./model/hijaiyah_model_final.keras")
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH", "./model/label_mapping.json")
NORM_MEAN_PATH = os.getenv("NORM_MEAN_PATH", "./model/norm_mean.npy")
NORM_STD_PATH = os.getenv("NORM_STD_PATH", "./model/norm_std.npy")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads/audio"))
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./audio"))

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "22050"))
DURATION = float(os.getenv("DURATION", "2.0"))
MAX_LEN = int(SAMPLE_RATE * DURATION)
N_MFCC = int(os.getenv("N_MFCC", "40"))
N_FFT = int(os.getenv("N_FFT", "2048"))
HOP_LEN = int(os.getenv("HOP_LEN", "512"))
THRESHOLD = float(os.getenv("THRESHOLD", "70.0"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "2.0"))
