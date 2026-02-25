from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token
from app.services import user_service
from app.schemas.user import User, UserCreate, Token
from app.config import settings
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=User)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = user_service.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    db_user = user_service.get_user_by_username(db, username=user_in.username)
    if db_user:
        raise HTTPException(status_code=400, detail="该用户名已被注册")
    return user_service.create_user(db, user_in=user_in)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = user_service.authenticate_user(
        db, username_or_email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user
