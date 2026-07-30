from sqlalchemy import Column, Integer, String,Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base, SessionLocal
from passlib.context import CryptContext



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    
    
    # Data Access Object (DAO) Methods
    @staticmethod
    def create_user(user_credentials):
        
        with SessionLocal() as db:
           last_user = db.query(User).order_by(User.id.desc()).first()
           new_id = last_user.id + 1 if last_user else 1 
            
           hashed_password = pwd_context.hash(user_credentials.password)
           db_user = User(id = new_id,
                          username = user_credentials.username,
                          email = user_credentials.email,
                          password = hashed_password,
                          )
           db.add(db_user)
           db.commit()
           db.refresh(db_user)
           return db_user

    @staticmethod
    def get_users():
        with SessionLocal() as db:
         return db.query(User).all() or []

    @staticmethod
    def get_user(user_id: int):
        with SessionLocal() as db: 
           return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user(user_credentials,user_id: int):
        with SessionLocal() as db:
         user = db.query(User).filter(User.id == user_id).first()
         if not user:
             return None  
                
         if 'username' in user_credentials:
            user.username = user_credentials['username']
         if 'email' in user_credentials:
            user.email = user_credentials['email']
         if 'password' in user_credentials:
            user.password = pwd_context.hash(user_credentials['password'])
            
         db.commit()
         db.refresh(user)
        
         return user

    @staticmethod
    def update_partial_user(user_id: int, user_data):
        with SessionLocal() as db:
            
         user = db.query(User).filter(User.id == user_id).first()   
         
         for key, value in user_data.items():
           setattr(user, key, value)  

         db.commit()
         db.refresh(user)
         return {"message": "User updated successfully", "user": user}
    
    @staticmethod
    def delete_user(user_id: int):
        with SessionLocal() as db:
         user = db.query(User).filter(User.id == user_id).first()
         if not user:
             return None

         db.delete(user)
         db.commit()
         
         return user
    
    
    @staticmethod
    def authenticate_user(username: str, password: str):
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return False
            if not pwd_context.verify(password,user.password):
                return False
            return user
    
    
    
    