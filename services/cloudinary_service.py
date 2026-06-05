import os
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True
)

def upload_audio_to_cloudinary(audio_bytes: bytes, filename: str, folder: str = "tarteel_space") -> str:
    """
    Mengunggah raw audio bytes ke Cloudinary dan mengembalikan secure URL (https).
    """
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    if not cloud_name:
        raise ValueError("Cloudinary belum dikonfigurasi di server (.env)")

    try:
        response = cloudinary.uploader.upload(
            audio_bytes,
            resource_type="video",  # Audio file (wav) diunggah menggunakan resource_type='video'
            public_id=filename,
            folder=folder,
            overwrite=True
        )
        return response.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah audio ke Cloudinary: {str(e)}")
