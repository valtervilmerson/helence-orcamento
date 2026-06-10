# Implantação e operação — Helence Orçamento

> Manual de instalação, execução e operação da aplicação. Construído
> sobre as decisões de arquitetura já tomadas em
> `docs/06-arquitetura-api.md` (estrutura de pastas, storage, logs,
> backup, migrations) e `docs/03-modelagem-sqlite.md` (schema/SQLite).
>
> **Status do projeto**: este documento descreve como a aplicação
> **deve** ser instalada e operada, conforme desenhado — a estrutura
> `backend/`/`frontend/` ainda será criada na Fase 0 de
> `docs/07-plano-implementacao.md`. Os comandos abaixo assumem a stack
> já decidida (FastAPI + SQLite no backend, React + TypeScript + Vite
> no frontend); ajuste nomes de comandos se a Fase 0 escolher
> ferramentas equivalentes diferentes (ex. `pnpm` em vez de `npm`).
>
> **Decisão de hospedagem**: o ambiente de produção (uso real interno)
> roda na **Railway** (railway.app). As seções 11–18 abaixo foram
> ajustadas para refletir essa decisão — em particular: persistência de
> `backend/data/` (banco SQLite + uploads) via **Railway Volume**,
> variáveis de ambiente configuradas no painel/CLI da Railway (não em
> arquivos `.env` no servidor), logs em **stdout** (capturados pelo
> *log stream* da Railway, em vez de arquivo rotacionado em disco), e
> deploy via *push* para o repositório Git conectado ao serviço Railway
> (build automático, sem `systemd`/Docker Compose manual). Ambientes
> **locais de desenvolvimento** continuam usando `.env` e os comandos
> das seções 4–9 normalmente.

---

## 1. Pré-requisitos

| Ferramenta | Versão mínima recomendada | Por quê |
|---|---|---|
| **Python** | 3.11+ | Backend (FastAPI). Versões anteriores não são testadas. |
| **Node.js** | 20 LTS+ | Build do frontend (Vite + React + TS). |
| **npm** (ou `pnpm`/`yarn`) | acompanha o Node | Gerenciador de pacotes do frontend — fixar o mesmo em todo o time via *lockfile*. |
| **SQLite** | 3.35+ (suporte a `ALTER TABLE` parcial usado pelas migrations) | Embutido no Python (`sqlite3`) — não requer instalação separada na maioria dos sistemas. |
| **Git** | qualquer versão recente | Controle de versão. |
| **Docker** | recomendado (seção 11) | A Railway pode buildar via Nixpacks (sem Dockerfile) ou via Dockerfile próprio — ter um `Dockerfile` testado localmente facilita reproduzir o build de produção. |
| **Railway CLI** (`railway`) | opcional, recomendado | `railway login`, `railway run`, `railway logs`, `railway volume` — útil para depurar variáveis de ambiente e rodar comandos pontuais (ex. `railway run python -m app.db.migrate`) contra o ambiente de produção. |

**Verificação rápida**:
```bash
python3 --version
node --version
npm --version
sqlite3 --version   # opcional — útil para inspecionar o banco manualmente
```

> ⚠ **Variáveis de ambiente**: nenhum segredo (senhas, chaves) deve ser
> commitado. Use um arquivo `.env` (não versionado — adicionar a
> `.gitignore`) baseado em `.env.example` (versionado, ver seção 3).

---

## 2. Estrutura de diretórios

Reproduzida de `docs/06-arquitetura-api.md`, seção 2 — esta é a
estrutura **alvo** depois da Fase 0:

```
helence-orcamento/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── connection.py
│   │   │   └── migrations/
│   │   │         0001_initial.sql
│   │   │         0002_...
│   │   ├── shared/            # errors, logging, pagination, auth
│   │   ├── files/              # storage.py — abstração de upload
│   │   ├── imports/            # importação de PDFs
│   │   ├── catalog/            # catálogo normalizado
│   │   ├── quotes/              # orçamentos
│   │   └── auth/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── data/
│   │   ├── helence.db          # banco SQLite (NÃO versionado)
│   │   └── uploads/             # PDFs originais (NÃO versionado)
│   ├── logs/                    # logs rotacionados (NÃO versionado)
│   ├── .env                     # variáveis de ambiente locais (NÃO versionado)
│   ├── .env.example              # modelo versionado
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   ├── .env                     # variáveis do Vite (NÃO versionado)
│   ├── .env.example
│   └── package.json
│
├── docs/                         # este e os documentos anteriores
├── data/                         # amostras/insumos de domínio (PDF/planilha originais)
└── scripts/
    ├── spikes/                   # spikes exploratórios (não fazem parte da app)
    ├── backup.sh                 # ver seção 12
    └── restore.sh                # ver seção 13
```

**Diretórios que precisam existir em runtime mas não são versionados**
(criar via `.gitkeep` + `.gitignore`, ou criação automática no
*startup*):
- `backend/data/` (e `backend/data/uploads/`)
- `backend/logs/` — apenas em desenvolvimento local; em produção
  (Railway) os logs vão para stdout (seção 14), não para arquivo.

> **Railway**: `backend/data/` (banco SQLite + `uploads/`) deve ser
> montado sobre um **Volume** da Railway (disco persistente associado
> ao serviço), apontando `DATABASE_PATH`/`UPLOADS_DIR` para o
> *mount path* do volume (ex. `/data/helence.db`,
> `/data/uploads`). Sem volume, o sistema de arquivos do contêiner é
> **efêmero** — qualquer redeploy ou reinício apaga o banco e os PDFs
> enviados (seção 11.2).

---

## 3. Variáveis de ambiente

### 3.1 Backend (`backend/.env`)

| Variável | Exemplo | Descrição |
|---|---|---|
| `APP_ENV` | `development` \| `production` | Controla nível de log, exposição de stack trace, `reload` do servidor. |
| `DATABASE_PATH` | `./data/helence.db` | Caminho do arquivo SQLite (relativo a `backend/`). |
| `UPLOADS_DIR` | `./data/uploads` | Diretório de armazenamento dos PDFs originais (`docs/06`, seção 6). |
| `MAX_UPLOAD_SIZE_MB` | `50` | Limite de tamanho de upload (`docs/06`, seção 6.1). |
| `SECRET_KEY` | *(gerar — ver abaixo)* | Chave de assinatura de sessão (`docs/06`, seção 13). **Nunca** usar valor padrão em produção. |
| `SESSION_COOKIE_SECURE` | `false` (dev) / `true` (prod) | Cookie de sessão só em HTTPS quando `true`. |
| `LOG_LEVEL` | `INFO` | `DEBUG` em desenvolvimento, `INFO`/`WARNING` em produção. |
| `LOG_DIR` | `./logs` | Diretório de logs estruturados rotacionados (`docs/06`, seção 8). |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origem(ns) do frontend permitidas (separadas por vírgula). |
| `BACKUP_DIR` | `./backups` | Destino padrão dos backups locais (seção 12) — recomenda-se apontar para um disco/volume separado. |

**Gerar `SECRET_KEY`**:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 Frontend (`frontend/.env`)

| Variável | Exemplo | Descrição |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | URL base da API consumida pelo cliente HTTP (`docs/06`, seção 5). |

### 3.3 `.env.example`

Cada `.env.example` deve listar **todas** as chaves acima com valores
de exemplo (não-secretos) — é o contrato que qualquer pessoa nova segue
para configurar seu ambiente local. Manter `.env` no `.gitignore` de
ambos os projetos.

### 3.4 Variáveis de ambiente na Railway

Em produção, **não existe arquivo `.env` no servidor** — todas as
variáveis das tabelas 3.1/3.2 são cadastradas no painel do serviço
(*Variables*) ou via `railway variables set` da CLI. Pontos de atenção:

- `DATABASE_PATH` e `UPLOADS_DIR` devem apontar para dentro do *mount
  path* do Volume (seção 2), ex. `/data/helence.db` e `/data/uploads`.
- `APP_ENV=production`, `SESSION_COOKIE_SECURE=true` — a Railway expõe
  o serviço sempre via HTTPS (domínio `*.up.railway.app` ou domínio
  customizado), então o cookie seguro pode (e deve) ficar ativo desde o
  primeiro deploy.
- `CORS_ALLOWED_ORIGINS` deve incluir o domínio público do frontend na
  Railway (ex. `https://helence-orcamento.up.railway.app` ou o domínio
  customizado configurado).
- `LOG_DIR` não é usado em produção (seção 14) — pode ficar ausente ou
  ser ignorado pela aplicação quando `APP_ENV=production`.
- `BACKUP_DIR` deve apontar para um caminho dentro do mesmo Volume
  apenas como destino **temporário**; o destino final do backup precisa
  ser **externo** ao serviço (seção 12.3), já que o Volume da Railway
  não substitui um backup fora da plataforma.
- `SECRET_KEY` é gerada uma vez (seção 3.1) e cadastrada como variável
  — nunca commitada, nunca gerada automaticamente a cada deploy (isso
  invalidaria sessões ativas a cada redeploy).

---

## 4. Instalação — backend

```bash
cd backend

# 1. Ambiente virtual isolado
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependências (a definir em pyproject.toml na Fase 0)
pip install -e ".[dev]"

# 3. Configuração
cp .env.example .env
# editar .env: gerar SECRET_KEY (seção 3.1), ajustar caminhos se necessário

# 4. Diretórios de runtime (se não criados automaticamente no startup)
mkdir -p data/uploads logs
```

> **Lockfile**: o `pyproject.toml`/`requirements*.txt` deve fixar
> versões exatas (não apenas limites mínimos) para reduzir o risco de
> "funciona na minha máquina" (`docs/07`, Fase 0, riscos).

---

## 5. Instalação — frontend

```bash
cd frontend

# 1. Dependências (lockfile commitado garante reprodutibilidade)
npm ci

# 2. Configuração
cp .env.example .env
# editar .env: VITE_API_BASE_URL apontando para o backend local
```

> Use `npm ci` (não `npm install`) em qualquer ambiente além do
> desenvolvimento ativo — `ci` respeita o `package-lock.json`
> exatamente, sem recalcular versões.

---

## 6. Inicialização do banco SQLite

O SQLite **não exige** um passo de "criação" separado — o arquivo
(`DATABASE_PATH`, ex. `backend/data/helence.db`) é criado
automaticamente na primeira conexão. O que **precisa** acontecer
explicitamente:

1. **`PRAGMA foreign_keys = ON`** deve ser executado em **toda
   conexão** aberta pela aplicação (`backend/app/db/connection.py`) —
   o SQLite não persiste essa configuração no arquivo
   (`docs/03`, nota da seção 3). Verificar isso é o primeiro passo de
   troubleshooting de qualquer problema de integridade referencial.
2. **Aplicar as migrations** (seção 7) — sem elas o arquivo existe mas
   está vazio (nenhuma tabela).

**Verificação manual** (após migrations aplicadas):
```bash
sqlite3 backend/data/helence.db ".tables"
sqlite3 backend/data/helence.db "PRAGMA foreign_key_check;"   # deve retornar vazio
sqlite3 backend/data/helence.db "PRAGMA integrity_check;"     # deve retornar 'ok'
```

---

## 7. Migrations

Conforme `docs/06`, seção 10 — scripts numerados em
`backend/app/db/migrations/`, registrados em `schema_migrations`.

**Aplicar migrations pendentes**:
```bash
cd backend
python -m app.db.migrate          # nome exato do comando a confirmar na Fase 0
```

- A aplicação **também** aplica migrations pendentes automaticamente no
  `main.py`, antes de aceitar requisições — recusa subir se alguma
  falhar (`docs/06`, seção 10). O comando manual acima existe para
  rodar a etapa **isoladamente** (ex. em CI, ou antes de iniciar o
  servidor numa atualização — seção 14).
- **Idempotência**: rodar o comando duas vezes seguidas não falha nem
  duplica nada — `schema_migrations` registra o que já foi aplicado.
- **`0001_initial.sql`** corresponde a `docs/schema/schema.sql` (24
  tabelas + 32 índices). Migrations seguintes são aditivas; alterações
  destrutivas seguem o procedimento de recriação de tabela documentado
  na própria migration (SQLite não suporta `DROP COLUMN`/`RENAME
  COLUMN` de forma universal).

**Seed de dados de referência** (Fase 1 de `docs/07`): após as
migrations, popular dados mínimos para destravar o desenvolvimento —
usuários de teste (um por papel: Importador/Revisor/Aprovador/Vendedor/
Auditor) e uma `price_table` vazia em status `vigente` (evita
`NENHUMA_TABELA_VIGENTE` ao testar a criação de orçamentos):
```bash
python -m app.db.seed              # nome exato a confirmar na Fase 0
```

---

## 8. Diretórios de upload

`backend/data/uploads/` armazena os PDFs originais, nomeados pelo
próprio hash SHA-256 (`<sha256>.pdf` — `docs/06`, seção 6.4).

- **Criação**: deve existir antes do primeiro upload — criar
  manualmente (`mkdir -p backend/data/uploads`) ou garantir que
  `files/storage.py` cria o diretório no *startup* se ausente.
- **Permissões**: o usuário/processo que roda o backend precisa de
  permissão de leitura/escrita neste diretório (e em
  `backend/data/` para `helence.db`).
- **Retenção**: PDFs originais **nunca são descartados** — são parte
  da cadeia de rastreabilidade (`docs/06`, seção 6.6). Não criar jobs
  de limpeza automática para este diretório (contraste com a seção 15,
  que trata de **outros** arquivos temporários).
- **Espaço em disco**: monitorar o crescimento de `uploads/` —
  cresce de forma permanente e proporcional ao número de importações
  (não ao número de catálogos publicados).
- **Backup**: este diretório faz parte do backup (seção 12) — copiar só
  `helence.db` sem `uploads/` quebra a rastreabilidade numa restauração.

---

## 9. Comandos de desenvolvimento

### 9.1 Backend
```bash
cd backend
source .venv/bin/activate

# aplica migrations pendentes e sobe com reload automático
uvicorn app.main:app --reload --port 8000
```

- Healthcheck: `GET http://localhost:8000/api/v1/health` → `200`.
- Documentação interativa (gerada pelo FastAPI): `http://localhost:8000/docs`
  e schema OpenAPI em `http://localhost:8000/api/v1/openapi.json`
  (usado pelo frontend para gerar tipos TS — `docs/06`, seção 5).

### 9.2 Frontend
```bash
cd frontend
npm run dev
```
- Sobe em `http://localhost:5173` (padrão Vite), consumindo a API em
  `VITE_API_BASE_URL`.

### 9.3 Testes
```bash
# backend — unitários e de integração (docs/08-testes-qualidade.md)
cd backend
pytest tests/unit
pytest tests/integration
pytest -m "not slow"     # exclui o teste de gabarito de extração (categoria 2.10)

# frontend — build sem erros (critério de aceite da Fase 0)
cd frontend
npm run build
npm run lint
```

### 9.4 Lint/format
```bash
# backend (ferramenta exata a definir na Fase 0 — ex. ruff/black)
ruff check .
ruff format .

# frontend
npm run lint
npm run format
```

---

## 10. Comandos de produção

> "Produção", neste contexto, significa **uso real interno** (`docs/06`,
> seção 7) — não necessariamente infraestrutura de larga escala.

### 10.1 Build do frontend
```bash
cd frontend
npm ci
npm run build           # gera frontend/dist/
```

O backend serve `frontend/dist/` como arquivos estáticos — **ou** o
frontend é hospedado como um serviço Railway separado, apontando
`VITE_API_BASE_URL` para o domínio público do backend (ver seção 11.1
para a comparação entre as duas opções na Railway).

### 10.2 Backend
```bash
cd backend
source .venv/bin/activate
pip install -e .                 # sem extras de dev em produção

# aplica migrations explicitamente antes de subir (recomendado em produção)
python -m app.db.migrate

# servidor de produção (sem --reload; ajustar workers conforme CPU disponível)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

> ⚠ **Atenção a múltiplos workers com SQLite**: SQLite serializa
> escritas (`docs/06`, seção 11.3). Para uma aplicação interna de baixa
> concorrência, 1–2 workers são suficientes e seguros. **Não** escalar
> para muitos workers/processos sem revisar a estratégia de acesso ao
> banco — concorrência de escrita alta é o sinal mencionado em
> `docs/06` para reconsiderar PostgreSQL.

### 10.3 Processo persistente

> Em produção (Railway), a plataforma **é** o supervisor de processo —
> não é necessário configurar `systemd`/`pm2`/Docker Compose
> manualmente. Esta subseção descreve o que a Railway já cobre e o que
> ainda precisa ser garantido pela aplicação. Para quem rodar fora da
> Railway (ex. servidor próprio), as opções abaixo continuam válidas:
> **systemd** (unit file com `Restart=on-failure`), Docker com
> `restart: unless-stopped`, ou `pm2`/`supervisord`.

Garantir, em qualquer ambiente:
- **Reinício automático em caso de falha** — coberto nativamente pela
  Railway (reinicia o contêiner se o processo morrer ou falhar o
  *healthcheck*, seção 11.3).
- Variáveis de ambiente carregadas do ambiente do processo (`.env`
  local em desenvolvimento; *Variables* da Railway em produção — seção
  3.4) — nunca *hardcoded* no comando.
- `APP_ENV=production` (desativa `--reload`, reduz verbosidade de
  stack traces nas respostas — `docs/06`, seção 9).

---

## 11. Implantação na Railway

A Railway é a plataforma de hospedagem decidida para o ambiente de
produção (uso real interno). Ela builda a aplicação a partir do
repositório Git (push automático para deploy), provê HTTPS/domínio
gerenciado, *health checks*, restart automático e *log streaming* —
substituindo a necessidade de `systemd`/Docker Compose/Nginx manuais.

### 11.1 Topologia de serviços

Recomendação: **dois serviços** dentro do mesmo projeto Railway,
ambos apontando para o mesmo repositório (diretórios `backend/` e
`frontend/` como *root directory* de cada serviço):

- **`backend`** — FastAPI (Uvicorn), com o **Volume** persistente
  montado (seção 2/3.4).
- **`frontend`** — build estático do Vite (`npm run build`), servido
  pela própria Railway (Nixpacks detecta projetos Vite/estáticos) ou
  por um pequeno servidor estático (ex. `serve`/`vite preview` não é
  recomendado para produção).

> **Alternativa mais simples** (válida para o MVP): o backend serve
> `frontend/dist/` como arquivos estáticos (FastAPI
> `StaticFiles`/`SPAStaticFiles`), publicando **um único serviço**
> Railway. Reduz custo e complexidade operacional às custas de acoplar
> o deploy do frontend ao do backend — aceitável enquanto a equipe for
> pequena. Esta decisão pode ser revisada sem impacto no modelo de
> dados ou na API.

### 11.2 Build e start

- **Build**: Nixpacks detecta automaticamente Python (backend,
  `pyproject.toml`) e Node (frontend, `package.json`). Caso o
  comportamento automático não seja suficiente, um `Dockerfile` por
  serviço dá controle total do build — ambas as opções são suportadas
  pela Railway sem mudança de arquitetura.
- **Start command** do backend:
  ```bash
  python -m app.db.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
  ```
  - A Railway injeta a porta via variável `$PORT` — o comando de start
    **deve** usar essa variável, não uma porta fixa (ex. `8000`).
  - Como já discutido (`docs/06`, seção 10), as migrations também
    rodam automaticamente no `main.py` no *startup* — incluir o
    comando explícito no *start command* é uma camada extra de
    segurança (falha cedo, antes do `uvicorn` subir, com log claro no
    *deploy log* da Railway).
- **Start command** do frontend (se servido como serviço separado):
  servir `frontend/dist/` com um servidor estático de produção (ex.
  `npx serve -s dist -l $PORT` ou Nixpacks com builder estático
  nativo).

### 11.3 Healthcheck

Configurar no serviço `backend` o *healthcheck path*
`GET /api/v1/health` (já previsto na seção 9.1). A Railway usa esse
endpoint para decidir se um deploy foi bem-sucedido e para reiniciar o
serviço automaticamente em caso de falha — sem isso, um deploy quebrado
pode ficar "no ar" sem detecção automática.

### 11.4 Volume persistente

- Criar um **Volume** Railway anexado ao serviço `backend`, montado em
  um caminho fixo (ex. `/data`).
- `DATABASE_PATH=/data/helence.db`, `UPLOADS_DIR=/data/uploads` (seção
  3.4).
- **Limitação importante**: um Volume Railway é anexado a **uma única
  instância** do serviço — reforça a decisão já existente (`docs/06`,
  seção 11) de rodar o backend com 1–2 *workers* em **um único
  serviço/instância**, sem escalonamento horizontal. Se no futuro for
  necessário escalar horizontalmente, isso exige migrar de SQLite (em
  Volume) para um banco gerenciado (PostgreSQL — caminho já discutido
  em `docs/06`, seção 11) ou para armazenamento de objeto externo para
  os uploads.

### 11.5 Variáveis de ambiente e domínio

- Configurar todas as variáveis da seção 3.1/3.2 em *Variables* do
  serviço (seção 3.4).
- A Railway gera um domínio público `*.up.railway.app` por serviço
  automaticamente (com HTTPS); um domínio customizado pode ser
  configurado depois sem mudar a aplicação — apenas
  `CORS_ALLOWED_ORIGINS`/`VITE_API_BASE_URL`.

### 11.6 Docker Compose (apenas para desenvolvimento local)

Não obrigatório para o MVP. Útil **apenas** para padronizar o ambiente
entre máquinas/desenvolvedores localmente — **não** é o mecanismo de
deploy de produção (que é a Railway, seções 11.1–11.5).

```yaml
# docker-compose.yml (exemplo de referência — ajustar Dockerfiles)
version: "3.9"

services:
  backend:
    build: ./backend
    env_file: ./backend/.env
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data        # banco + uploads persistidos no host
      - ./backend/logs:/app/logs
    restart: unless-stopped

  frontend:
    build: ./frontend
    env_file: ./frontend/.env
    ports:
      - "5173:80"                        # ex. servido via Nginx no contêiner
    depends_on:
      - backend
    restart: unless-stopped
```

```bash
docker compose up -d --build
docker compose logs -f backend
docker compose down                 # mantém volumes; dados preservados
```

---

## 12. Backup do SQLite

Conforme `docs/06`, seção 12 — usar a **API de Online Backup** do
SQLite (não copiar o arquivo "a frio" com `cp`, que pode capturar um
estado inconsistente se houver escrita concorrente).

> **Railway — atenção**: o sistema de arquivos do contêiner (incluindo
> o Volume montado, seção 11.4) só é acessível **a partir do próprio
> processo da aplicação** em execução — não há acesso SSH/`cron` no
> host, e `railway run script.sh` executa o script **localmente**, sem
> acesso ao Volume remoto. Os scripts `scripts/backup.sh`/
> `scripts/restore.sh` abaixo continuam válidos para **desenvolvimento
> local**, mas em produção o backup precisa ser feito **de dentro da
> aplicação** (seção 12.5).

### 12.1 Script de referência — desenvolvimento local (`scripts/backup.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

DB_PATH="backend/data/helence.db"
UPLOADS_DIR="backend/data/uploads"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${DEST}"

# 1. Backup consistente do banco via API nativa do SQLite
sqlite3 "${DB_PATH}" ".backup '${DEST}/helence.db'"

# 2. Cópia do diretório de uploads (PDFs originais — parte da rastreabilidade)
cp -r "${UPLOADS_DIR}" "${DEST}/uploads"

echo "Backup criado em ${DEST}"
```

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

### 12.2 Frequência e retenção
- **Diário** (job agendado, ex. `cron`/Agendador de Tarefas, fora do
  horário de uso) **+ manual** antes de operações sensíveis — em
  particular, **antes de publicar uma nova versão de tabela de preço**
  (`POST /price-tables/{id}/publish`), a operação que mais altera dados
  de catálogo de uma só vez.
- **Retenção sugerida**: últimos 14 backups diários + 1 snapshot
  mensal — suficiente para reverter erros humanos ("importei o arquivo
  errado", "publiquei a tabela errada") sem acumular indefinidamente.
  Exemplo de poda:
  ```bash
  find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime +14 -name "20*" \
    ! -name "$(date +%Y%m)*" -exec rm -rf {} +
  ```

### 12.3 Local de armazenamento
- O destino de `BACKUP_DIR` deve ficar **fora** do disco onde a
  aplicação roda (outro disco, volume de rede, ou destino de
  armazenamento gerenciado/sincronizado) — um backup no mesmo disco não
  protege contra a falha mais comum (perda do disco).
- **Em produção (Railway)**: "fora do disco" significa fora do Volume
  do serviço — o destino final deve ser um **armazenamento de objeto
  externo** compatível com S3 (ex. AWS S3, Backblaze B2, Cloudflare
  R2), configurado via variáveis de ambiente próprias (ex.
  `BACKUP_S3_BUCKET`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_ACCESS_KEY`,
  `BACKUP_S3_SECRET_KEY` — nomes a confirmar na implementação). O
  Volume da Railway protege contra perda de dados em redeploys/restart,
  mas **não** contra exclusão acidental do projeto/serviço ou corrupção
  do volume — daí a necessidade de um destino verdadeiramente externo.

### 12.4 Verificação periódica
- Testar a **restauração** (seção 13) periodicamente — um backup nunca
  restaurado é uma suposição não verificada. Recomenda-se incluir essa
  verificação no checklist operacional mensal.

### 12.5 Backup em produção — job interno da aplicação

Como o Volume da Railway só é acessível pelo processo em execução
(nota no início da seção 12), o backup de produção deve ser implementado
como uma **rotina agendada dentro da própria aplicação** (ex.
`APScheduler` ou *background task* equivalente, registrada no
`main.py`), e não como um script externo chamado por `cron`:

1. Rodar `sqlite3 .backup` (ou equivalente via `sqlite3` do Python —
   `sqlite3.Connection.backup()`) para um arquivo temporário dentro do
   próprio Volume.
2. Copiar `uploads/` (ou os arquivos novos desde o último backup) junto
   com o `.db` gerado.
3. Enviar o pacote resultante para o armazenamento de objeto externo
   (seção 12.3) via SDK compatível com S3 (ex. `boto3`).
4. Registrar o resultado (sucesso/falha, tamanho, timestamp) no log
   estruturado de domínio (seção 14) — falhas de backup devem ser
   visíveis nos logs de produção, não silenciosas.

Esta rotina é um item da **Fase 11/12** (`docs/07`) — até que esteja
implementada, backups de produção devem ser feitos manualmente via um
endpoint/comando administrativo equivalente, especialmente **antes de
publicar uma nova versão de tabela de preço** (seção 12.2).

---

## 13. Restauração do SQLite

### 13.1 Script de referência (`scripts/restore.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_SOURCE="$1"   # ex. ./backups/20260601_020000
DB_PATH="backend/data/helence.db"
UPLOADS_DIR="backend/data/uploads"

if [ -z "${BACKUP_SOURCE}" ]; then
  echo "Uso: ./scripts/restore.sh <diretorio_do_backup>"
  exit 1
fi

# 1. Parar a aplicação ANTES de restaurar (evita escrita concorrente
#    durante a substituição do arquivo)
echo "Confirme que a aplicação está PARADA antes de continuar (Ctrl+C para abortar)."
read -r _

# 2. Backup de segurança do estado atual (caso a restauração precise ser desfeita)
TS=$(date +%Y%m%d_%H%M%S)
mv "${DB_PATH}" "${DB_PATH}.before_restore_${TS}"
mv "${UPLOADS_DIR}" "${UPLOADS_DIR}.before_restore_${TS}"

# 3. Restaurar
cp "${BACKUP_SOURCE}/helence.db" "${DB_PATH}"
cp -r "${BACKUP_SOURCE}/uploads" "${UPLOADS_DIR}"

# 4. Verificar integridade
sqlite3 "${DB_PATH}" "PRAGMA integrity_check;"
sqlite3 "${DB_PATH}" "PRAGMA foreign_key_check;"

echo "Restauração concluída a partir de ${BACKUP_SOURCE}."
echo "Reinicie a aplicação manualmente."
```

```bash
chmod +x scripts/restore.sh
./scripts/restore.sh ./backups/20260601_020000
```

### 13.2 Procedimento completo
1. **Parar a aplicação** (encerrar `uvicorn`/contêiner) — restaurar com
   a aplicação em execução pode causar leitura/escrita inconsistente.
2. Rodar o script acima, apontando para o backup desejado.
3. Confirmar `PRAGMA integrity_check` → `ok` e
   `PRAGMA foreign_key_check` → vazio.
4. Reiniciar a aplicação e validar com um *smoke test* (login,
   consulta ao catálogo, abertura de um orçamento existente).
5. Se algo der errado, os arquivos `.before_restore_<timestamp>`
   permitem reverter a restauração.

### 13.3 Restauração em produção (Railway)

Pela mesma razão da seção 12 (Volume só acessível pelo processo em
execução), a restauração em produção **não** é feita rodando
`scripts/restore.sh` localmente contra o Volume remoto. O caminho
recomendado:

1. Implementar um **comando/endpoint administrativo** (acessível
   apenas a Aprovador/Admin, ou via `railway run` executando dentro do
   ambiente do serviço — `railway run` permite abrir um shell *dentro*
   do contêiner com `railway shell`, que **tem** acesso ao Volume) que:
   - baixa o pacote de backup desejado do armazenamento externo (seção
     12.3);
   - aplica o mesmo procedimento de cópia de segurança do estado atual
     (`.before_restore_<timestamp>`, como no script de referência)
     **dentro do Volume**;
   - substitui `helence.db` e `uploads/` pelos arquivos restaurados;
   - roda `PRAGMA integrity_check`/`PRAGMA foreign_key_check`.
2. Colocar o serviço em modo de manutenção (ou escalar para 0 réplicas
   temporariamente, se a Railway permitir) durante a restauração, para
   evitar escrita concorrente.
3. Reiniciar o serviço (redeploy ou restart manual) e validar com o
   mesmo *smoke test* da seção 13.2.

Esta rotina, assim como o backup (seção 12.5), é um item da Fase 11/12
— até lá, uma restauração de produção exige acesso via `railway shell`
e execução manual dos passos do `scripts/restore.sh` **dentro** do
contêiner (não na máquina local).

---

## 14. Logs

Conforme `docs/06`, seção 8 — logs estruturados (JSON, um evento por
linha), com três focos: **requisição** (middleware), **domínio**
(decisões de negócio — revisão, publicação, bloqueios) e **erro**
(exceções não tratadas, com `request_id` e *stack trace*).

### 14.1 Localização e formato
- **Desenvolvimento**: saída para console (stdout), nível `DEBUG`.
- **Produção (Railway)**: saída para **stdout/stderr** (JSON
  estruturado, um evento por linha), nível `INFO`/`WARNING` — a Railway
  captura automaticamente a saída padrão do processo e a expõe no *log
  stream* do serviço (painel web, `railway logs`, ou *log drains* para
  um agregador externo). **Não** usar `RotatingFileHandler`/arquivo em
  `LOG_DIR` em produção: o sistema de arquivos do contêiner é efêmero
  fora do Volume (seção 2), e escrever logs no Volume desperdiçaria
  espaço de armazenamento que deveria ser reservado para
  banco+uploads.
- **Retenção de logs na Railway**: o *log stream* da Railway tem
  retenção limitada (verificar o limite do plano contratado). Se for
  necessário reter logs por mais tempo do que a plataforma oferece,
  configurar um *log drain* para um agregador externo (ex. Logtail,
  Better Stack, Datadog) — isso é tratado como evolução pós-MVP
  (`docs/06`, seção 8, "sem observabilidade externa").

### 14.2 Correlação
- Todo log de requisição/erro carrega `request_id` — o mesmo valor
  retornado no cabeçalho HTTP de respostas de erro (`docs/06`, seção
  9). Para investigar um erro relatado por um usuário, busque pelo
  `request_id` exibido na tela de erro (se exposto) ou peça o horário
  aproximado e correlacione pelo log de requisição.

### 14.3 Comandos úteis

**Desenvolvimento local**:
```bash
# acompanhar em tempo real (saída via console/redirecionada para arquivo local)
tail -f backend/logs/app.log

# filtrar por request_id
grep '"request_id":"<id>"' backend/logs/app.log

# filtrar erros
grep '"level":"ERROR"' backend/logs/app.log
```

**Produção (Railway)**:
```bash
# acompanhar em tempo real
railway logs --service backend --follow

# filtrar por request_id (cada linha é JSON — usar jq)
railway logs --service backend | grep '"request_id":"<id>"'

# filtrar erros
railway logs --service backend | grep '"level":"ERROR"'
```
Ou usar o painel web da Railway (aba *Deployments* → *Logs*), que
permite busca/filtro sem CLI.

### 14.4 O que NUNCA aparece nos logs
Senhas, conteúdo de sessão/cookies, dados pessoais de cliente além do
estritamente necessário (ex. `customer_id`, nunca `customer.document`)
— `docs/06`, seção 8.

### 14.5 Retenção de logs
- **Desenvolvimento**: definir uma política de rotação/retenção (ex.
  manter últimos 30 dias) — evita que `backend/logs/` cresça
  indefinidamente.
- **Produção (Railway)**: a retenção é controlada pelo plano da
  Railway (seção 14.1) — não há `logrotate` para configurar. Se a
  retenção padrão não for suficiente, a mitigação é um *log drain*
  externo, não uma política de arquivo local.

Esta política, junto com a de backups (seção 12), é um item
explicitamente reservado para a Fase 11 de `docs/07` ("Política de
retenção de logs e backups em produção").

---

## 15. Limpeza de arquivos temporários

> **Não confundir** com o diretório de uploads (seção 8), que **nunca**
> deve ser limpo automaticamente.

Candidatos a limpeza periódica (conforme forem introduzidos pela
implementação):
- **Arquivos de exportação temporários** (Fase 10, `docs/06` 14.14) —
  se a geração de PDF/planilha gravar arquivos intermediários em disco
  antes do download, definir um TTL curto (ex. remover após 1h ou após
  o download confirmado).
- **Backups de restauração** (`*.before_restore_*`, seção 13) — remover
  manualmente após confirmar que a restauração foi bem-sucedida e não
  precisa ser revertida.
- **Logs antigos** além da política de retenção (seção 14.5), se não
  geridos por `logrotate`.
- **Banco de testes** (`backend/tests/...`) — arquivos SQLite
  temporários de teste devem ser criados em diretório temporário do SO
  (`tempfile`) e removidos automaticamente ao final de cada execução de
  teste; nunca persistidos no repositório.

**Script de exemplo** (executar periodicamente, ex. semanal):
```bash
# remove backups de restauração com mais de 30 dias
find backend/data -maxdepth 1 -name "*.before_restore_*" -mtime +30 -exec rm -rf {} +
```

---

## 16. Atualização da aplicação

### 16.1 Passo a passo (produção — Railway)

Na Railway, o deploy é disparado por **push** para a branch conectada
ao serviço (ex. `main`) — não há passo manual de "reiniciar o serviço"
separado do deploy:

```bash
# 1. Backup ANTES de atualizar (seção 12) — sempre, sem exceção.
#    Em produção, isso significa: confirmar que o job de backup
#    interno (seção 12.5) rodou recentemente, ou disparar um backup
#    manual via o comando/endpoint administrativo (seção 12.5).

# 2. Atualizar o código (no repositório, localmente)
git fetch
git checkout main
git pull

# 3. Validar localmente ANTES de empurrar (seção 9.3)
cd backend && pytest -m "not slow"
cd ../frontend && npm run build && npm run lint

# 4. Push para a branch conectada ao(s) serviço(s) Railway
#    -> dispara o build e deploy automaticamente em backend/frontend
git push origin main
```

A Railway então: builda a imagem, roda o *start command* (que inclui
`python -m app.db.migrate`, seção 11.2 — aplica migrations novas de
forma idempotente), espera o *healthcheck* (`GET /api/v1/health`,
seção 11.3) responder `200`, e só então direciona tráfego para a nova
versão (zero-downtime na maioria dos casos). Se o *healthcheck* falhar,
a Railway mantém a versão anterior no ar e marca o deploy como falho.

### 16.2 Checklist pós-atualização
- [ ] Deploy marcado como bem-sucedido no painel da Railway
      (*healthcheck* passou).
- [ ] Migrations aplicadas sem erro (`schema_migrations` reflete a
      versão mais recente — conferir no log de deploy, seção 14.3).
- [ ] `GET /api/v1/health` → `200` (no domínio público do serviço).
- [ ] *Smoke test* manual: login, consulta ao catálogo, abrir um
      orçamento existente, criar um novo orçamento de teste.
- [ ] Logs (seção 14) sem erros inesperados nos primeiros minutos após
      o deploy (`railway logs --follow`).

### 16.3 Rollback
Se algo falhar após a atualização:
1. **Re-deploy da versão anterior** pelo painel da Railway (aba
   *Deployments* → selecionar o deploy anterior → *Redeploy*) — mais
   rápido que reverter via Git para um incidente em produção.
2. Em paralelo, reverter o código no repositório
   (`git revert`/`git checkout <commit_anterior>` + novo push) para que
   a branch `main` volte a refletir o estado em produção.
3. **Migrations são aditivas** (`docs/06`, seção 10) — normalmente não
   é necessário reverter o schema para voltar a uma versão anterior do
   código, **exceto** se a migration nova alterou dados de forma
   incompatível com o código antigo. Nesse caso, restaurar o backup
   feito antes do deploy (seção 13.3) é o caminho seguro.

### 16.4 Ambiente de desenvolvimento local

O passo a passo de desenvolvimento local (rodar migrations, build do
frontend, restart manual) continua como nas seções 4–9 — a mudança
desta seção 16 se aplica apenas ao fluxo de **deploy em produção**.

---

## 17. Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `PRAGMA foreign_key_check` retorna linhas / inserções com FK inválida não são rejeitadas | `PRAGMA foreign_keys = ON` não foi executado nesta conexão (`docs/03`, nota da seção 3 — não é persistido pelo SQLite) | Verificar `backend/app/db/connection.py` — a pragma deve ser setada **a cada** abertura de conexão, não uma vez globalmente. |
| Aplicação não sobe: erro de migration | Migration nova falhou (sintaxe, conflito de schema) | Ler o erro completo no log de *startup*; corrigir a migration; **não** editar uma migration já aplicada em outro ambiente — criar uma nova migration corretiva. |
| `database is locked` | Múltiplos processos/workers escrevendo simultaneamente no SQLite, ou uma transação longa não finalizada | Reduzir `--workers` para 1–2 (seção 10.2); verificar se algum código mantém uma transação aberta sem `commit`/`rollback`; para uso muito concorrente, revisar `docs/06` seção 11 (migração futura para PostgreSQL). |
| `ARQUIVO_DUPLICADO` ao reenviar um PDF que parece diferente | O `sha256` é calculado sobre o **conteúdo** do arquivo — PDFs "iguais visualmente" mas re-exportados podem ter hash diferente, e vice-versa (raro) | Comparar `sha256sum` dos dois arquivos; se forem realmente idênticos, o comportamento está correto (`docs/06`, seção 6.3). |
| Upload rejeitado com `ARQUIVO_MUITO_GRANDE`/`ARQUIVO_INVALIDO` | Arquivo excede `MAX_UPLOAD_SIZE_MB` ou não é um PDF válido | Verificar tamanho/MIME do arquivo; ajustar `MAX_UPLOAD_SIZE_MB` apenas se houver justificativa real (PDFs observados na auditoria são bem menores que 50MB). |
| Frontend não consegue falar com a API (`CORS`/`Network Error`) | `VITE_API_BASE_URL` incorreta, ou `CORS_ALLOWED_ORIGINS` no backend não inclui a origem do frontend | Conferir as duas variáveis (seção 3); reiniciar ambos após alterar `.env`. |
| `ITEM_SEM_PRECO`/`ITEM_SEM_SKU` inesperado para um item que "deveria" ter preço | Tabela de preço errada está marcada `vigente`, ou a publicação (Fase 7) não promoveu essa variação | Consultar `price_tables` (`status='vigente'`); usar a consulta "auditar origem de preço" (`docs/03`, 6.5) para confirmar se existe `prices` para a variação na tabela vigente. |
| Logs não aparecem (produção) | Em desenvolvimento: `APP_ENV` ainda em `development`. Em produção (Railway): aplicação está escrevendo em arquivo/`LOG_DIR` em vez de stdout (seção 14.1) | Confirmar `APP_ENV=production`; garantir que o *handler* de log em produção escreve em stdout/stderr, não em arquivo. |
| Erro `500` genérico para o usuário, sem detalhe | Comportamento **esperado** — exceções não previstas nunca vazam *stack trace*/SQL na resposta (`docs/06`, seção 9) | Buscar o `request_id` (cabeçalho da resposta) no log de erro (seção 14.2) para ver o detalhe completo. |
| Restauração falha com `PRAGMA integrity_check` != `ok` | Backup corrompido (cópia "a frio" feita incorretamente) ou arquivo truncado | Tentar um backup anterior na sequência de retenção (seção 12.2); revisar se o backup foi feito com `.backup` (API online), não `cp` direto no arquivo em uso. |
| Deploy bem-sucedido, mas dados (banco/uploads) "zerados" após redeploy | Volume não está montado, ou `DATABASE_PATH`/`UPLOADS_DIR` não apontam para o caminho do Volume (seção 11.4) | Conferir no painel Railway que o Volume está anexado ao serviço **e** que as variáveis de ambiente apontam para o *mount path* correto (ex. `/data/...`). |
| Deploy falha no *healthcheck*, versão anterior continua no ar | `GET /api/v1/health` não responde `200` dentro do tempo esperado (erro de migration, exceção no `startup`, porta incorreta) | Ler o *deploy log* (`railway logs` ou painel) — confirmar que o processo está escutando em `$PORT` (seção 11.2) e que as migrations aplicaram sem erro. |
| `database is locked` mais frequente após mover para Railway | Volume em rede pode ter latência de I/O maior que disco local; combinado com >1 worker aumenta chance de contenção | Confirmar `--workers 1` ou `2` (seção 10.2/11.2); se persistir, é o sinal documentado em `docs/06` seção 11 para considerar PostgreSQL gerenciado. |

---

## 18. Checklist de deploy

Use antes de colocar uma nova versão em uso real (primeiro deploy ou
atualização — complementa a seção 16.2):

### 18.0 Primeiro deploy — configuração do projeto Railway (uma vez)

> **Status (Fase 0)**: projeto criado e primeiro deploy ("hello world")
> validado em ambos os serviços. Falta apenas **conectar o repositório
> Git** pela dashboard (ver nota abaixo) — até lá, atualizações são
> publicadas via `railway up` (deploy manual a partir do diretório
> local).

- [x] Projeto Railway criado: **`helence-orcamento`** (workspace
      `valtervilmerson's Projects`).
- [ ] Repositório Git conectado (branch `main`) — **pendente**: a CLI
      retornou `Unauthorized` ao tentar `railway add --repo
      valtervilmerson/helence-orcamento`, porque o GitHub App da
      Railway ainda não está autorizado para este repositório/conta.
      Ação manual única: na dashboard do projeto, em cada serviço →
      *Settings → Source*, clicar em *Connect Repo*, autorizar o
      GitHub App para `valtervilmerson/helence-orcamento` e definir o
      *Root Directory* (`backend` ou `frontend`, conforme o serviço).
      Depois disso, `git push` para `main` passa a disparar deploy
      automático (seção 16).
- [x] Serviço(s) configurado(s) conforme seção 11.1 — **dois
      serviços**: `backend` e `frontend`, ambos com build via
      `Dockerfile`/`railway.toml` próprios (seção 11.2).
- [x] **Volume** criado e anexado ao serviço `backend`
      (`backend-volume`, 5 GB), *mount path* `/data` (seção 11.4).
      `DATABASE_PATH=/data/helence.db`,
      `UPLOADS_DIR=/data/uploads`, `BACKUP_DIR=/data/backups`.
- [x] *Healthcheck path* `GET /api/v1/health` configurado no serviço
      `backend` via `backend/railway.toml` (seção 11.3) — validado:
      primeiro deploy passou no healthcheck.
- [x] *Start command* configurado usando `$PORT` (seção 11.2) — `CMD`
      do `Dockerfile` de cada serviço.
- [x] Domínio público gerado para os dois serviços:
      - Backend: `https://backend-production-bbe9.up.railway.app`
      - Frontend: `https://frontend-production-c2a9.up.railway.app`
- [x] Variáveis de ambiente de produção cadastradas no serviço
      `backend` (`APP_ENV=production`, `SECRET_KEY` gerada,
      `SESSION_COOKIE_SECURE=true`, `CORS_ALLOWED_ORIGINS` apontando
      para o domínio do `frontend`, `LOG_LEVEL=INFO`,
      `MAX_UPLOAD_SIZE_MB=50`) e no serviço `frontend`
      (`VITE_API_BASE_URL` apontando para `/api/v1` do domínio do
      `backend`) — seção 3.4.

### 18.1 Antes do deploy
- [ ] Todos os testes passam (`docs/08-testes-qualidade.md`, seção 3 —
      critérios mínimos de qualidade do MVP).
- [ ] Variáveis de ambiente de produção revisadas no painel Railway
      (seção 3.4): `APP_ENV=production`, `SECRET_KEY` gerada (não o
      valor de exemplo), `SESSION_COOKIE_SECURE=true`,
      `CORS_ALLOWED_ORIGINS` restrito ao(s) domínio(s) reais,
      `DATABASE_PATH`/`UPLOADS_DIR` apontando para o Volume.
- [ ] Backup do estado atual realizado e verificado (seção 12.5).
- [ ] `frontend/dist/` gerado a partir do código atualizado
      (`npm run build`), apontando para a `VITE_API_BASE_URL` correta —
      ou, se servido pelo backend, build incluído no processo de build
      do serviço único (seção 11.1).

### 18.2 Durante o deploy
- [ ] Migrations aplicadas (`python -m app.db.migrate`, parte do *start
      command*, seção 11.2) — confirmar `schema_migrations` atualizado
      no log de deploy.
- [ ] Volume montado e preservado entre deploys — `backend/data/
      uploads/` e `helence.db` **não** recriados do zero (seção 11.4).
- [ ] *Healthcheck* (`GET /api/v1/health`) passou antes da Railway
      direcionar tráfego para a nova versão (seção 11.3).

### 18.3 Após o deploy
- [ ] `GET /api/v1/health` → `200` no domínio público do serviço.
- [ ] `PRAGMA foreign_key_check` e `PRAGMA integrity_check` no banco em
      produção → vazio / `ok`.
- [ ] *Smoke test* dos três módulos: importar (ou listar importações
      existentes), consultar catálogo, abrir/criar um orçamento.
- [ ] Logs (`railway logs`, seção 14.3) sem erros nos primeiros
      minutos.
- [ ] Cada papel de usuário (Importador/Revisor/Aprovador/Vendedor/
      Auditor) consegue logar — se autenticação (Fase 11) já estiver
      implementada.
- [ ] Job de backup automático agendado e testado (seções 12.2/12.5).

---

## 19. Limitações conhecidas do MVP

Estas limitações são **decisões deliberadas** documentadas em
`docs/06-arquitetura-api.md` — não débitos técnicos escondidos. Listadas
aqui para que quem opera o sistema saiba o que **não** esperar:

1. **SQLite, não um servidor de banco** (`docs/06`, seção 11) — adequado
   ao volume e à concorrência de uma aplicação interna. Múltiplas
   instâncias do backend escrevendo simultaneamente **não** são
   suportadas sem revisão arquitetural; rodar com 1–2 *workers*.
2. **Processamento de importação em background *in-process*, sem fila
   externa** (`docs/06`, seção 7) — se o backend reiniciar durante um
   processamento (incluindo um redeploy na Railway), o progresso
   incremental gravado em `imported_pages`/`extracted_items` permanece
   (está no Volume), mas o job em si precisa ser **relançado
   manualmente** (não há *retry* automático no MVP).
3. **Armazenamento de uploads em disco local (Volume Railway)**
   (`docs/06`, seção 6.5) — sem replicação/objeto distribuído, e preso a
   uma única instância (seção 11.4). Backup externo (seção 12.5) é a
   única proteção contra perda do Volume.
4. **Autenticação simples baseada em sessão** (`docs/06`, seção 13) —
   sem SSO/OAuth corporativo, sem MFA. Adequado para uso interno por
   uma equipe pequena conhecida.
5. **Sem observabilidade externa (APM/agregador de logs)** (`docs/06`,
   seção 8) — logs estruturados em stdout, capturados pelo *log stream*
   da Railway (seção 14); investigação depende do painel/CLI da Railway
   ou de configurar um *log drain* externo.
6. **Sem fila de e-mail/notificação** — exportação (Fase 10) gera o
   documento para download; envio automático por e-mail está fora do
   escopo confirmado (`docs/07`, Fase 10).
7. **Backup/restauração dependem de uma rotina interna da aplicação +
   armazenamento externo** (seções 12.5/13.3) — diferente de um banco
   gerenciado com *snapshot* automático; até essa rotina estar
   implementada (Fase 11/12), backup/restauração de produção exigem
   intervenção manual via `railway shell`.
8. **Migrations destrutivas em SQLite são manuais e arriscadas** —
   `ALTER TABLE ... DROP/RENAME COLUMN` não é suportado de forma
   universal; cada caso exige o procedimento de recriação de tabela
   documentado na própria migration (`docs/06`, seção 10). Sempre fazer
   backup (seção 12) antes de aplicar uma migration desse tipo.
9. **Margem e desconto** (RN-09/RN-10 de `docs/05`) — regras ainda
   pendentes de confirmação comercial; o sistema **não** calcula
   margem e a estrutura de desconto é uma proposta inicial, sujeita a
   mudança de schema/comportamento.
10. **Regras de compatibilidade tampo↔estrutura (RN-04)** — modeladas
    como dado de configuração revisável, **inferido** da nomenclatura
    do PDF (não declarado explicitamente pelo fabricante) — pode
    exigir ajustes manuais conforme o catálogo real revelar exceções
    (`docs/05`, pergunta de validação 1).
11. **Sem escalonamento horizontal** — o Volume Railway (seção 11.4)
    prende o backend a uma única instância; aumentar capacidade no MVP
    significa aumentar recursos da instância (*vertical scaling*), não
    adicionar réplicas.
12. **Sem internacionalização** — interface e mensagens de erro em
    português, moeda fixa em `BRL` (`docs/03`, seção 2.12 — valores
    monetários como `NUMERIC`, registro consciente de revisitar antes
    de escalar).
