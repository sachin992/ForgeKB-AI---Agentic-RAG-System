from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User


def _resolve_role(requested_role: str) -> str:
    role = (requested_role or "user").strip().lower()
    if role == "admin":
        return "admin"
    return "user"


def register_user(db: Session, email: str, password: str, requested_role: str = "user") -> dict:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(email=email, role=_resolve_role(requested_role), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_access_token(user.email, user.role, user.id),
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }


def login_user(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {
        "access_token": create_access_token(user.email, user.role, user.id),
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }
