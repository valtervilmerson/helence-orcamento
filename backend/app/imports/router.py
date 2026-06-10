"""Endpoints REST de upload e listagem de importações (docs/06, 14.1/14.2)."""

import sqlite3

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.config import get_settings
from app.db.connection import get_connection
from app.files.storage import FileStorage
from app.imports import service
from app.imports.schemas import ImportedFileOut, ImportListOut

router = APIRouter(prefix="/imports", tags=["imports"])


def get_db() -> sqlite3.Connection:
    with get_connection() as connection:
        yield connection


def get_storage() -> FileStorage:
    settings = get_settings()
    return FileStorage(settings.uploads_dir)


@router.post("", response_model=ImportedFileOut, status_code=status.HTTP_201_CREATED)
def upload_import(
    file: UploadFile = File(...),
    notes: str | None = Form(default=None),
    connection: sqlite3.Connection = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> ImportedFileOut:
    settings = get_settings()
    content = file.file.read()
    return service.receive_upload(
        connection,
        storage,
        content=content,
        original_filename=file.filename,
        notes=notes,
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )


@router.get("", response_model=ImportListOut)
def list_imports(
    status_: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    connection: sqlite3.Connection = Depends(get_db),
) -> ImportListOut:
    return service.list_imports(connection, status=status_, page=page, page_size=page_size)
