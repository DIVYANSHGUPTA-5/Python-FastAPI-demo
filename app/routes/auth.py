from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app import security
from app.schemas import ErrorResponse, Token, UserCreate, UserResponse
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={409: {"model": ErrorResponse, "description": "Username already taken"}},
)
def register(data: UserCreate) -> UserResponse:
    user = user_service.create_user(data.username, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )
    return UserResponse(id=user.id, username=user.username)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and get a JWT access token",
    responses={401: {"model": ErrorResponse, "description": "Wrong username or password"}},
)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Send `username` and `password` as form data. Use the returned token as a Bearer token."""
    user = user_service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=security.create_access_token(user.id))
