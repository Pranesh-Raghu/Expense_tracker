from models.user_model import User
from fastapi import Depends
from services.expense_services import user_dependency
from validators.user_validators import validate_user
from schemas.user_schemas import UserCreate

def create_user(user_data: UserCreate):
    user = User.create_user(user_data)
    
    return user

def get_users():
    users = User.get_users()
    
    validate_user(users)
    return users

def get_user(user_id: int):
    user = User.get_user(user_id)
    validate_user(user)
    return user

def update_user(user_data, user_id: int = Depends(user_dependency)):
    user = User.update_user(user_data.model_dump(),user_id)
    validate_user(user)
    return user

def update_partial_user(user_id,user_data):
    user = User.update_partial_user(user_id,user_data)  
    
    return {"message": f"{user} deleted successfully"}

def delete_user(user_id: int):
    deleted = User.delete_user(user_id)

    validate_user(deleted)
    
    return {"message": f"{deleted.username} deleted successfully"}







