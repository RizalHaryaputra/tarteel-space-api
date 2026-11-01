from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled=True otomatis menambahkan header X-RateLimit dan Retry-After (dalam detik)
limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=True
)
