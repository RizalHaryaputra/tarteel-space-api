# Gunakan base image Python resmi yang ringan (Debian-slim)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Tentukan working directory
WORKDIR /app

# Instal dependensi sistem yang dibutuhkan oleh librosa/soundfile (libsndfile) dan av (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Salin requirements.txt terlebih dahulu untuk efisiensi caching layer
COPY requirements.txt .

# Instal dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh isi proyek ke dalam container
COPY . .

# Buat folder untuk upload audio (opsional, jika dinamis)
RUN mkdir -p uploads/audio

# Expose port (default 8000, tetapi akan disesuaikan secara dinamis oleh host)
EXPOSE 8000

# Jalankan server uvicorn secara dinamis menggunakan port dari environment variable (default: 8000)
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port \${PORT:-8000}"
