from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_db

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

@router.get("/{letter_id}")
def get_letter(letter_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")
    return letter
