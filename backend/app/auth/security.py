"""Hash de senha e assinatura de cookie de sessão, sem dependências externas.

Senhas: ``hashlib.scrypt`` (stdlib) com salt aleatório, formato de
armazenamento ``scrypt$n$r$p$salt_hex$hash_hex``.

Sessão: token ``base64(user_id:expira_em:assinatura_hmac_sha256)``, assinado
com ``settings.secret_key``. Não há estado de sessão no banco — revogar
exige apenas trocar ``secret_key``.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import get_settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32

SESSION_MAX_AGE_SECONDS = 60 * 60 * 12  # 12h


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored_hash.split("$")
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=_DKLEN,
        )
        return hmac.compare_digest(derived.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_session_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
    payload = f"{user_id}:{expires_at}"
    signature = hmac.new(
        settings.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    raw = f"{payload}:{signature}"
    return urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def verify_session_token(token: str) -> int | None:
    settings = get_settings()
    try:
        raw = urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id_str, expires_at_str, signature = raw.split(":")
        payload = f"{user_id_str}:{expires_at_str}"
        expected = hmac.new(
            settings.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        if int(expires_at_str) < time.time():
            return None
        return int(user_id_str)
    except (ValueError, AttributeError):
        return None
