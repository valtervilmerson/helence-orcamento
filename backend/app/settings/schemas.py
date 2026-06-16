"""Schemas Pydantic das configurações globais."""

from __future__ import annotations

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    global_markup_percent: float


class AppSettingsPatchIn(BaseModel):
    global_markup_percent: float | None = None
