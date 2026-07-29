"""Schemas Pydantic das configurações globais."""

from __future__ import annotations

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    global_markup_percent: float
    discount_limit_percent: float
    default_validity_days: int


class AppSettingsPatchIn(BaseModel):
    global_markup_percent: float | None = None
    discount_limit_percent: float | None = None
    default_validity_days: int | None = None
