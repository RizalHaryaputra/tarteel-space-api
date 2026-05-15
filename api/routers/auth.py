import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import get_db
from core.security import hash_password, verify_password, create_access_token
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from schemas.auth import RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autentikasi"])

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
