from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
COOKIE_NAME = "life_epm_session"


# Le hachage et la vérification des mots de passe utilisent pwdlib.
def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


# Les routes placent le jeton JWT à durée limitée dans un cookie HTTP-only.
def create_session_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


# Vérifie l'identité et les rôles avant l'accès aux routes protégées.
def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ce compte est inactif.")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous devez modifier votre mot de passe provisoire avant de continuer.",
            )
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits nécessaires.")
        return user

    return dependency
