import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, func, select
from app.database import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, AuthResponse, LoginRequest, Profile
from app.services.auth_service import hash_password, verify_password, create_access_token, get_current_user, oauth2_scheme
from app.services.cache_service import set_cached
from app.limiter import limiter

logger = structlog.get_logger().bind(service="auth")

auth_router = APIRouter()


def _free_username(session: Session, base: str) -> str:
    """ivan, ivan2, ivan3 ... — the username is made from the email and the user never sees
    it, so ivan@gmail.com and ivan@ukr.net must both be able to register."""
    base = base or "user"
    taken = set(session.exec(select(User.username).where(User.username.startswith(base))).all())
    if base not in taken:
        return base
    n = 2
    while f"{base}{n}" in taken:
        n += 1
    return f"{base}{n}"


@auth_router.post('/register', response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    email = user_data.email.strip().lower()
    if session.exec(select(User).where(func.lower(User.email) == email)).first():
        logger.warning("register_conflict", email=email, reason="email_taken")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Акаунт з такою поштою вже існує — увійдіть")
    if user_data.username:
        if session.exec(select(User).where(User.username == user_data.username)).first():
            logger.warning("register_conflict", username=user_data.username, reason="username_taken")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Таке ім'я користувача вже зайняте")
        effective_username = user_data.username
    else:
        effective_username = _free_username(session, email.split('@')[0])
    new_user = User(
        username=effective_username,
        email=email,
        hashed_password=hash_password(user_data.password)
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    access_token = create_access_token(data={"email": new_user.email})
    logger.info("user_registered", username=new_user.username, email=new_user.email)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@auth_router.post('/login', response_model=AuthResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, session: Session = Depends(get_session)):
    credential = body.email.strip()
    user = session.exec(
        select(User).where((func.lower(User.email) == credential.lower()) | (User.username == credential))
    ).first()
    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning("login_failed", credential=credential, reason="no_user" if not user else "bad_password")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неправильна пошта або пароль")
    access_token = create_access_token(data={"email": user.email})
    logger.info("user_logged_in", email=user.email)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@auth_router.delete('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    set_cached(f"blacklist:{token}", "1", ttl=3600)
    logger.info("user_logged_out", email=current_user.email)
    return None


@auth_router.get('/profile', response_model=Profile)
async def get_profile(current_user: User = Depends(get_current_user)):
    return Profile(**(current_user.profile or {}))


@auth_router.put('/profile', response_model=Profile)
async def put_profile(body: Profile, current_user: User = Depends(get_current_user),
                      session: Session = Depends(get_session)):
    """Replaces "Мої дані" — the defaults every new report starts with."""
    current_user.profile = body.model_dump(exclude_none=True)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return Profile(**current_user.profile)
