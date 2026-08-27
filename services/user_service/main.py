"""
user_service: signup, login, and user CRUD, protected by JWT auth.

Route functions stay thin - they parse input via schemas, delegate to
crud.py for actual logic, and translate exceptions/results into HTTP
responses. This keeps HTTP concerns (status codes, headers) separate from
business rules (validation, what counts as a duplicate, etc).
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common.auth import create_access_token, get_current_user
from common.validation import (
    DuplicateUserError,
    InvalidUserIdError,
    MalformedStateError,
    MalformedZipError,
)
from services.user_service import crud
from services.user_service.database import Base, SessionLocal, engine, get_db
from services.user_service.schemas import Token, UserCreate, UserLogin, UserResponse, UserUpdate

# Creates the users table if it does not already exist. Fine for this
# project's scale; a production system would use a migration tool
# (e.g. Alembic) instead of relying on this on startup.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service")

# allow_origins=["*"] is deliberately permissive for local development,
# where a plain HTML/JS frontend on a different port needs to call this
# API from the browser. Restrict this to known domains before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "user_service"}


@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = crud.create_user(db, user_data)
    except InvalidUserIdError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MalformedStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MalformedZipError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return new_user


@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, credentials.email, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(user_id=user.user_id)
    return Token(access_token=token)


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    updates: UserUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    try:
        user = crud.update_user(db, user_id, updates)
    except MalformedStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MalformedZipError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    deleted = crud.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
