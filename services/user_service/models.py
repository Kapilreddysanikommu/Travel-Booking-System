"""SQLAlchemy ORM model for the users table."""

from sqlalchemy import Column, String

from services.user_service.database import Base


class User(Base):
    __tablename__ = "users"

    # user_id is the SSN-formatted string itself (###-##-####), used as the
    # primary key per the spec - format and duplicate checks happen in
    # crud.py before a row is ever inserted.
    user_id = Column(String(11), primary_key=True, index=True)

    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    address = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)

    # Never named "password" - the name makes it obvious at every call site
    # that this column holds a bcrypt hash, not plaintext.
    hashed_password = Column(String(255), nullable=False)
