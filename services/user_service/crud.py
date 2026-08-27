"""
Business logic for user_service: validation, password hashing, and the
actual database operations. Kept separate from main.py so routes stay
focused on HTTP concerns and this logic is reusable/testable on its own.
"""

from sqlalchemy.orm import Session

from common.auth import hash_password, verify_password
from common.validation import (
    DuplicateUserError,
    validate_state,
    validate_user_id,
    validate_zip_code,
)
from services.user_service.models import User
from services.user_service.schemas import UserCreate, UserUpdate


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Validate fields, hash the password, and insert a new user.

    Validation runs before any database work so a malformed request never
    reaches the database at all.
    """
    validate_user_id(user_data.user_id)
    validate_state(user_data.state)
    validate_zip_code(user_data.zip_code)

    if get_user_by_id(db, user_data.user_id) is not None:
        raise DuplicateUserError(f"user_id '{user_data.user_id}' already exists")

    new_user = User(
        user_id=user_data.user_id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        address=user_data.address,
        city=user_data.city,
        state=user_data.state.upper(),
        zip_code=user_data.zip_code,
        phone=user_data.phone,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the User if email/password match, else None."""
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def update_user(db: Session, user_id: str, updates: UserUpdate) -> User | None:
    """Apply only the fields the caller actually provided."""
    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    update_data = updates.model_dump(exclude_unset=True)
    if "state" in update_data:
        validate_state(update_data["state"])
        update_data["state"] = update_data["state"].upper()
    if "zip_code" in update_data:
        validate_zip_code(update_data["zip_code"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: str) -> bool:
    """Delete a user. Returns True if a row was deleted, False if not found."""
    user = get_user_by_id(db, user_id)
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True
