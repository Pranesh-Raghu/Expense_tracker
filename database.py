import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "mysql+pymysql://root:root@localhost/expensetracker"
)

engine_kwargs = {"echo": os.environ.get("SQL_ECHO", "false").lower() == "true"}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

__all__ = ["SessionLocal", "Base", "engine"]
