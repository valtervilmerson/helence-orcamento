"""Envelope de erro padrão e exceções de domínio (docs/06, seção 9)."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Exceção base para erros de domínio nomeados (ex. ITEM_SEM_PRECO).

    Subclasses definem `code`, `status_code` e `message` padrão; cada uma
    deve ter pelo menos um teste dedicado (docs/08, seção 3.1).
    """

    code: str = "ERRO_DE_DOMINIO"
    status_code: int = status.HTTP_400_BAD_REQUEST
    message: str = "Ocorreu um erro de domínio."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


def error_envelope(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, exc.details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    details = {"request_id": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_envelope(
            "ERRO_INTERNO",
            "Ocorreu um erro inesperado. Informe o identificador da requisição ao suporte.",
            details,
        ),
    )
