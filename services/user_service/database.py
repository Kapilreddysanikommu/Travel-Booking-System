"""
Database connection setup for user_service.

Each service connects to the same MySQL instance but only ever touches its
own tables (users here). Sharing one MySQL server keeps local dev simple
(one container instead of four), while separate table ownership per service
keeps the services independent - user_service never queries flight tables.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://travel_app:app_password@localhost:3306/travel_booking"
)

# pool_pre_ping checks a connection is still alive before handing it to a
# request - without it, a connection that MySQL silently dropped (e.g. after
# sitting idle) would cause a confusing failure on the next query instead of
# being quietly replaced.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models inherit from this so SQLAlchemy knows which classes map
# to database tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields one DB session per request.

    The route function runs while this generator is paused at `yield`.
    Once the route finishes (successfully or via exception), execution
    resumes here and the session is closed in `finally`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
