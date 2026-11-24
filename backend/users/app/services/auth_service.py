from fastapi import HTTPException, status, Cookie
import urllib.parse
import jwt
from jwt.exceptions import InvalidTokenError
from typing import Annotated
from datetime import timedelta, datetime, timezone
from app.security import verify_password, DUMMY_HASH
from app.config import setting
from app.Models.auth_models import TokenData
from app.services.user_service import UserService, usuario_dict

user_service = UserService()

async def authenticate_user(email: str, password: str):
    user_doc = await user_service.read_user_by_email(email)
    if not user_doc:
        verify_password(password, DUMMY_HASH)
        return False
    
    correct_password = verify_password(password, user_doc.get("password_hash", ""))
    if not correct_password:
        return False
    
    return usuario_dict(user_doc)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expires_delta = expires_delta if expires_delta else timedelta(minutes=15)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, setting.SECRET_KEY, algorithm=setting.ALGORITHM)
    return encoded_jwt

async def get_current_user(access_token: Annotated[str | None, Cookie()] = None):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    if not access_token:
        raise credentials_exception
    try:
        raw_token = urllib.parse.unquote(access_token)
        cleaned_token = raw_token.strip(' "\'')
        token_type, token = cleaned_token.split(" ")
        if token_type.lower() != "bearer":
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(username=email)
    except InvalidTokenError:
        raise credentials_exception

    user_doc = await user_service.read_user_by_email(token_data.username)
    if user_doc is None:
        raise credentials_exception

    return usuario_dict(user_doc)