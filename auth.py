import os

from fastapi import APIRouter, Depends, status, HTTPException
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from typing import Annotated
from passlib.context import CryptContext  # pyright: ignore[reportMissingModuleSource]
from models.user_model import User
from schemas.user_schemas import Token
from oauth import service as oauth_service
from oauth.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo

router = APIRouter()


SECRET_KEY = os.environ.get('REST_JWT_SECRET_KEY', 'dev-only-insecure-secret-change-me')
ALGORITHM = 'HS256'



bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm = ALGORITHM)



def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    # Static API keys are a second, long-lived credential type for scripts and
    # automation where an interactive login isn't practical - accepted here
    # so the whole REST API works with either credential.
    if token.startswith(oauth_service.API_KEY_PREFIX):
        info = oauth_service.verify_api_key(token)
        if not info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate API key')
        user = User.get_user(info['user_id'])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate API key')
        return {'username': user.username, 'id': user.id}

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub', '')
        user_id: int = payload.get('id', 0)

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate token')


user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm,Depends()]):

    user = User.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

    token = create_access_token(user.username, user.id, timedelta(minutes=100))

    return  {'access_token':token, 'token_type':'bearer'}


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreateRequest, user: user_dependency):
    raw_key = oauth_service.issue_api_key(user_id=user['id'], name=payload.name)
    return ApiKeyCreateResponse(api_key=raw_key, name=payload.name)


@router.get("/api-keys", response_model=list[ApiKeyInfo])
def list_api_keys(user: user_dependency):
    return oauth_service.list_api_keys(user['id'])


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, user: user_dependency):
    if not oauth_service.revoke_api_key(user_id=user['id'], key_id=key_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='API key not found')



