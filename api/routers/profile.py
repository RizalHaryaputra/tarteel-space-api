from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from api.deps import get_current_user, get_db
from schemas.profile import ProfileResponse, ProfileUpdateRequest, PasswordUpdateRequest
from core.security import verify_password, hash_password
from services.cloudinary_service import upload_image_to_cloudinary

router = APIRouter(prefix="/profile", tags=["Profil"])

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role, auth_provider, avatar_url, bio FROM users WHERE id = %s", (current_user["id"],))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    return user

@router.put("/me")
def update_profile(req: ProfileUpdateRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT auth_provider, email FROM users WHERE id = %s", (current_user["id"],))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
        
    if user['auth_provider'] != 'local' and user['email'] != req.email:
        raise HTTPException(400, "Tidak dapat mengubah email untuk akun SSO.")
        
    if user['email'] != req.email:
        # Cek apakah email baru sudah dipakai
        cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (req.email, current_user['id']))
        if cursor.fetchone():
            raise HTTPException(400, "Email sudah digunakan oleh akun lain.")

    cursor.execute(
        "UPDATE users SET name = %s, email = %s, bio = %s WHERE id = %s",
        (req.name, req.email, req.bio, current_user["id"])
    )
    db.commit()
    return {"message": "Profil berhasil diperbarui"}

@router.put("/me/password")
def update_password(req: PasswordUpdateRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT auth_provider, password_hash FROM users WHERE id = %s", (current_user["id"],))
    user = cursor.fetchone()
    
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
        
    if user['auth_provider'] != 'local':
        raise HTTPException(400, "Akun SSO tidak dapat mengubah password di sini.")
        
    if not verify_password(req.old_password, user['password_hash']):
        raise HTTPException(400, "Password lama salah.")
        
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password baru minimal 8 karakter.")
        
    new_hash = hash_password(req.new_password)
    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, current_user['id']))
    db.commit()
    return {"message": "Password berhasil diperbarui"}

@router.put("/me/avatar")
async def update_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(400, "Format gambar tidak didukung. Gunakan JPG, PNG, atau WEBP.")
        
    try:
        content = await file.read()
        file_url = upload_image_to_cloudinary(content, f"avatar_{current_user['id']}")
        
        cursor = db.cursor()
        cursor.execute("UPDATE users SET avatar_url = %s WHERE id = %s", (file_url, current_user['id']))
        db.commit()
        return {"message": "Foto profil berhasil diperbarui", "avatar_url": file_url}
    except Exception as e:
        raise HTTPException(500, f"Gagal mengunggah foto profil: {str(e)}")

@router.delete("/me/avatar")
def delete_avatar(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE users SET avatar_url = NULL WHERE id = %s", (current_user['id'],))
    db.commit()
    
    from services.cloudinary_service import delete_image_from_cloudinary
    delete_image_from_cloudinary(f"tarteel_space_avatars/avatar_{current_user['id']}")
    
    return {"message": "Foto profil berhasil dihapus"}
