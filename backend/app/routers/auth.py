from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import verify_password, create_access_token
from app.schemas import TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is inactive")
    
    # Update last_login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token(user.username)
    user_out = UserOut.model_validate(user)
    return TokenOut(access_token=token, user=user_out, username=user.username, role=user.role)


@router.get("/me", response_model=UserOut)
def get_me(db: Session = Depends(get_db), user: User = Depends(__import__("app.auth", fromlist=["get_current_user"]).get_current_user)):
    """Get current authenticated user info"""
    return UserOut.model_validate(user)
