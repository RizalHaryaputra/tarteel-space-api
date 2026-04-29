# Tarteel Space API 🚀

Backend API untuk aplikasi **Tarteel Space** — platform evaluasi pelafalan huruf hijaiyah berbasis Artificial Intelligence (AI). Dibangun menggunakan **FastAPI**, **TensorFlow/Keras**, dan **MySQL**.

## ✨ Fitur Utama
- **Autentikasi Pengguna**: Registrasi dan Login yang aman menggunakan token JWT.
- **Evaluasi Pelafalan (AI)**: Mengekstrak fitur audio (MFCC) dengan Librosa dan memprediksi keakuratan pelafalan menggunakan model Convolutional Neural Network (CNN).
- **Manajemen Sesi & Riwayat**: Mencatat setiap sesi latihan dan skor evaluasi.
- **Dashboard Statistik**: Memberikan ringkasan performa harian pengguna, streak latihan, dan menganalisis huruf terlemah/terkuat.

## 🛠️ Teknologi yang Digunakan
- **Framework Web**: FastAPI (Uvicorn)
- **Machine Learning**: TensorFlow (Keras), Librosa, Numpy
- **Database**: MySQL (MySQL Connector Python + Pooling)
- **Keamanan**: Passlib (Bcrypt), python-jose (JWT)

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

### 3. Setup Database MySQL
1. Pastikan server MySQL lokal Anda sedang berjalan.
2. Buat database baru bernama `db_tarteel_space`.
3. Import skema tabel `.sql` (berisi struktur tabel `users`, `hijaiyah_letters`, `evaluations`, `sessions`) ke dalam database tersebut.
4. Buka file `main.py` dan sesuaikan kredensial di bagian `DB_CONFIG` (username dan password) sesuai server MySQL Anda.

### 4. Konfigurasi Model AI
Pastikan file pendukung model sudah berada pada folder `model/`:
- `hijaiyah_model_final.keras` (Model Utama Keras)
- `label_mapping.json` (Pemetaan label indeks kelas)
- `norm_mean.npy` & `norm_std.npy` (Data statistik normalisasi Z-score)

### 5. Jalankan Server
Gunakan Uvicorn untuk menjalankan server secara lokal:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Server akan berjalan di: `http://localhost:8000`

Anda dapat melihat Dokumentasi API interaktif secara otomatis di: **http://localhost:8000/docs**

## 📂 Struktur Direktori Utama
- `main.py` : Berisi routing, konfigurasi, koneksi database, dan fungsi inferensi AI.
- `model/` : Menyimpan model CNN `.keras` dan file pendukung normalisasi.
- `uploads/audio/` : Menyimpan file audio rekaman pengguna yang masuk.
- `requirements.txt` : Daftar semua dependensi library Python.

---
**Tarteel Space API** | Dikembangkan oleh **Rizal Haryaputra** | Teknologi Informasi UNY | 2026
