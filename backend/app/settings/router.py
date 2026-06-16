"""Endpoints de configurações globais da aplicação."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user, require_role
from app.db.connection import get_connection
from app.settings import repository
from app.settings.schemas import AppSettingsOut, AppSettingsPatchIn
from app.shared.errors import DescontoInvalidoError

router = APIRouter(prefix="/settings", tags=["settings"])


def get_db() -> sqlite3.Connection:
    with get_connection() as connection:
        yield connection


@router.get("", response_model=AppSettingsOut, dependencies=[Depends(get_current_user)])
def get_settings(connection: sqlite3.Connection = Depends(get_db)) -> AppSettingsOut:
    return AppSettingsOut(global_markup_percent=repository.get_global_markup(connection))


@router.patch(
    "",
    response_model=AppSettingsOut,
    dependencies=[Depends(require_role("admin"))],
)
def update_settings(
    payload: AppSettingsPatchIn, connection: sqlite3.Connection = Depends(get_db)
) -> AppSettingsOut:
    if payload.global_markup_percent is not None:
        if payload.global_markup_percent < 0:
            raise DescontoInvalidoError(
                details={"global_markup_percent": payload.global_markup_percent}
            )
        repository.set_global_markup(connection, payload.global_markup_percent)
    return AppSettingsOut(global_markup_percent=repository.get_global_markup(connection))
