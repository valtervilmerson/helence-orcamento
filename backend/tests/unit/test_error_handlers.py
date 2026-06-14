"""Testes dos handlers de erro (docs/06, seção 8/9): toda exceção — de
domínio ou não — deve ser logada, com `request_id` quando disponível, e
exceções não previstas devem logar o *stack trace* (`exc_info`)."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.shared.errors import (
    ItemSemPrecoError,
    domain_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)


def _request(request_id: str | None = "req-123") -> SimpleNamespace:
    return SimpleNamespace(
        method="POST",
        url=SimpleNamespace(path="/api/v1/quotes/1/items"),
        state=SimpleNamespace(request_id=request_id),
    )


def test_domain_error_is_logged_with_request_id(caplog: pytest.LogCaptureFixture) -> None:
    exc = ItemSemPrecoError(details={"component_variant_id": 42})

    with caplog.at_level(logging.WARNING, logger="app.error"):
        response = asyncio.run(domain_error_handler(_request(), exc))

    assert response.status_code == 422
    record = next(r for r in caplog.records if r.name == "app.error")
    assert record.levelno == logging.WARNING
    assert "ITEM_SEM_PRECO" in record.getMessage()
    assert record.request_id == "req-123"


def test_http_exception_uses_standard_envelope(caplog: pytest.LogCaptureFixture) -> None:
    exc = HTTPException(status_code=403, detail="Chave inválida.")

    with caplog.at_level(logging.WARNING, logger="app.error"):
        response = asyncio.run(http_exception_handler(_request(), exc))

    assert response.status_code == 403
    body = response.body.decode()
    assert '"code":"HTTP_403"' in body
    assert "Chave inválida." in body
    record = next(r for r in caplog.records if r.name == "app.error")
    assert record.request_id == "req-123"


def test_validation_error_uses_standard_envelope(caplog: pytest.LogCaptureFixture) -> None:
    try:
        from pydantic import BaseModel

        class Payload(BaseModel):
            name: str

        Payload.model_validate({})
    except Exception as raised:
        pydantic_error = raised

    exc = RequestValidationError(errors=pydantic_error.errors())

    with caplog.at_level(logging.WARNING, logger="app.error"):
        response = asyncio.run(validation_error_handler(_request(), exc))

    assert response.status_code == 422
    body = response.body.decode()
    assert '"code":"DADOS_INVALIDOS"' in body
    assert '"errors"' in body
    record = next(r for r in caplog.records if r.name == "app.error")
    assert record.request_id == "req-123"


def test_unhandled_exception_is_logged_with_stack_trace(
    caplog: pytest.LogCaptureFixture,
) -> None:
    exc = RuntimeError("falha inesperada")

    with caplog.at_level(logging.ERROR, logger="app.error"):
        response = asyncio.run(unhandled_exception_handler(_request(), exc))

    assert response.status_code == 500
    record = next(r for r in caplog.records if r.name == "app.error")
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.request_id == "req-123"

    body = response.body.decode()
    assert "falha inesperada" not in body
    assert "ERRO_INTERNO" in body
