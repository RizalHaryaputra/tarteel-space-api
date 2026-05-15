from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from core.config import SECRET_KEY, ALGORITHM
from db.database import get_db_connection

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    """Dependency: ambil koneksi dari pool, kembalikan setelah selesai."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def get_current_user(token: str = Depends(oauth2), db=Depends(get_db)) -> dict:
    """Dependency: validasi JWT dan kembalikan data user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kadaluarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user is None:
        raise credentials_exception
    return user
