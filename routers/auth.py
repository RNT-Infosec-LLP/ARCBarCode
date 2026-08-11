"""Authentication routes: register (helper) and login."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    hash_password,
    is_account_locked,
    record_failed_login,
    reset_failed_logins,
    verify_password,
)
from database import get_db
from models import User
from schemas import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user. Useful for initial setup / admin invites."""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Validate credentials and return a JWT access token.

    Enforces an account lockout policy: after too many consecutive failed
    attempts, the account is temporarily locked regardless of whether the
    correct password is supplied afterwards, until the lockout window elapses.
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    if user and is_account_locked(user):
        minutes_left = max(1, int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed login attempts. Try again in {minutes_left} minute(s).",
        )

    if not user or not verify_password(credentials.password, user.hashed_password):
        if user:
            record_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    reset_failed_logins(db, user)
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token)
