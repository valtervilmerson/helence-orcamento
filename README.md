# Helence Orçamento

Sistema interno de catálogo de produtos e orçamentos, com importação de
PDFs de fornecedores. Backend em **FastAPI + SQLite**, frontend em
**React + TypeScript + Vite**, hospedado em produção na **Railway**.

A documentação completa do domínio, arquitetura e plano de implementação
está em [`docs/`](docs/) — comece por
[`docs/README_IMPLEMENTACAO.md`](docs/README_IMPLEMENTACAO.md).

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Python | 3.11+ |
| Node.js | 20 LTS+ |
| npm | acompanha o Node |

```bash
python3 --version
node --version
npm --version
```

## Backend

```bash
cd backend

# Ambiente virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Dependências
pip install -e ".[dev]"

# Configuração
cp .env.example .env
# editar .env e gerar SECRET_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Subir o servidor (com reload)
# Aplica migrations pendentes automaticamente no startup (docs/06, seção 10)
uvicorn app.main:app --reload --port 8000
```

### Migrations e seed

```bash
# aplicar migrations pendentes manualmente (idempotente)
python -m app.db.migrate

# popular dados mínimos de referência (usuários de teste, price_table 'vigente')
python -m app.db.seed
```

- Healthcheck: `GET http://localhost:8000/api/v1/health` → `{"status": "ok"}`
- Documentação interativa: `http://localhost:8000/docs`

### Lint, formatação e testes

```bash
ruff check .
ruff format --check .
pytest -m "not slow"
```

## Frontend

```bash
cd frontend

# Dependências
npm ci

# Configuração
cp .env.example .env
# editar .env: VITE_API_BASE_URL apontando para o backend local

# Subir o servidor de desenvolvimento
npm run dev
```

### Lint e build

```bash
npm run lint
npm run build
```

## Ambiente de produção (Railway)

Projeto Railway: **`helence-orcamento`**.

| Serviço | URL |
|---|---|
| Backend (API) | https://backend-production-bbe9.up.railway.app |
| Frontend | https://frontend-production-c2a9.up.railway.app |

Detalhes de configuração (Volume, variáveis de ambiente, deploy) em
[`docs/09-implantacao-operacao.md`](docs/09-implantacao-operacao.md),
seção 18.0.

## Estrutura do repositório

```
helence-orcamento/
├── backend/        # API FastAPI + SQLite
├── frontend/       # Aplicação React + TypeScript + Vite
├── docs/           # Documentação de domínio, arquitetura e plano
└── .github/        # Workflows de CI
```

Para mais detalhes (variáveis de ambiente, migrations, deploy na
Railway, backup/restore), consulte
[`docs/09-implantacao-operacao.md`](docs/09-implantacao-operacao.md).
