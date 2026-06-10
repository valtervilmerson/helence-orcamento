import os
import tempfile
from pathlib import Path

_tmp_dir = Path(tempfile.mkdtemp(prefix="helence-test-"))
os.environ.setdefault("DATABASE_PATH", str(_tmp_dir / "test.db"))
os.environ.setdefault("UPLOADS_DIR", str(_tmp_dir / "uploads"))
