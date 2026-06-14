"""Teste de ponta a ponta de backup/restauração (docs/07, Fase 11)."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.backup import create_backup, restore_backup
from app.db.migrate import apply_migrations
from app.db.seed import seed


@pytest.fixture
def db_environment(tmp_path):
    db_path = tmp_path / "helence.db"
    uploads_dir = tmp_path / "uploads"
    backup_dir = tmp_path / "backups"

    uploads_dir.mkdir()
    (uploads_dir / "exemplo.pdf").write_bytes(b"conteudo original")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        apply_migrations(connection)
        seed(connection)
    finally:
        connection.close()

    return db_path, uploads_dir, backup_dir


def test_backup_and_restore_round_trip(db_environment):
    db_path, uploads_dir, backup_dir = db_environment

    dest = create_backup(db_path=db_path, uploads_dir=uploads_dir, backup_dir=backup_dir)
    assert (dest / db_path.name).exists()
    assert (dest / uploads_dir.name / "exemplo.pdf").read_bytes() == b"conteudo original"

    # Altera o banco e o upload depois do backup.
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            ("Usuário Pós-Backup", "pos-backup@helence.local", "colaborador"),
        )
        connection.commit()
    finally:
        connection.close()
    (uploads_dir / "exemplo.pdf").write_bytes(b"conteudo alterado")
    (uploads_dir / "novo.pdf").write_bytes(b"arquivo criado depois do backup")

    restore_backup(dest, db_path=db_path, uploads_dir=uploads_dir)

    # Estado anterior preservado em "*.before_restore_*".
    before_restore_dbs = list(db_path.parent.glob(f"{db_path.name}.before_restore_*"))
    assert len(before_restore_dbs) == 1

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        users = connection.execute(
            "SELECT email FROM users WHERE email = ?", ("pos-backup@helence.local",)
        ).fetchall()
        assert users == []

        (integrity,) = connection.execute("PRAGMA integrity_check").fetchone()
        assert integrity == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()

    assert (uploads_dir / "exemplo.pdf").read_bytes() == b"conteudo original"
    assert not (uploads_dir / "novo.pdf").exists()


def test_restore_fails_when_backup_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        restore_backup(tmp_path / "inexistente", db_path=tmp_path / "helence.db")
