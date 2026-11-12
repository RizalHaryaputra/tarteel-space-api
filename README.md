# Tarteel Space API 🚀

Backend API untuk aplikasi **Tarteel Space** — platform evaluasi pelafalan huruf hijaiyah berbasis Artificial Intelligence (AI). Dibangun menggunakan **FastAPI**, **LiteRT (TensorFlow Lite)**, dan **MySQL**.

## ✨ Fitur Utama
- **Autentikasi Pengguna**: Registrasi, Login, dan manajemen token JWT yang aman.
- **Single Sign-On (SSO)**: Mendukung integrasi OAuth 2.0 untuk login via Google dan GitHub.
- **Pemulihan Akun**: Fitur lupa & reset password menggunakan token aman dan notifikasi email via SMTP Gmail.
- **Evaluasi Pelafalan (AI CNN)**: Mengekstrak fitur audio (MFCC) dengan Librosa dan memprediksi keakuratan pelafalan menggunakan model Convolutional Neural Network (CNN) berbasis LiteRT (TensorFlow Lite).
- **Sistem Umpan Balik Tiga Tingkat (Score-based Feedback)**: Mengkategorikan hasil pelafalan secara dinamis berdasarkan skor akurasi:
  - **Sangat Baik** (skor $\ge$ 80%)
  - **Cukup Baik** (skor 60% – 79%)
  - **Perlu Latihan** (skor < 60%)
- **Benchmarking Waktu Respons (Skripsi Testing)**: Pencatatan otomatis waktu inferensi model (`inference_ms`) dan waktu respons ujung-ke-ujung klien (`client_e2e_ms`) ke berkas CSV persisten (`logs/benchmark_latency.csv`), lengkap dengan endpoint pengunduhan log langsung.
- **Rate Limiting & Anti-Abuse (SlowAPI)**: Proteksi pembatasan laju permintaan untuk mencegah serangan *brute force*, spam bot, dan kelebihan beban CPU:
  - Auth Login: 5 req / menit
  - Auth Register: 5 req / jam
  - Lupa & Reset Password: 3–5 req / 15 menit
  - Evaluasi AI: 30 req / menit
  - Pembaruan Password & Avatar: 5 req / 10–15 menit
- **Manajemen Sesi & Riwayat**: Mencatat setiap sesi latihan dan skor evaluasi beserta rekaman audionya yang tersimpan aman di **Cloudinary**.
- **Dashboard Statistik & Admin**: Menyediakan ringkasan performa harian pengguna, tren latihan 7 hari terakhir, manajemen huruf hijaiyah (84 kombinasi huruf & harakat), serta verifikasi laporan pelafalan pengguna (*feedback validation*).
- **Persetujuan Privasi Data Audio**: Mekanisme *opt-in* bagi pengguna yang bersedia menyumbangkan rekaman suaranya ke *dataset pool* untuk keperluan penelitian (*active learning*).

## 🛠️ Teknologi yang Digunakan
- **Framework Web**: FastAPI (Uvicorn dengan `--proxy-headers` untuk integrasi Cloudflare/Reverse Proxy)
- **Machine Learning & Audio**: LiteRT (`ai-edge-litert`), Librosa, NumPy, PyAV (`av`)
- **Database**: MySQL (MySQL Connector Python + Connection Pooling, kompatibel dengan MySQL 8.0+)
- **Penyimpanan Cloud**: Cloudinary SDK (Audio & Avatar Pengguna)
- **Keamanan & Rate Limiting**: SlowAPI, Limits, Passlib (Bcrypt), python-jose (JWT), Authlib (OAuth 2.0)
- **Email & Utilitas**: smtplib (SMTP Gmail), httpx, python-dotenv

## 📋 Persyaratan Sistem
- Python 3.11 atau lebih baru
- MySQL Server 8.0+ / MariaDB
- Akun Cloudinary (untuk penyimpanan audio)
- Akun Google / GitHub Developer (opsional, untuk SSO)

## 🚀 Cara Instalasi & Menjalankan

### 1. Setup Lingkungan Virtual (Virtual Environment)
```bash
python -m venv venv

# Aktivasi di Windows (PowerShell):
venv\Scripts\Activate.ps1

# Aktivasi di Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependensi
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables
Salin format dari `.env.example` atau buat file `.env` baru di *root* direktori:
```env
# Keamanan & Web
SECRET_KEY=secret_kunci_jwt_anda
SESSION_SECRET_KEY=kunci_rahasia_sesi
FRONTEND_URL=https://tarteelspace.web.id,http://localhost:3000

# Database MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_DATABASE=db_tarteel_space
DB_SSL_DISABLED=True

# Konfigurasi SMTP (Reset Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email_anda@gmail.com
SMTP_PASSWORD=16_digit_app_password

# Kredensial OAuth (SSO)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Cloudinary (Penyimpanan Audio & Avatar)
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### 4. Setup Database MySQL
1. Pastikan server MySQL berjalan.
2. Buat database bernama `db_tarteel_space`.
3. Import file `db_tarteel_space_clean.sql` yang sudah bersih dan kompatibel penuh dengan MySQL 8.0+ (berisi 84 huruf hijaiyah terisi lengkap).

### 5. Konfigurasi Model AI
Pastikan berkas bobot model telah tersedia di folder `model/`:
- `hijaiyah_model_full_aug.tflite` (Model CNN TFLite - 84 kelas)
- `label_mapping.json` (Pemetaan 84 kelas label)
- `norm_mean_full_aug.npy` & `norm_std_full_aug.npy` (Statistik normalisasi Z-Score MFCC)
- `preprocessing_params.json` (Parameter pra-pemrosesan & MFCC)

### 6. Menjalankan Server Lokal
```bash
uvicorn main:app --reload --port 8000
```
- API Base URL: `http://localhost:8000`
- Dokumentasi Interaktif (Swagger UI): `http://localhost:8000/docs`

---

## 🐳 Kontainerisasi & Deployment (Docker / Coolify)

Proyek ini telah dikonfigurasi menggunakan Dockerfile yang dioptimalkan untuk Coolify / VPS:

### 1. Build & Run Docker Lokal
```bash
docker build -t tarteel-space-api .
docker run -p 8000:8000 --env-file .env tarteel-space-api
```

### 2. Deployment di Coolify
- **Build Pack**: Dockerfile.
- **Port Expose**: `8000`.
- **Persistent Storage (Volume)**: Sangat disarankan menambahkan volume untuk menjaga keutuhan log benchmark:
  - Destination Path: `/app/logs`
- **Reverse Proxy / Cloudflare**: Uvicorn sudah otomatis dikonfigurasi dengan flag `--proxy-headers --forwarded-allow-ips='*'` untuk membaca IP asli klien di balik Cloudflare/Traefik.

---

## 📂 Struktur Direktori Utama
```text
tarteel-space-api/
├── api/
│   ├── deps.py              # Dependency injection (Auth JWT, Database connection)
│   └── routers/             # Endpoint modular (auth, evaluate, letters, history, admin, profile, dsb.)
├── core/
│   ├── config.py            # Pembaca environment variable & konfigurasi CORS
│   ├── limiter.py           # Inisialisasi Rate Limiter (SlowAPI)
│   └── security.py          # Enkripsi password (Bcrypt) & pembuatan token JWT
├── db/
│   └── database.py          # MySQL Connection Pool
├── logs/                    # Berkas log benchmarking waktu respons (benchmark_latency.csv)
├── model/                   # Model LiteRT (.tflite), label mapping, & bobot normalisasi
├── schemas/                 # Data validation & response schema (Pydantic)
├── services/
│   ├── cloudinary_service.py # Pengunggahan audio & gambar ke Cloudinary
│   ├── email_service.py      # Pengiriman email reset password via SMTP
│   └── ml_service.py         # Ekstraksi MFCC audio & inferensi CNN
├── Dockerfile               # Konfigurasi container produksi
├── requirements.txt         # Dependensi Python
└── main.py                  # Entrypoint aplikasi FastAPI
```

---
**Tarteel Space API** | Dikembangkan untuk Penelitian Tugas Akhir / Skripsi | 2026
