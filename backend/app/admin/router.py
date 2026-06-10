"""Endpoint administrativo temporário para aplicar o seed em produção (Fase 2).

Protegido por `ADMIN_SEED_KEY` (header `X-Admin-Key`), uma chave dedicada e
descartável — não a `SECRET_KEY` de sessão. Sem essa variável configurada, a
rota fica desabilitada (retorna 403). Remover após o uso — esta rota existe
apenas para destravar o bootstrap do catálogo manual em ambientes onde não há
acesso de shell ao banco.
"""

import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import get_settings
from app.db.connection import get_connection
from app.db.seed import seed

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db() -> sqlite3.Connection:
    with get_connection() as connection:
        yield connection


@router.post("/seed", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def run_seed(
    x_admin_key: str = Header(...),
    connection: sqlite3.Connection = Depends(get_db),
) -> None:
    settings = get_settings()
    if not settings.admin_seed_key or x_admin_key != settings.admin_seed_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chave inválida.")
    seed(connection)
