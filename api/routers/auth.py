import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import get_db
from core.security import hash_password, verify_password, create_access_token
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from schemas.auth import RegisterRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest
from services.email_service import send_reset_email

router = APIRouter(prefix="/auth", tags=["Autentikasi"])

RESET_TOKEN_EXPIRE_MINUTES = 15

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    if cursor.fetchone():
        raise HTTPException(400, "Email sudah terdaftar")

    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (id, name, email, password_hash) VALUES (%s, %s, %s, %s)",
        (user_id, req.name, req.email, hash_password(req.password))
    )
    db.commit()
    return {"message": "Akun berhasil dibuat", "user_id": user_id}

@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (form.username,))
    user = cursor.fetchone()

    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )

    token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(
        access_token=token,
        user_name=user["name"],
        user_id=user["id"]
    )

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, background_tasks: BackgroundTasks, db=Depends(get_db)):
    """
    Kirim link reset password ke email pengguna.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(404, "Email tidak terdaftar dalam sistem.")

    # Generate token acak yang kuat (32 byte = 64 karakter hex)
    reset_token = secrets.token_hex(32)
    token_id    = str(uuid.uuid4())
    expires_at  = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    # Hapus token lama yang belum dipakai untuk user yang sama
    cursor.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = %s AND used = 0",
        (user["id"],)
    )

    cursor.execute(
        "INSERT INTO password_reset_tokens (id, user_id, token, expires_at) VALUES (%s, %s, %s, %s)",
        (token_id, user["id"], reset_token, expires_at)
    )
    db.commit()

    # Kirim email di background agar response tidak menunggu
    background_tasks.add_task(send_reset_email, req.email, reset_token)
    print(f"[Auth] Reset password requested for: {req.email}")

    return {"message": "Link reset password telah dikirim ke email Anda."}

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db=Depends(get_db)):
    """
    Validasi token dan perbarui password pengguna.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM password_reset_tokens WHERE token = %s AND used = 0",
        (req.token,)
    )
    token_row = cursor.fetchone()

    if not token_row:
        raise HTTPException(400, "Link reset password tidak valid atau sudah digunakan.")

    # Cek apakah token sudah kedaluwarsa
    if datetime.utcnow() > token_row["expires_at"]:
        raise HTTPException(400, "Link reset password sudah kedaluwarsa. Silakan minta link baru.")

    # Validasi password baru
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password baru minimal 8 karakter.")

    # Update password
    new_hash = hash_password(req.new_password)
    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_hash, token_row["user_id"])
    )

    # Tandai token sebagai sudah digunakan
    cursor.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE id = %s",
        (token_row["id"],)
    )
    db.commit()

    print(f"[Auth] Password successfully reset for user_id: {token_row['user_id']}")
    return {"message": "Password berhasil diperbarui. Silakan login dengan password baru Anda."}
