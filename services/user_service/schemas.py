"""
Pydantic schemas for user_service.

These define the shape of API requests and responses - separate from
models.py (the database shape). Keeping them separate means a password
field can exist on input without ever being able to leak out on output.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for POST /signup. Includes plaintext password."""

    user_id: str
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Request body for POST /login."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    Request body for PUT /users/{user_id}.

    Every field is optional so a client can send only the fields it wants
    to change - crud.py applies only the ones that are not None.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """
    What gets returned to clients. No password field exists here at all,
    so it is not possible to accidentally serialize the hash into a response.
    """

    user_id: str
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: EmailStr

    class Config:
        # Lets Pydantic read attributes off a SQLAlchemy User object
        # directly (user.first_name) instead of requiring a dict.
        from_attributes = True


class Token(BaseModel):
    """Response body for POST /login."""

    access_token: str
    token_type: str = "bearer"
