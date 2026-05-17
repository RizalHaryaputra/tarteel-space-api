import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

from api.deps import get_db
from core.security import create_access_token
from core.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    FRONTEND_URL,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["OAuth"])

oauth = OAuth()

# Setup Google OAuth
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Setup GitHub OAuth
if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    oauth.register(
        name='github',
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )

@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request):
    """
    Redirect pengguna ke halaman login OAuth provider (Google/GitHub).
    """
    if provider not in ['google', 'github']:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Provider tidak didukung")

    client = oauth.create_client(provider)
    if not client:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Kredensial OAuth belum dikonfigurasi")

    # URL ini harus sama persis dengan yang didaftarkan di Google Console / GitHub Settings
    redirect_uri = str(request.url_for('oauth_callback', provider=provider))
    return await client.authorize_redirect(request, redirect_uri)

@router.get("/callback/{provider}")
async def oauth_callback(provider: str, request: Request, db=Depends(get_db)):
    """
    Menangani callback dari provider OAuth.
    """
    if provider not in ['google', 'github']:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Provider tidak didukung")

    client = oauth.create_client(provider)
    if not client:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Kredensial OAuth belum dikonfigurasi")

    try:
        token = await client.authorize_access_token(request)
    except OAuthError as error:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Autentikasi gagal")

    # Ambil data user dari provider
    user_info = None
    if provider == 'google':
        user_info = token.get('userinfo')
        if not user_info:
            user_info = await client.parse_id_token(request, token)
        email = user_info.get('email')
        name = user_info.get('name')
        
    elif provider == 'github':
        resp = await client.get('user', token=token)
        profile = resp.json()
        name = profile.get('name') or profile.get('login')
        
        # GitHub tidak selalu mengembalikan email di profile utama
        email = profile.get('email')
        if not email:
            email_resp = await client.get('user/emails', token=token)
            emails = email_resp.json()
            # Cari email primary yang terverifikasi
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    email = e['email']
                    break
            if not email and emails:
                email = emails[0]['email']

    if not email:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=Tidak dapat mengambil email dari akun {provider}")

    # Cek database, apakah email sudah ada
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        # Jika belum ada, buat user baru
        user_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO users (id, name, email, auth_provider) VALUES (%s, %s, %s, %s)",
            (user_id, name, email, provider)
        )
        db.commit()
        user = {
            "id": user_id,
            "name": name,
            "email": email
        }

    # Buat JWT token untuk aplikasi Tarteel Space
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Arahkan kembali ke frontend (halaman callback khusus)
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={access_token}&user_id={user['id']}&user_name={user['name']}"
    return RedirectResponse(url=redirect_url)
