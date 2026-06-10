"""Endpoints REST de upload, listagem e processamento de importações (docs/06, 14.1-14.4)."""

import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status

from app.config import get_settings
from app.db.connection import get_connection
from app.files.storage import FileStorage
from app.imports import repository, service
from app.imports.schemas import (
    ImportedFileOut,
    ImportListOut,
    ImportStatusOut,
    ProcessImportIn,
    ProcessImportOut,
)

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


@router.post(
    "/{import_id}/process",
    response_model=ProcessImportOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_import(
    import_id: int,
    background_tasks: BackgroundTasks,
    body: ProcessImportIn | None = None,
    connection: sqlite3.Connection = Depends(get_db),
) -> ProcessImportOut:
    strategy = body.strategy if body is not None else None
    result = service.start_processing(connection, import_id, strategy=strategy)

    row = repository.get_imported_file(connection, import_id)
    assert row is not None
    background_tasks.add_task(service.run_processing, import_id, row["file_path"])

    return result


@router.get("/{import_id}/status", response_model=ImportStatusOut)
def get_import_status(
    import_id: int,
    connection: sqlite3.Connection = Depends(get_db),
) -> ImportStatusOut:
    return service.get_status(connection, import_id)
