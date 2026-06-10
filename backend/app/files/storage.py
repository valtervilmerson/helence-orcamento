"""Abstração mínima de armazenamento de arquivos (docs/06, seção 5).

Para uma aplicação interna de pequeno porte, "disco local" é suficiente —
mas todo acesso a arquivo passa por esta interface para que a forma de
armazenamento possa mudar sem afetar `app/imports`.
"""

from __future__ import annotations

from pathlib import Path


class FileStorage:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, filename: str) -> Path:
        return self.base_dir / filename

    def exists(self, filename: str) -> bool:
        return self.path_for(filename).exists()

    def save(self, filename: str, content: bytes) -> Path:
        path = self.path_for(filename)
        path.write_bytes(content)
        return path

    def read(self, filename: str) -> bytes:
        return self.path_for(filename).read_bytes()
