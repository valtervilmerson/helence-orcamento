"""Endpoints de login/logout/sessão atual."""

import sqlite3

from fastapi import APIRouter, Depends, Response, status

from app.auth import service
from app.auth.dependencies import SESSION_COOKIE_NAME, get_current_user
from app.auth.schemas import LoginIn, UserOut
from app.auth.security import SESSION_MAX_AGE_SECONDS, create_session_token
from app.config import get_settings
from app.db.connection import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: sqlite3.Row) -> UserOut:
    return UserOut(id=user["id"], name=user["name"], email=user["email"], role=user["role"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response) -> UserOut:
    with get_connection() as connection:
        user = service.authenticate(connection, payload.email, payload.password)
    settings = get_settings()
    token = create_session_token(user["id"])
    # Frontend e backend rodam em subdomínios distintos do up.railway.app
    # (sites diferentes para fins de SameSite). Sem SameSite=None o
    # cookie de sessão não é enviado nas chamadas cross-site, mesmo com
    # credentials: 'include' no fetch. SameSite=None exige Secure=True.
    samesite = "none" if settings.session_cookie_secure else "lax"
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite=samesite,
        secure=settings.session_cookie_secure,
    )
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(response: Response) -> None:
    settings = get_settings()
    samesite = "none" if settings.session_cookie_secure else "lax"
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        samesite=samesite,
        secure=settings.session_cookie_secure,
    )


@router.get("/me", response_model=UserOut)
def me(user: sqlite3.Row = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
