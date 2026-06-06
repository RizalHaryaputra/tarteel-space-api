# Tarteel Space API 🚀

Backend API untuk aplikasi **Tarteel Space** — platform evaluasi pelafalan huruf hijaiyah berbasis Artificial Intelligence (AI). Dibangun menggunakan **FastAPI**, **LiteRT (TensorFlow Lite)**, dan **MySQL**.

## ✨ Fitur Utama
- **Autentikasi Pengguna**: Registrasi, Login, dan manajemen token JWT yang aman.
- **Single Sign-On (SSO)**: Mendukung integrasi OAuth 2.0 untuk login via Google dan GitHub.
- **Pemulihan Akun**: Fitur lupa & reset password menggunakan token aman dan notifikasi email via SMTP.
- **Evaluasi Pelafalan (AI)**: Mengekstrak fitur audio (MFCC) dengan Librosa dan memprediksi keakuratan pelafalan menggunakan model Convolutional Neural Network (CNN).
- **Manajemen Sesi & Riwayat**: Mencatat setiap sesi latihan dan skor evaluasi.
- **Dashboard Statistik**: Memberikan ringkasan performa harian pengguna, streak latihan, dan menganalisis huruf terlemah/terkuat.
- **Panel Kontrol Admin**: Menyediakan endpoint statistik menyeluruh, manajemen daftar pengguna, dan manajemen huruf hijaiyah.
- **Active Learning Loop**: Mendukung fitur pelaporan (feedback) dari pengguna atas prediksi yang salah, dan mengizinkan admin untuk memvalidasi rekaman sebagai *ground truth* baru.
- **Dataset Pool & Ekspor**: Mengagregasi data rekaman audio yang tervalidasi untuk keperluan *retraining* model AI, serta dapat diekspor langsung ke format CSV atau JSON.

## 🛠️ Teknologi yang Digunakan
- **Framework Web**: FastAPI (Uvicorn)
- **Machine Learning**: LiteRT (ai-edge-litert), TensorFlow (lokal fallback), Librosa, Numpy
- **Database**: MySQL (MySQL Connector Python + Pooling, mendukung SSL & Custom Port)
- **Keamanan & Autentikasi**: Passlib (Bcrypt - pinned ke versi 3.2.0), python-jose (JWT), Authlib (OAuth 2.0)
- **Email & Utilitas**: smtplib, httpx, python-dotenv

## 📋 Persyaratan Sistem
- Python 3.11 atau lebih baru
- MySQL Server (misalnya XAMPP atau MySQL native)

## 🚀 Cara Instalasi & Menjalankan

### 1. Setup Lingkungan Virtual (Virtual Environment)
Disarankan menggunakan virtual environment agar dependensi tidak bentrok.
```bash
python -m venv venv

# Aktivasi Virtual Environment di Windows:
venv\Scripts\activate

# Aktivasi di Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependensi
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables
1. Salin format dari `.env.example` atau buat file `.env` baru di *root* direktori.
2. Atur kredensial database (username, password), *secret key* JWT, dan lokasi model.
   Contoh `.env`:
   ```env
   # Keamanan & Web
   SECRET_KEY=secret_anda
   FRONTEND_URL=http://localhost:3000

   # Database MySQL
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=
   DB_DATABASE=db_tarteel_space

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
   SESSION_SECRET_KEY=kunci_rahasia_sesi
   ```

### 4. Setup Database MySQL
1. Pastikan server MySQL lokal Anda sedang berjalan atau siapkan database managed di cloud (seperti Aiven.io).
2. Buat database baru bernama `db_tarteel_space` (sesuai `DB_DATABASE` di `.env`).
3. Import skema tabel `db_tarteel_space.sql` ke dalam database tersebut. File SQL ini sudah disesuaikan agar kompatibel dengan MySQL 8.0+ / Aiven (memiliki tanda kurung pada default `(UUID())` dan melewati batasan aturan primary key secara otomatis selama proses impor).

### 5. Konfigurasi Model AI
Pastikan file pendukung model sudah berada pada folder `model/` (bisa diatur via `.env`):
- `hijaiyah_model.tflite` (Model Utama TFLite)
- `label_mapping.json` (Pemetaan label indeks kelas)
- `norm_mean.npy` & `norm_std.npy` (Data statistik normalisasi Z-score)

### 6. Jalankan Server Secara Lokal
Untuk menjalankan server secara lokal (Windows) menggunakan virtual environment:
1. Pastikan variabel di `.env` lokal Anda mengarah ke `DB_SSL_DISABLED=True` (jika MySQL lokal Anda tidak menggunakan SSL).
2. Aktifkan mode UTF-8 pada terminal Windows Anda agar emoji tidak memicu error *Unicode*:
   ```bash
   $env:PYTHONUTF8=1 # Di PowerShell
   ```
3. Jalankan server menggunakan Uvicorn:
   ```bash
   venv\Scripts\python.exe -m uvicorn main:app --reload
   ```
Server akan berjalan di: `http://localhost:8000` dan Dokumentasi API interaktif di: **http://localhost:8000/docs**

---

## 🐳 Kontainerisasi & Deployment (Docker & Cloud)

Proyek ini sudah dilengkapi dengan konfigurasi Docker siap pakai untuk deployment di platform cloud berbasis container (seperti **Railway.app** atau **Render.com**):

### 1. Build Docker Image Secara Lokal
Untuk melakukan build image secara lokal:
```bash
docker build -t tarteel-space-api .
```
*(Ukuran build context sangat ringan (~11 MB) karena dilindungi oleh file `.dockerignore`)*

### 2. Jalankan Container Secara Lokal
Pastikan `.env` telah disesuaikan (masukkan kredensial database Aiven Anda jika ingin mengetes koneksi cloud, dan pastikan `DB_SSL_DISABLED=False`):
```bash
docker run -p 8000:8000 --env-file .env tarteel-space-api
```
*(Catatan: Jika port 8000 dialokasikan untuk proses lain, Anda dapat memetakannya ke port lain, misal `-p 8001:8000`)*

### 3. Variabel Lingkungan di Cloud (Railway/Render)
Saat mendeploy di cloud, pastikan untuk menyetel environment variables berikut pada dashboard Anda:
* `DB_HOST` = `<host_database_aiven_atau_lain>`
* `DB_PORT` = `<port_database_aiven>`
* `DB_USER` = `<username_database>`
* `DB_PASSWORD` = `<password_database>`
* `DB_DATABASE` = `<nama_database>`
* `DB_SSL_DISABLED` = `False`
* `FRONTEND_URL` = `https://<nama-app-anda>.vercel.app` (URL frontend Vercel Anda)
* `SECRET_KEY` = `<token_acak>`
* `SESSION_SECRET_KEY` = `<token_acak_lain>`

## 📂 Struktur Direktori Utama
Proyek ini mengadopsi arsitektur modular standar FastAPI untuk kemudahan pemeliharaan:
- `api/` : Berisi *routers* (endpoint API) yang dipisah per-fitur (auth, oauth, evaluate, letters, dsb.) dan komponen *dependencies* (seperti autentikasi & DB).
- `core/` : Menyimpan konfigurasi global (`config.py`) yang membaca file `.env` dan utilitas keamanan (hashing, JWT).
- `db/` : Berisi konfigurasi dan setup *connection pool* untuk MySQL.
- `schemas/` : Mendefinisikan struktur data I/O (Request/Response) menggunakan Pydantic.
- `services/` : Menyimpan logika inti (*business logic*), seperti `ml_service.py` untuk pemrosesan audio (MFCC) & inferensi CNN, serta `email_service.py` untuk pengiriman email.
- `model/` : Direktori untuk menampung bobot model `.keras` dan status normalisasi.
- `uploads/audio/` : Menyimpan file audio rekaman pengguna yang masuk.
- `main.py` : Berfungsi secara eksklusif sebagai *entrypoint* aplikasi dan memuat router.

---
**Tarteel Space API** | Dikembangkan oleh **Rizal Haryaputra** | Teknologi Informasi UNY | 2026
