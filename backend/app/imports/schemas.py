"""Modelos de request/response de importações (docs/06, seções 14.1/14.2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.catalog.schemas import PriceTableSummary
from app.quotes.schemas import UserSummary

ImportStatus = Literal["recebido", "processando", "concluido", "erro"]


class ImportedFileOut(BaseModel):
    id: int
    original_filename: str | None
    file_hash: str | None
    page_count: int | None
    status: ImportStatus
    imported_at: str
    imported_by: UserSummary | None
    notes: str | None = None


class ImportListItem(BaseModel):
    id: int
    original_filename: str | None
    status: ImportStatus
    page_count: int | None
    imported_at: str
    items_extracted: int
    items_pending_review: int
    linked_price_table: PriceTableSummary | None


class ImportListOut(BaseModel):
    items: list[ImportListItem]
    page: int
    page_size: int
    total: int
