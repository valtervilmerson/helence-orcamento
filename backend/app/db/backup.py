"""Backup e restauração do SQLite (docs/06, seção 12; docs/09, seções 12-13).

Usa a API de *Online Backup* do SQLite (``sqlite3.Connection.backup``) em
vez de copiar o arquivo "a frio", evitando capturar um estado inconsistente
caso haja escrita concorrente. Cada backup é um diretório com o `.db` e uma
cópia do diretório de uploads, nomeado pelo timestamp UTC de criação.

Sem dependências externas — substitui os scripts `.sh` de `docs/09` (que
assumem o CLI `sqlite3`, indisponível neste ambiente) por um módulo Python
equivalente, executável via ``python -m app.db.backup`` /
``python -m app.db.backup restore <diretorio>``.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings


def create_backup(
    db_path: str | Path | None = None,
    uploads_dir: str | Path | None = None,
    backup_dir: str | Path | None = None,
) -> Path:
    """Cria um novo backup consistente do banco e dos uploads. Retorna o diretório criado."""
    settings = get_settings()
    db_path = Path(db_path or settings.database_path)
    uploads_dir = Path(uploads_dir or settings.uploads_dir)
    backup_dir = Path(backup_dir or settings.backup_dir)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / timestamp
    dest.mkdir(parents=True, exist_ok=False)

    source = sqlite3.connect(db_path)
    try:
        target = sqlite3.connect(dest / db_path.name)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    if uploads_dir.exists():
        shutil.copytree(uploads_dir, dest / uploads_dir.name)

    return dest


def restore_backup(
    backup_path: str | Path,
    db_path: str | Path | None = None,
    uploads_dir: str | Path | None = None,
) -> None:
    """Restaura banco e uploads a partir de um diretório de backup.

    O estado atual é preservado em arquivos/diretórios
    ``*.before_restore_<timestamp>`` antes da substituição (docs/09, seção
    13.1, passo 2), e a integridade do banco restaurado é verificada via
    ``PRAGMA integrity_check`` e ``PRAGMA foreign_key_check``.
    """
    settings = get_settings()
    backup_path = Path(backup_path)
    db_path = Path(db_path or settings.database_path)
    uploads_dir = Path(uploads_dir or settings.uploads_dir)

    backup_db = backup_path / db_path.name
    if not backup_db.exists():
        raise FileNotFoundError(f"Backup do banco não encontrado: {backup_db}")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if db_path.exists():
        db_path.rename(db_path.with_name(f"{db_path.name}.before_restore_{timestamp}"))
    if uploads_dir.exists():
        uploads_dir.rename(uploads_dir.with_name(f"{uploads_dir.name}.before_restore_{timestamp}"))

    shutil.copy2(backup_db, db_path)

    backup_uploads = backup_path / uploads_dir.name
    if backup_uploads.exists():
        shutil.copytree(backup_uploads, uploads_dir)
    else:
        uploads_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    try:
        (integrity,) = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != "ok":
            raise RuntimeError(f"PRAGMA integrity_check falhou após restauração: {integrity}")

        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"PRAGMA foreign_key_check encontrou violações: {fk_errors}")
    finally:
        connection.close()


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "restore":
        restore_backup(sys.argv[2])
        print(f"Restauração concluída a partir de {sys.argv[2]}.")
        return

    if len(sys.argv) == 1:
        dest = create_backup()
        print(f"Backup criado em {dest}")
        return

    print("Uso: python -m app.db.backup            (cria um novo backup)")
    print("     python -m app.db.backup restore <diretorio_do_backup>")
    sys.exit(1)


if __name__ == "__main__":
    main()
