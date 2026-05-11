from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta,timezone
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"])

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    hashed = pwd_context.hash(password)
    return hashed

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
    

def create_access_token(data: dict,expires_delta: timedelta | None = None) -> jwt:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,ALGORITHM)
    return encoded_jwt