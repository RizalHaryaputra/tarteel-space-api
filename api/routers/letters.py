from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from api.deps import get_db
from core.config import AUDIO_DIR

router = APIRouter(prefix="/letters", tags=["Huruf Hijaiyah"])

@router.get("/")
def get_all_letters(db=Depends(get_db)):
    """Ambil semua 84 huruf untuk ditampilkan di halaman latihan."""
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, base_letter, harakat, pronunciation, arabic_script "
        "FROM hijaiyah_letters ORDER BY id"
    )
    return cursor.fetchall()

@router.get("/{letter_id}/audio")
def get_letter_audio(letter_id: int, db=Depends(get_db)):
    """Streaming file audio referensi pelafalan huruf berdasarkan letter_id."""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    if not cursor.fetchone():
        raise HTTPException(404, "Huruf tidak ditemukan")

    audio_file = AUDIO_DIR / f"{letter_id}.wav"
    if not audio_file.exists():
        raise HTTPException(404, f"File audio untuk huruf ID {letter_id} belum tersedia")

    return FileResponse(
        path=str(audio_file),
        media_type="audio/wav",
        filename=f"{letter_id}.wav",
    )

@router.get("/{letter_id}")
def get_letter(letter_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")
    return letter
