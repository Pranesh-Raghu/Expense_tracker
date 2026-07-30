from fastapi import APIRouter, status
from services.user_services import update_user, get_user, get_users, delete_user, create_user, update_partial_user
from schemas.user_schemas import UserCreate, UserResponse, DeleteResponse
from auth import user_dependency
from authz import service as authz
router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create__user(user_data:UserCreate):
    return create_user(user_data)

@router.get("/", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
def get__users(user: user_dependency):
    return get_users()

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get__user(user_id: int, user: user_dependency):
    authz.require(user['id'] == user_id or authz.is_admin(user['id']))
    return get_user(user_id)

@router.put("/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
def update__user(user_data:UserCreate,user_id:int, user: user_dependency):
    authz.require(user['id'] == user_id or authz.is_admin(user['id']))
    return update_user(user_data,user_id)

@router.patch("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update__partial__user(user_id:int,user_data:dict, user: user_dependency):
    authz.require(authz.is_admin(user['id']))
    return update_partial_user(user_id,user_data)

@router.delete("/{user_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
def delete__user(user_id: int, user: user_dependency):
    authz.require(authz.is_admin(user['id']))
    deleted = delete_user(user_id)
    return deleted
