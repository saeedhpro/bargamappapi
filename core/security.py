from datetime import datetime, timedelta

from jose import jwt

from core.config import settings


def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=6000)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
