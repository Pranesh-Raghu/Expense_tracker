from fastapi import APIRouter, status
from services.user_services import update_user, get_user, get_users, delete_user, create_user, update_partial_user
from schemas.user_schemas import UserCreate, UserUpdate, UserResponse, UserPublic, DeleteResponse
from auth import user_dependency
from authz import service as authz
router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create__user(user_data:UserCreate):
    return create_user(user_data)

@router.get("/", status_code=status.HTTP_200_OK)
def get__users(user: user_dependency) -> list[UserResponse] | list[UserPublic]:
    # Every authenticated user needs this list for the "share with" picker
    # (id + username + avatar), but only admins should see everyone's email -
    # shape the response by privilege instead of gating the whole endpoint.
    users = get_users()
    if authz.is_admin(user['id']):
        return [UserResponse.model_validate(u) for u in users]
    return [UserPublic.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get__user(user_id: int, user: user_dependency):
    authz.require(user['id'] == user_id or authz.is_admin(user['id']))
    return get_user(user_id)

@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update__user(user_data: UserUpdate, user_id: int, user: user_dependency):
    authz.require(user['id'] == user_id or authz.is_admin(user['id']))
    return update_user(user_data, user_id)

@router.patch("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update__partial__user(user_id:int,user_data:dict, user: user_dependency):
    authz.require(authz.is_admin(user['id']))
    return update_partial_user(user_id,user_data)

@router.delete("/{user_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
def delete__user(user_id: int, user: user_dependency):
    authz.require(authz.is_admin(user['id']))
    deleted = delete_user(user_id)
    return deleted
