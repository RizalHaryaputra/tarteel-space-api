# Tarteel Space API 🚀

Backend API untuk aplikasi **Tarteel Space** — platform evaluasi pelafalan huruf hijaiyah berbasis Artificial Intelligence (AI). Dibangun menggunakan **FastAPI**, **TensorFlow/Keras**, dan **MySQL**.

## ✨ Fitur Utama
- **Autentikasi Pengguna**: Registrasi, Login, dan manajemen token JWT yang aman.
- **Single Sign-On (SSO)**: Mendukung integrasi OAuth 2.0 untuk login via Google dan GitHub.
- **Pemulihan Akun**: Fitur lupa & reset password menggunakan token aman dan notifikasi email via SMTP.
- **Evaluasi Pelafalan (AI)**: Mengekstrak fitur audio (MFCC) dengan Librosa dan memprediksi keakuratan pelafalan menggunakan model Convolutional Neural Network (CNN).
- **Manajemen Sesi & Riwayat**: Mencatat setiap sesi latihan dan skor evaluasi.
- **Dashboard Statistik**: Memberikan ringkasan performa harian pengguna, streak latihan, dan menganalisis huruf terlemah/terkuat.

## 🛠️ Teknologi yang Digunakan
- **Framework Web**: FastAPI (Uvicorn)
- **Machine Learning**: TensorFlow (Keras), Librosa, Numpy
- **Database**: MySQL (MySQL Connector Python + Pooling)
- **Keamanan & Autentikasi**: Passlib (Bcrypt), python-jose (JWT), Authlib (OAuth 2.0)
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
1. Pastikan server MySQL lokal Anda sedang berjalan.
2. Buat database baru bernama `db_tarteel_space` (sesuai `DB_DATABASE` di `.env`).
3. Import skema tabel `.sql` (berisi struktur tabel `users`, `hijaiyah_letters`, `evaluations`, `sessions`) ke dalam database tersebut.

### 5. Konfigurasi Model AI
Pastikan file pendukung model sudah berada pada folder `model/` (bisa diatur via `.env`):
- `hijaiyah_model_final.keras` (Model Utama Keras)
- `label_mapping.json` (Pemetaan label indeks kelas)
- `norm_mean.npy` & `norm_std.npy` (Data statistik normalisasi Z-score)

### 6. Jalankan Server
Gunakan Uvicorn untuk menjalankan server secara lokal:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Server akan berjalan di: `http://localhost:8000`

Anda dapat melihat Dokumentasi API interaktif secara otomatis di: **http://localhost:8000/docs**

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
