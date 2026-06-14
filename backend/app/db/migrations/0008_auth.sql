-- Autenticação por sessão (docs/04, papéis de usuário).
-- Senha armazenada como hash scrypt (formato "scrypt$n$r$p$salt$hash"),
-- gerado em app/auth/security.py — sem dependências externas.
ALTER TABLE users ADD COLUMN password_hash TEXT;
