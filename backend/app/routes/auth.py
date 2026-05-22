import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.database import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import hash_password, verify_password, create_access_token, get_current_user, oauth2_scheme
from app.services.cache_service import set_cached
from app.limiter import limiter

logger = structlog.get_logger().bind(service="auth")

auth_router = APIRouter()


@auth_router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    user_exists = session.exec(
        select(User).where((User.email == user_data.email) | (User.username == user_data.username))
    ).first()
    if user_exists:
        if user_exists.email == user_data.email:
            logger.warning("register_conflict", email=user_data.email, reason="email_taken")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")
        logger.warning("register_conflict", username=user_data.username, reason="username_taken")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this username already exists")
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    logger.info("user_registered", username=new_user.username, email=new_user.email)
    return new_user


@auth_router.post('/login', response_model=Token, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(
        select(User).where((User.email == form_data.username) | (User.username == form_data.username))
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("login_failed", credential=form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"email": user.email})
    logger.info("user_logged_in", email=user.email)
    return Token(access_token=access_token, token_type="bearer")


@auth_router.delete('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    set_cached(f"blacklist:{token}", "1", ttl=3600)
    logger.info("user_logged_out", email=current_user.email)
    return None
