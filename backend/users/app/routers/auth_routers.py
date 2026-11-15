from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from starlette import status
from datetime import timedelta
from ..Models.users import UsersResponse
from ..services.auth_service import authenticate_user, create_access_token, get_current_user
from ..config import setting

router = APIRouter(
  prefix="/auth",
  tags=["auth"],
  responses= {404: {"description": "not found"}}
)

@router.post("/token", status_code=status.HTTP_202_ACCEPTED)
async def login(
  response: Response,
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
  ):
  user = await authenticate_user(form_data.username, form_data.password)
  if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Autenticate": "Bearer"})
  access_token_expires = timedelta(minutes=setting.ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
  response.set_cookie(
      key="access_token",
      value=f"Bearer {access_token}",
      httponly=True,
      max_age=int(access_token_expires.total_seconds()),
      samesite="lax",
      secure=False,
      path="/"
  )
  return {"message": "Login successful"}

@router.get("/validate", response_model=UsersResponse, status_code=status.HTTP_200_OK)
async def validate_token(
    current_user: Annotated[UsersResponse, Depends(get_current_user)]
):
    return current_user
