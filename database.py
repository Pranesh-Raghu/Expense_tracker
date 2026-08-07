import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "mysql+pymysql://root:root@localhost/expensetracker"
)

engine_kwargs = {"echo": os.environ.get("SQL_ECHO", "false").lower() == "true"}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Managed Postgres providers on free/serverless tiers (e.g. Neon) close
    # idle server-side connections without telling the client. Without
    # pool_pre_ping, SQLAlchemy hands out that dead connection on the next
    # request and the query fails with "SSL connection has been closed
    # unexpectedly" - surfaced as a bare 500 on whatever endpoint happened
    # to run first after the idle gap (e.g. /auth/google/callback).
    # pool_pre_ping issues a cheap SELECT 1 before reusing a pooled
    # connection and transparently reconnects if that fails.
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

__all__ = ["SessionLocal", "Base", "engine"]
