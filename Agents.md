# Agents.md — Guia de orientação para agentes de IA

> Leia este arquivo antes de qualquer outro. Ele resume o projeto,
> a arquitetura, as convenções e os invariantes que você **não pode quebrar**.
> Para detalhe adicional, os documentos de origem estão em `docs/`.

---

## 1. O que é este projeto

**Helence Orçamento** é um sistema interno B2B para uma equipe pequena
(Importador, Revisor, Admin/Aprovador, Vendedor, Auditor). O cliente final
**nunca acessa o sistema** — ele recebe apenas o PDF de orçamento gerado.

Fluxo principal:

```
Planilha Excel do fabricante
      ↓
Agente IA externo gera JSON (contrato docs/10-contrato-importacao-json.md)
      ↓
POST /api/v1/imports/json  →  extracted_items (fast-path ou fila de revisão)
      ↓ (aprovação humana se necessário)
Catálogo normalizado (component_variants + prices)
      ↓
Vendedor monta orçamento (preço congelado no momento de adição do item)
      ↓
PDF exportado para o cliente
```

---

## 2. Stack e estrutura de diretórios

```
helence-orcamento/
├── backend/                  # FastAPI + SQLite
│   ├── app/
│   │   ├── main.py
│   │   ├── auth/             # JWT, roles (admin/vendedor/revisor/importador/auditor)
│   │   ├── catalog/          # component_variants, finishes, dimensions, families, etc.
│   │   ├── imports/          # json_ingest.py, extraction.py (legado PDF), service.py, router.py
│   │   ├── quotes/           # orçamentos, pricing.py, export.py (PDF)
│   │   ├── settings/         # app_settings (global_markup_percent)
│   │   ├── files/            # storage.py (uploads físicos)
│   │   ├── db/
│   │   │   ├── connection.py
│   │   │   ├── migrate.py
│   │   │   ├── seed.py
│   │   │   └── migrations/   # 0001_initial.sql … 0020_commercial_policy_settings.sql
│   │   └── shared/           # errors.py, logging.py, schemas comuns
│   └── tests/integration/    # pytest, banco SQLite em memória por teste
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── api/              # funções fetch tipadas (catalog.ts, quotes.ts, …)
│       ├── context/          # CatalogContext (famílias, produtos, acabamentos, etc.)
│       ├── pages/
│       │   ├── catalog/      # families, products, variants, finishes, dimensions
│       │   ├── quotes/       # QuotesPage.tsx (lista + form + detalhe)
│       │   ├── imports/      # upload JSON, ReviewPage.tsx
│       │   └── settings/     # SettingsPage.tsx (admin)
│       └── layout/           # AppShell.tsx, sidebar
├── importacao/               # Geradores Python de JSON de importação
│   ├── generate_import_json_reunioes.py
│   ├── generate_import_json_reunioes_p900.py
│   ├── generate_import_json_solucoes_acusticas.py
│   ├── importacao_reunioes.json
│   ├── importacao_reunioes_p900_piloto.json
│   └── importacao_solucoes_acusticas.json
├── docs/
│   ├── 05-regras-orcamento.md        # RN-01 a RN-18 — leia antes de tocar em quotes/
│   ├── 06-arquitetura-api.md         # contratos de todos os endpoints
│   ├── 10-contrato-importacao-json.md # contrato do JSON de importação
│   └── agente-importacao-json/       # CONTRATO.md, README, exemplos para o agente externo
├── data/                     # planilhas Excel fonte (não versionadas no git)
└── Agents.md                 # este arquivo
```

---

## 3. Como rodar localmente

```bash
# Backend (FastAPI, porta 8000)
cd backend
python -m uvicorn app.main:app --reload

# Frontend (Vite, porta 5173)
cd frontend
npm run dev
```

Ou use a skill `/run` do Claude Code, que sobe os dois em paralelo.

Variáveis de ambiente necessárias:
- `backend/.env` — `DATABASE_URL`, `SECRET_KEY`, etc. (ver `docs/09`)
- `frontend/.env` — `VITE_API_BASE_URL=http://localhost:8000/api/v1`

Banco é criado automaticamente em `data/helence.db` ao subir o backend
(migrations + seed rodam via `app/db/migrate.py` no startup).

---

## 4. Como rodar os testes

```bash
cd backend
pytest tests/integration/ -v
```

Cada teste recebe um banco SQLite **em memória** isolado (via `conftest.py`).
Não há mocks de banco — os testes batem em banco real. Não mude isso.

Arquivos de teste relevantes:
- `test_imports_json.py` — fast path, revisão, deduplicação, variantes distintas
- `test_publish.py` — publicação de itens aprovados no catálogo
- `test_quotes.py` — ciclo de vida de orçamento, congelamento de preço
- `test_review.py` — aprovação, correção, rejeição de itens

---

## 5. Importação de preços (caminho ativo)

O único caminho ativo de importação é via **JSON estruturado**:

```
POST /api/v1/imports/json
Content-Type: application/json
```

O JSON segue o contrato de `docs/10-contrato-importacao-json.md` e
`docs/agente-importacao-json/CONTRATO.md`. Pontos-chave:

- Itens referenciam entidades **por nome** (família, produto, componente,
  dimensão, acabamento) — o backend resolve/cria.
- **Fast path**: item com `notes` nulo + `confidence` alta + todas as entidades
  já existentes no catálogo → publicado diretamente, sem fila de revisão.
- Itens fora do fast path caem em `extracted_items` com `review_status = pendente`.
- `finish_group` no JSON **é obrigatório** para acabamentos novos (senão cai em
  `ACABAMENTO_NAO_CADASTRADO`). Valores válidos: `"madeirado"`, `"metalico"`.
- Acabamentos como Preto e Branco são **multi-grupo** (madeirado + metálico) —
  a modelagem suporta isso desde a migration `0017`.
- Reimportar o mesmo item atualiza o preço via upsert (não duplica).

O pipeline de extração de PDF (`app/imports/extraction.py`) existe no backend
mas **não aparece mais na UI** — é código legado. Não remova, não quebre.

---

## 6. Regras de negócio críticas (não viole)

Ver `docs/05-regras-orcamento.md` para o texto completo de RN-01 a RN-18.
As mais sensíveis:

| Regra | O que é | Onde vive |
|---|---|---|
| **RN-16** | Preço congelado no momento de adição do item ao orçamento | `quotes/service.py` — `frozen_unit_price` em `quote_item_components` |
| **RN-04** | Compatibilidade tampo↔estrutura (dimensão deve ser a mesma) | `catalog/service.py` — `component_compatibility_rules` |
| **RN-14** | Nenhum item de importação vira catálogo sem aprovação (exceto fast path) | `imports/json_ingest.py` |
| **RN-12** | Item sem preço não pode ser adicionado ao orçamento | `quotes/service.py` — `ITEM_SEM_PRECO` |

**Invariante de cálculo** (ordem obrigatória, não altere):
```
frozen_unit_price × markup_factor × qty
  → desconto de item (% XOR R$)
  → desconto do orçamento (% XOR R$)
  → total
  → juros de parcelamento
  → installment_total
```

`markup_factor` vem de `_get_effective_markup_percent()` em `service.py`:
usa `quotes.markup_percent` se `markup_uses_global = false`, caso contrário
lê `app_settings.global_markup_percent`. **Nunca é gravado em `frozen_unit_price`.**

---

## 7. Modelo de dados — tabelas principais

```
product_families → products → product_components
                                    ↓
dimensions + finishes + finish_groups (multi-valor, migration 0017)
                                    ↓
                          component_variants  ←─ extracted_items (origem rastreável)
                                    ↓
                               prices (upsert por variant)
                                    ↓
quote_items → quote_item_components (frozen_unit_price aqui)
    ↓
quote_totals (snapshot congelado — base para export PDF)
```

Tabelas de apoio relevantes:
- `app_settings` — chave `global_markup_percent` (TEXT/REAL)
- `component_compatibility_rules` — compatibilidade tampo↔estrutura
- `product_compositions` — composição recursiva de produtos (ex-`product_kit_items`)
- `imported_files` / `imported_pages` / `extracted_items` — rastreabilidade de importação

Schema completo: `docs/schema/schema.sql`. Migrations numeradas em
`backend/app/db/migrations/` (0001 a 0020 atualmente).

---

## 8. Endpoints principais

Ver `docs/06-arquitetura-api.md` para o contrato completo. Resumo:

| Grupo | Prefixo |
|---|---|
| Saúde | `GET /api/v1/health` |
| Catálogo (CRUD) | `GET/POST/PATCH /api/v1/components`, `/families`, `/finishes`, `/dimensions`, etc. |
| Importação JSON | `POST /api/v1/imports/json` |
| Revisão | `POST /api/v1/extracted-items/{id}/review` |
| Orçamentos | `GET/POST /api/v1/quotes`, `POST .../items`, `PATCH .../settings`, `GET .../export` |
| Configurações | `GET/PATCH /api/v1/settings` (admin) |
| Auth | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` |

Todos os erros seguem o envelope:
```json
{ "error": "NOME_ERRO_SNAKE_UPPER", "detail": "...", "context": {} }
```
Nomes de erro estão em `backend/app/shared/errors.py`. Nunca retorne
erro de banco cru ao cliente.

---

## 9. Deploy (Railway)

- **Backend**: serviço `backend` na Railway, banco SQLite em Volume montado em `/data/`
- **Frontend**: serviço `frontend` na Railway, build Vite estático
- Acesso SSH: `railway ssh -s backend` (chave `id_ed25519_railway`)
- Para uploads de script ao servidor: `scp` via alias `railway-backend`
- Migrations rodam automaticamente no startup — não é necessário rodar manualmente
- `VITE_API_BASE_URL` deve ser a URL pública do backend (variável de ambiente no Railway)

---

## 10. Convenções de código

**Backend (Python/FastAPI)**
- Separação estrita: `router.py` (HTTP) → `service.py` (regras) → `repository.py` (SQL)
- Nenhum SQL em `service.py`; nenhuma regra de negócio em `router.py`
- Erros de domínio: levantar exceção com nome do erro → handler global formata
- Testes de integração: banco em memória, sem mocks, fixture de `app` em `conftest.py`

**Frontend (React/TypeScript)**
- Estado de catálogo (famílias, produtos, acabamentos, etc.) via `CatalogContext` — não busque de novo o que já está no contexto
- Funções de API ficam em `src/api/` com tipos explícitos; não use `fetch` direto nos componentes
- `QuoteSettingsForm` centraliza markup, desconto, parcelamento e entrada — não duplique essa lógica

**Migrações**
- Nunca edite uma migration existente; sempre crie uma nova numerada
- `PRAGMA foreign_keys = ON` é ativado por conexão em `connection.py` — não remova isso

---

## 11. O que NÃO fazer

- **Não moque o banco nos testes** — a equipe foi queimada por divergência mock/prod
- **Não grave markup em `frozen_unit_price`** — markup é runtime, não snapshot
- **Não remova o pipeline de extração de PDF** — é código legado, mas pode ser necessário
- **Não crie migration sem testar idempotência** (rodar duas vezes não pode falhar)
- **Não adicione lógica de parcelamento/desconto/entrada sem respeitar a ordem de cálculo** da seção 6
- **Não use `finish_group` como campo único** — desde a migration 0017 é uma tabela associativa
- **Não publique itens com `notes ≠ None` via fast path** — eles devem ir para revisão

---

## 12. Armadilhas conhecidas

**`publish_item` e colisão de variantes**: itens com a mesma chave
`(family, product, component, dimension, finish)` mas `description_raw`
diferente precisam gerar variantes separadas. O fix está em
`backend/app/catalog/service.py` (commit `3b7e2a0`). Se aparecer sintoma
de "importação resulta em menos itens que o esperado no catálogo", essa
é a causa mais provável.

**`finish_group` vazio no JSON de importação**: se um acabamento não
existe no catálogo e o JSON não traz `finish_group`, o item cai em
`ACABAMENTO_NAO_CADASTRADO`. Os geradores em `importacao/` devem
sempre preencher `finish_group` para acabamentos novos.

**Porta do frontend**: `VITE_API_BASE_URL` deve apontar para `8000`
(backend FastAPI), não `8030` ou qualquer outra porta.

**Orçamentos finalizados**: aprovados/rejeitados/expirados ficam em
`<details>` colapsável no sidebar, não na lista principal.

---

## 13. Status do redesign em andamento

O pacote `entrega-redesign-helence/` é a fonte de verdade visual do redesign
em andamento. O estado real, lacunas e próximas etapas estão em
`docs/11-status-redesign.md`; leia-o antes de alterar frontend, settings ou
PDF. Não trate as novas rotas como redesign concluído: a migração de telas
ainda é parcial.

## 14. Documentos de referência

| Documento | Para que serve |
|---|---|
| `docs/05-regras-orcamento.md` | RN-01 a RN-18 — ler antes de alterar qualquer lógica de orçamento |
| `docs/06-arquitetura-api.md` | Contratos de todos os endpoints (request/response/erros) |
| `docs/10-contrato-importacao-json.md` | Schema do JSON de importação (campos, validações, fast path) |
| `docs/agente-importacao-json/CONTRATO.md` | Versão do contrato para o agente externo gerador de JSON |
| `docs/09-implantacao-operacao.md` | Guia de deploy, backup e operação na Railway |
| `docs/03-modelagem-sqlite.md` | Modelo de dados detalhado (24 tabelas + índices) |
| `docs/README_IMPLEMENTACAO.md` | Visão consolidada de tudo que foi implementado |
| `docs/11-status-redesign.md` | Handoff do redesign: estado real, lacunas e próximas etapas |
