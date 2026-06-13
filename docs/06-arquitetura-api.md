# Arquitetura da aplicação web — Helence Orçamento

> Proposta de arquitetura full-stack para uma **aplicação web interna**
> apoiada em SQLite, cobrindo os três domínios já modelados/desenhados:
> importação de tabelas de preço (`docs/03-…`, `docs/04-…`), catálogo
> normalizado e montagem de orçamentos (`docs/05-…`). Este documento
> propõe **como construir** o que os anteriores definiram **o quê**
> construir — não há código de produção aqui, apenas a arquitetura,
> as convenções e os contratos de API que orientariam a implementação.
>
> **Stack proposta**: Python (FastAPI) no backend — natural, já que os
> spikes de extração (`scripts/spikes/`) também são em Python, então o
> *pipeline* de importação reaproveita bibliotecas e conhecimento — e
> React + TypeScript no frontend, com SQLite como único banco (sem
> serviços externos), adequado ao porte de uma ferramenta interna de
> uso por uma equipe pequena.

---

## 1. Arquitetura em camadas

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + TypeScript)                                    │
│  Telas descritas em docs/04-ux-operacional.md                     │
│  Fala com o backend exclusivamente via API HTTP/JSON (seção 5)    │
└───────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP/JSON (REST)
┌───────────────────────────────▼────────────────────────────────────┐
│  BACKEND — camada de API (routers/controllers)                     │
│  Validação de entrada, autenticação/permissões, tradução           │
│  request↔domínio, formatação de resposta e de erro                 │
├─────────────────────────────────────────────────────────────────────┤
│  BACKEND — camada de serviço/domínio (services)                    │
│  Onde vivem as REGRAS DE NEGÓCIO (docs/05-regras-orcamento.md):    │
│  compatibilidade tampo↔estrutura, congelamento de preço,           │
│  bloqueio de item sem preço/SKU, fluxo de revisão→publicação...    │
│  Não conhece HTTP nem SQL — only orquestra repositórios e regras.  │
├─────────────────────────────────────────────────────────────────────┤
│  BACKEND — camada de acesso a dados (repositories)                 │
│  Único lugar que escreve SQL/usa o driver do SQLite.               │
│  Espelha as 3 camadas do schema (docs/03-modelagem-sqlite.md):     │
│  importação · catálogo normalizado · orçamentos                    │
├─────────────────────────────────────────────────────────────────────┤
│  BACKEND — infraestrutura transversal                              │
│  logging, tratamento de erro, migrations, storage de arquivos,     │
│  autenticação/sessão, configuração                                 │
└───────────────────────────────┬────────────────────────────────────┘
                                 │
                         ┌───────▼────────┐    ┌────────────────────┐
                         │  SQLite (.db)  │    │  Storage de PDFs   │
                         │  schema.sql    │    │  (sistema de       │
                         │  (docs/03-…)   │    │  arquivos local)   │
                         └────────────────┘    └────────────────────┘
```

**Por que esta separação importa especificamente aqui**: as regras de
negócio documentadas em `docs/05-…` (compatibilidade, congelamento,
bloqueios) são o ativo mais valioso e mais sujeito a mudança deste
sistema — concentrá-las numa camada de serviço isolada de HTTP e de SQL
significa que (a) podem ser testadas sem subir um servidor ou tocar o
banco, e (b) sobrevivem intactas a uma eventual troca de framework web
ou de banco de dados (seção 11).

---

## 2. Estrutura de pastas

```
helence-orcamento/
├── backend/
│   ├── app/
│   │   ├── main.py                 # cria a app FastAPI, registra routers e middlewares
│   │   ├── config.py               # leitura de variáveis de ambiente / settings
│   │   ├── db/
│   │   │   ├── connection.py       # abre conexão SQLite, ativa PRAGMA foreign_keys=ON
│   │   │   └── migrations/         # ver seção 10 — scripts numerados e versionados
│   │   │         0001_initial.sql
│   │   │         0002_quote_totals_snapshot.sql
│   │   ├── shared/
│   │   │   ├── errors.py           # exceções de domínio + envelope padrão (seção 9)
│   │   │   ├── logging.py          # configuração de logs estruturados (seção 8)
│   │   │   ├── pagination.py       # helpers de paginação reutilizados pelos routers
│   │   │   └── auth.py             # sessão/usuário autenticado (seção 13)
│   │   ├── files/
│   │   │   └── storage.py          # abstração de armazenamento de PDFs (seção 6)
│   │   ├── imports/                # MÓDULO: importação de tabelas de preço
│   │   │   ├── router.py           #   endpoints HTTP (upload, listagem, status, itens, revisão)
│   │   │   ├── service.py          #   orquestra extração + regras de revisão/publicação
│   │   │   ├── extraction.py       #   adapta a estratégia validada no spike (docs/02-…)
│   │   │   ├── repository.py       #   consultas/escritas em imported_files/pages/items/...
│   │   │   └── schemas.py          #   modelos de request/response (Pydantic)
│   │   ├── catalog/                # MÓDULO: catálogo normalizado
│   │   │   ├── router.py           #   busca, CRUD manual de componentes, publicação
│   │   │   ├── service.py          #   regras de compatibilidade e publicação (RN-03..06,14)
│   │   │   ├── repository.py       #   consultas/escritas em products/component_variants/prices/...
│   │   │   └── schemas.py
│   │   ├── quotes/                 # MÓDULO: orçamentos
│   │   │   ├── router.py           #   criação, composição, edição, totais, exportação
│   │   │   ├── service.py          #   regras de composição/congelamento/bloqueio (docs/05-…)
│   │   │   ├── pricing.py          #   cálculo de subtotal/desconto/total (puro, testável)
│   │   │   ├── export.py           #   geração do documento de orçamento (PDF/planilha)
│   │   │   ├── repository.py       #   consultas/escritas em quotes/quote_items/...
│   │   │   └── schemas.py
│   │   └── auth/
│   │       ├── router.py           #   login/logout/sessão (seção 13)
│   │       └── service.py
│   ├── tests/
│   │   ├── unit/                   #   regras de negócio isoladas (sem HTTP/banco)
│   │   └── integration/            #   fluxos completos contra um SQLite de teste
│   ├── data/
│   │   ├── helence.db              #   arquivo do banco (fora do controle de versão)
│   │   └── uploads/                #   PDFs originais armazenados (seção 6)
│   ├── pyproject.toml
│   └── alembic.ini                 #   (opcional — ver discussão na seção 10)
│
├── frontend/
│   ├── src/
│   │   ├── app/                    #   roteamento, layout raiz, providers globais
│   │   ├── pages/                  #   uma pasta por tela de docs/04-ux-operacional.md
│   │   │   ├── imports/            #     telas 1-5 (upload, processamento, revisão, correção, aprovação)
│   │   │   ├── catalog/            #     tela 6 (consulta do catálogo)
│   │   │   ├── quotes/             #     telas 7-9 (montagem, edição, exportação)
│   │   │   └── audit/              #     tela 10 (auditoria de origem de preço)
│   │   ├── features/               #   lógica de domínio no cliente (hooks + estado por módulo)
│   │   │   ├── imports/
│   │   │   ├── catalog/
│   │   │   └── quotes/
│   │   ├── components/             #   componentes de UI compartilhados (tabela, modal, alerta...)
│   │   ├── api/                    #   cliente HTTP + tipos de request/response (espelham schemas.py)
│   │   └── hooks/                  #   hooks transversais (sessão, paginação, notificações)
│   └── package.json
│
├── docs/                           #   este e os documentos anteriores (01-06)
└── scripts/spikes/                 #   spikes exploratórios (docs/02-…) — não fazem parte da app
```

**Convenção-chave**: cada módulo de backend (`imports`, `catalog`,
`quotes`) replica o mesmo padrão interno — `router → service →
repository` — e o frontend espelha essa divisão em `pages`/`features`
por módulo. Isso facilita a navegação ("a regra de compatibilidade
tampo↔estrutura está em `quotes/service.py`; a tela que a aciona está
em `pages/quotes/`") sem depender de busca textual.

---

## 3. Módulos do backend

| Módulo | Responsabilidade | Pontos de regra de negócio que concentra |
|---|---|---|
| `imports` | Recebe PDFs, dispara a extração (estratégia validada em `docs/02-…`), expõe o progresso e os itens extraídos para revisão humana | RN-14 indiretamente — é aqui que um item nasce com `review_status='pendente'` e só avança por decisão humana registrada em `import_review_decisions` |
| `catalog` | Mantém o catálogo normalizado (famílias, produtos, variações, acabamentos, SKUs, preços) e processa a **publicação** de uma versão de tabela revisada | A publicação é o "portão" da RN-14: só promove para `component_variants`/`prices` itens com `review_status='aprovado'`; também hospeda o CRUD manual usado para preencher lacunas pontuais (ex. casos de "código sem preço") |
| `quotes` | Orquestra a montagem, edição, cálculo e exportação de orçamentos | Concentra praticamente todas as regras de `docs/05-…`: compatibilidade (RN-03/04/05), obrigatoriedade (RN-07), bloqueios (RN-12/13), congelamento (RN-16), versão vigente (RN-15), revisão final (RN-18) |
| `auth` | Login, sessão, papel do usuário | Define quem pode importar/revisar/aprovar/vender/auditar (tabela de papéis de `docs/04-…`, seção 0) |
| `shared` | Erros, logging, paginação, abstrações transversais | Garante que **todo** módulo retorna erros e logs no mesmo formato (seções 8/9) — sem isso, cada módulo inventaria o seu |
| `files` | Abstrai onde/como os PDFs originais são armazenados | Isola o restante do sistema da decisão "disco local hoje, *object storage* amanhã" (seção 6) |

A regra de ouro de divisão: **um módulo nunca chama o `repository` de
outro módulo diretamente** — se `quotes` precisa saber o preço vigente
de uma variação, chama `catalog.service`, não `catalog.repository`. Isso
mantém cada camada de regras de negócio coesa e testável de forma
isolada.

---

## 4. Módulos do frontend

| Módulo (`features/<nome>`) | Telas que alimenta (de `docs/04-…`) | Estado/lógica de cliente que concentra |
|---|---|---|
| `imports` | 1. Upload · 2. Processamento · 3. Revisão · 4. Correção · 5. Aprovação | Acompanhamento de progresso (polling — seção 5), agrupamento para correção em lote, navegação página-a-página com o trecho original em destaque |
| `catalog` | 6. Consulta do catálogo · 10. Auditoria de origem | Filtros de busca (família/produto/componente/dimensão/acabamento), trilha de rastreabilidade até o item extraído de origem |
| `quotes` | 7. Montagem · 8. Edição de item · 9. Exportação | Composição incremental do item (seleção em cascata: família → produto → dimensão → componente → acabamento, sempre restrita ao que o catálogo realmente tem — RN-03/05), exibição de avisos de bloqueio (item sem preço/SKU) e de versão mista de tabela (RN-15) |

**Componentes de UI compartilhados** (`components/`) que valem a pena
existir desde o início, por aparecerem em várias telas de `docs/04-…`:
tabela com paginação/filtros, modal de confirmação com prévia (usado
tanto na correção em lote quanto na publicação e na duplicação de
orçamento), indicador de nível de confiança (`alta`/`média`/`baixa`),
e "cartão de rastreabilidade" (arquivo → página → linha → item — reusado
nas telas 3, 6 e 10).

O cliente HTTP (`api/`) deve expor **um módulo por recurso de backend**
(`api/imports.ts`, `api/catalog.ts`, `api/quotes.ts`), com tipos
TypeScript que espelham — idealmente são **gerados a partir de** —
os `schemas.py` do backend (ver seção 5), evitando que os dois lados
divirjam silenciosamente.

---

## 5. Estratégia de comunicação frontend/backend

**REST sobre HTTP/JSON**, com o backend como única fonte de verdade
sobre o estado — sem lógica de negócio duplicada no cliente.

- **Formato**: JSON em todas as trocas, exceto upload de arquivo
  (`multipart/form-data` — seção 6) e download de exportação (binário,
  com `Content-Disposition`).
- **Convenções de URL**: recursos no plural, aninhamento reflete posse
  (`/api/quotes/{id}/items/{itemId}/components/{componentId}`),
  *query strings* para filtro/paginação/busca.
- **Versionamento**: prefixo `/api/v1/...` desde o início — mesmo MVP
  trocando endpoints com frequência, um prefixo de versão custa nada
  hoje e evita uma migração dolorosa amanhã, quando o frontend não for
  mais o único cliente.
- **Tipos compartilhados**: os `schemas.py` (Pydantic) do backend são a
  fonte; o frontend gera seus tipos TypeScript a partir do schema
  OpenAPI que o FastAPI já expõe automaticamente (`/api/v1/openapi.json`)
  — elimina uma classe inteira de bugs de "campo renomeado de um lado
  só".
- **Atualização de progresso de longa duração** (processamento de PDF —
  seção 7): MVP usa **polling simples** (`GET .../status` a cada poucos
  segundos enquanto `status='processando'`) — é a opção mais simples de
  implementar, depurar e operar numa aplicação interna de baixo volume
  simultâneo; *web sockets*/SSE ficam como evolução futura caso o
  polling se mostre custoso na prática (não há indício disso no
  tamanho de catálogo observado na auditoria).
- **Autenticação**: cookie de sessão (seção 13) enviado automaticamente
  pelo navegador — não exige o frontend gerenciar tokens manualmente.

---

## 6. Estratégia de upload de arquivos

O upload de PDF (`POST /api/v1/imports`) é o único ponto de entrada de
arquivo binário no sistema. Decisões:

1. **Transporte**: `multipart/form-data`, com limite de tamanho
   configurável (ex. 50 MB — folgado frente aos PDFs de tabela de
   preço observados na auditoria) validado **antes** de o corpo ser
   integralmente lido, para não desperdiçar memória/IO com arquivos
   claramente fora do esperado.
2. **Validação de conteúdo**: confirma que o arquivo é de fato um PDF
   válido (assinatura/MIME + tentativa de abertura com a biblioteca de
   extração) — rejeita cedo, com mensagem clara, em vez de deixar o
   problema aparecer só na hora de processar.
3. **Deduplicação por hash**: calcula `sha256` do conteúdo
   (`imported_files.file_hash`) e, se já existir um arquivo idêntico
   importado, **não** cria um novo registro — responde apontando para
   a importação existente. Evita reprocessar (e poluir o catálogo com)
   o mesmo arquivo enviado duas vezes por engano.
4. **Armazenamento**: arquivos ficam no sistema de arquivos local,
   fora do diretório do banco (`backend/data/uploads/`), nomeados pelo
   próprio hash (`<sha256>.pdf`) — nome estável, sem depender do nome
   original (que pode repetir ou conter caracteres problemáticos). O
   caminho final é gravado em `imported_files.file_path`.
5. **Abstração de armazenamento** (`files/storage.py`): todo acesso a
   arquivo passa por uma interface mínima (`save`, `read`,
   `path_for`) — para uma aplicação interna de pequeno porte, "disco
   local" é a opção certa hoje; a interface existe apenas para que
   trocar por *object storage* no futuro (se o volume crescer ou se
   for necessário acesso de múltiplas instâncias) seja uma troca de
   implementação, não uma reescrita espalhada pelo código.
6. **Retenção**: o PDF original **nunca é descartado** após o
   processamento — ele é a base de toda a cadeia de rastreabilidade até
   "página X, linha Y" (telas 3 e 10 de `docs/04-…`; consulta "auditar
   origem de preço" de `docs/03-…`). Removê-lo quebraria a garantia
   central do produto.

---

## 7. Estratégia de processamento — síncrono ou assíncrono (MVP)

**Proposta para o MVP: processamento assíncrono *em processo*** — ou
seja, sem fila/worker externos (Celery, RQ, etc.), mas também sem
bloquear a requisição HTTP de upload:

- `POST /api/v1/imports/{id}/process` **dispara** o processamento (via
  *background task* nativa do framework web) e responde imediatamente
  `202 Accepted` com `status='processando'`.
- O frontend acompanha o progresso por **polling** em
  `GET /api/v1/imports/{id}/status` (seção 5), que reflete o avanço
  página a página gravado incrementalmente em `imported_pages`/
  `extracted_items`.
- Ao final, o status muda para `concluido` (ou `erro`, com detalhe).

**Por que não síncrono**: a auditoria encontrou arquivos de centenas de
páginas — uma extração completa pode levar de dezenas de segundos a
poucos minutos; segurar a conexão HTTP aberta todo esse tempo é frágil
(timeouts de proxy/navegador) e impede o usuário de fazer qualquer
outra coisa enquanto espera.

**Por que não uma fila externa (ainda)**: introduzir
Celery/Redis/RabbitMQ adiciona peças móveis — processos extras para
operar, monitorar e versionar — que não se justificam para uma
aplicação **interna**, de **uso esporádico** (importações acontecem
quando uma nova tabela de preço sai, não continuamente) e de
**concorrência baixa** (não há cenário plausível de dezenas de
importações simultâneas). *Background tasks* em processo resolvem o
problema real (não travar a UI) com a menor complexidade operacional
possível.

**Quando reconsiderar**: se no futuro existirem múltiplas instâncias do
backend (exigindo que o estado do processamento seja compartilhado) ou
o volume de importações crescer a ponto de competir por recursos com o
tráfego normal da aplicação, migrar para uma fila externa é uma
extensão localizada — o contrato HTTP (`process` → `status`) não
precisa mudar, só a implementação por trás dele.

---

## 8. Estratégia de logs

Logs estruturados (JSON, um evento por linha) com **três focos**,
porque uma aplicação cujo valor central é rastreabilidade (RN-16,
tela 10) precisa também ser rastreável *sobre si mesma*:

1. **Logs de requisição** (automáticos, via *middleware*): método, rota,
   status, duração, usuário autenticado, *id* de correlação por
   requisição (`request_id`) — permitem reconstruir "o que aconteceu
   quando o usuário X clicou em Y".
2. **Logs de domínio** (emitidos explicitamente pelos `services`, nos
   pontos que já são, por natureza, decisões registradas): início/fim
   de processamento de importação, decisão de revisão
   (aprovar/rejeitar/corrigir — *espelhando* o que já vai para
   `import_review_decisions`, mas no canal operacional), publicação de
   tabela, criação/transição de status de orçamento, bloqueios de
   regra de negócio acionados (ex. tentativa de adicionar item sem
   preço — mesmo bloqueada, vale registrar que **alguém tentou**, pois
   isso é um sinal de lacuna no catálogo que a área de catálogo
   deveria ver).
3. **Logs de erro** (seção 9): toda exceção não tratada é logada com
   `request_id`, *stack trace* e contexto suficiente para reproduzir —
   nunca apenas "ocorreu um erro".

**Nível e destino**: `INFO` para os três acima, `WARNING` para
condições anômalas mas recuperáveis (ex. PDF com página ilegível),
`ERROR` para falhas que impedem completar uma operação. Em
desenvolvimento e em produção, saída para **stdout/stderr** (console)
— em produção (Railway, `docs/09` seção 11), o *log stream* da
plataforma captura essa saída automaticamente, sem necessidade de
arquivo rotacionado local. Suficiente para o porte da aplicação, sem
exigir um sistema de observabilidade externo desde o primeiro dia (se a
operação crescer, o formato estruturado já facilita plugar um *log
drain*/coletor externo depois, sem reescrever os pontos de log —
`docs/09` seção 14.1).

**O que nunca vai para o log**: senhas, conteúdo de sessão/cookies, e
dados pessoais de cliente além do estritamente necessário para
correlacionar (ex. logar `customer_id`, não `customer.document`).

---

## 9. Estratégia de tratamento de erros

**Princípio**: todo erro de negócio é uma **exceção de domínio
nomeada** (definida em `shared/errors.py`, ex. `ItemSemPrecoError`,
`StatusInvalidoError`, `VariacaoDuplicadaError`) — nunca um `ValueError`
genérico ou um `if`/`return None` silencioso. Isso obriga cada situação
de erro a ser **decidida e nomeada** no momento em que a regra é escrita
(coerente com o espírito de `docs/05-…`: "nunca uma mensagem genérica
de 'corrija os erros'").

**Envelope de resposta padrão** (um *middleware* converte qualquer
exceção de domínio neste formato — o mesmo em todos os módulos):

```json
{
  "error": {
    "code": "ITEM_SEM_PRECO",
    "message": "Este componente não possui preço cadastrado na tabela de preço vigente (01-2025).",
    "details": {
      "component_variant_id": 1182,
      "price_table_id": 6,
      "suggestion": "Selecione outra variação ou contate o time de catálogo."
    }
  }
}
```

- `code`: estável, em `MAIUSCULO_COM_UNDERSCORE` — o frontend usa este
  campo (não `message`) para decidir como reagir (ex. exibir um botão
  de ação específico); `message` é só para exibição.
- `details`: estruturado, específico do erro — permite ao frontend
  apontar exatamente o componente/linha problemático (RN-12/13/18
  exigem mensagens "nomeadas e acionáveis", não agregadas).
- Toda resposta de erro carrega o `request_id` no cabeçalho HTTP,
  amarrando-a ao log correspondente (seção 8) — essencial para
  diagnosticar problemas relatados pelo usuário depois do fato.

**Mapeamento para HTTP**: exceções de domínio carregam seu próprio
status HTTP (`404` para "não encontrado", `409` para "conflito de
estado" — ex. tentar revisar um item já decidido, `422` para "violação
de regra de negócio sobre uma entrada sintaticamente válida" — ex.
`ITEM_SEM_PRECO`, `400` para erro de formato/parâmetro). Erros não
previstos (bugs) sempre retornam `500`, são logados com prioridade
máxima e **nunca** vazam detalhes internos (stack trace, SQL) na
resposta ao cliente — só no log correlacionado por `request_id`.

---

## 10. Estratégia de migrations

**Scripts numerados e versionados**, aplicados em ordem e registrados
em uma tabela de controle própria (`schema_migrations(version,
applied_at)`) — o padrão mais simples que garante que (a) todo ambiente
(desenvolvimento, do colega, futuro "produção" interna) chega ao mesmo
estado de schema executando os mesmos passos, e (b) nunca se aplica a
mesma migration duas vezes:

```
backend/app/db/migrations/
  0001_initial.sql                    -- cria as 24 tabelas + índices de schema.sql
  0002_quote_export_jobs.sql          -- ex. evolução futura
  ...
```

- `0001_initial.sql` **é**, essencialmemte, o `docs/schema/schema.sql`
  já validado — a primeira migration consolida o que já foi desenhado,
  não recomeça do zero.
- Cada migration subsequente é **aditiva e incremental** (nova tabela,
  nova coluna, novo índice) — alterações destrutivas (remover/renomear
  coluna) em SQLite exigem recriar a tabela (`CREATE TABLE ... AS
  SELECT` + troca de nome), e a migration documenta esse procedimento
  passo a passo, já que o SQLite não suporta `ALTER TABLE ... DROP
  COLUMN`/`RENAME COLUMN` em todas as versões da mesma forma que outros
  bancos.
- **Execução**: na inicialização do backend (`main.py`), antes de
  aceitar requisições — aplica migrations pendentes e recusa subir se
  alguma falhar. Evita o cenário "aplicação no ar com schema
  desatualizado".

**Ferramenta**: um executor minimalista (lê os arquivos `.sql` em
ordem, compara com `schema_migrations`, aplica os que faltam dentro de
uma transação) é suficiente e mantém zero dependências externas — mas
adotar o **Alembic** (parte do ecossistema SQLAlchemy) é uma alternativa
igualmente razoável caso o time já tenha familiaridade com ele e
valorize *tooling* pronto (geração de migration a partir de diffs de
modelo, *downgrade* automático). Qualquer uma das duas opções satisfaz
o requisito — a recomendação é começar pela mais simples (script
próprio) e só adotar Alembic se a complexidade das migrations crescer
a ponto de justificar a dependência adicional.

---

## 11. Estratégia para futura migração de SQLite para PostgreSQL

O desenho já antecipa essa possibilidade — vale destacar **onde** ela
foi deliberadamente facilitada e **o que** precisaria mudar:

**O que já ajuda (decisões tomadas em `docs/03-…`)**:
- `PRAGMA foreign_keys = ON` + *constraints* explícitas (`CHECK`,
  `UNIQUE`, `REFERENCES`) — o schema já se comporta como um banco
  relacional "de verdade", não como um SQLite "solto"; a tradução para
  DDL do PostgreSQL é, em grande parte, mecânica.
- Datas em texto ISO-8601 e valores monetários em `NUMERIC` — ambos
  têm equivalentes diretos em PostgreSQL (`timestamptz`/`date` e
  `numeric`), sem ambiguidade de conversão.
- Toda regra de negócio mora na camada de serviço (seção 1), não em
  *triggers*/*views* específicas do SQLite — então a troca de banco não
  arrasta lógica de negócio junto.

**O que precisaria de atenção na migração**:
1. **Tipos específicos do SQLite**: `INTEGER PRIMARY KEY AUTOINCREMENT`
   → `BIGSERIAL`/`GENERATED ALWAYS AS IDENTITY`; `INTEGER` 0/1 com
   `CHECK` para booleano → `BOOLEAN` nativo; `datetime('now')` →
   `now()`/`CURRENT_TIMESTAMP`. São trocas mecânicas, mas exigem
   reescrever o arquivo de schema/migrations para o dialeto do
   PostgreSQL (não um simples *find-and-replace* — os defaults e
   *constraints* têm sintaxe própria).
2. **Camada de acesso a dados**: se os `repositories` usarem SQL puro
   (driver `sqlite3`), a migração exige reescrever as *queries*
   específicas de dialeto (ex. funções de data, `LIKE` vs. `ILIKE`,
   `LIMIT`/`OFFSET` — na maioria igual, mas vale auditar). Usar um
   *toolkit* de acesso a dados com suporte a múltiplos dialetos (ex.
   SQLAlchemy Core) desde o início **reduziria** esse atrito — é uma
   troca consciente de complexidade inicial por portabilidade futura,
   que vale a pena avaliar com o time antes de começar a implementação.
3. **Concorrência**: o SQLite serializa escritas (um *writer* por vez);
   o PostgreSQL não. Para uma aplicação interna de baixa concorrência
   isso nunca aparece como problema — mas é exatamente o tipo de
   suposição implícita que vale documentar agora, para que ninguém, no
   futuro, fique surpreso ao notar que o comportamento sob carga mudou
   (para melhor) após a migração.
4. **Arquivo único → serviço**: SQLite é um arquivo; PostgreSQL é um
   processo de servidor. A migração troca "copiar um arquivo" (seção
   12) por "configurar conexão, usuário, *backup* gerenciado pelo
   servidor" — um salto operacional real, não apenas técnico, que deve
   ser avaliado **junto** com a necessidade que motivaria a migração
   (ex. múltiplas instâncias, volume de dados, acesso concorrente
   pesado) — não antecipado sem necessidade concreta.

**Recomendação**: não migrar preventivamente. SQLite atende
integralmente ao perfil descrito (aplicação interna, volume modesto,
poucos usuários simultâneos). As decisões acima garantem que, **se e
quando** a necessidade aparecer, a migração será um projeto de
tradução e ajuste — não uma reescrita.

---

## 12. Estratégia de backup

Com SQLite, *backup* é, felizmente, um problema simples — desde que
feito corretamente (cópia "a frio" de um arquivo em uso pode corromper
o backup):

1. **Mecanismo**: usar o comando de *backup* nativo do SQLite (a API
   *Online Backup*, exposta por praticamente todo driver — em Python,
   `sqlite3.Connection.backup()`) — copia o banco de forma consistente
   mesmo com a aplicação rodando, sem travar escritas por mais que o
   tempo da cópia.
2. **Frequência**: backup diário automático (ex. *job* agendado fora do
   horário de uso) + backup manual sob demanda antes de operações
   sensíveis (ex. antes de publicar uma nova versão de tabela de
   preço — a operação que mais altera dados de catálogo de uma só vez).
3. **O que é copiado**: o arquivo do banco (`helence.db`) **e** o
   diretório de uploads (`data/uploads/`) — copiar só o banco sem os
   PDFs originais quebraria a cadeia de rastreabilidade em uma
   restauração (o banco referenciaria arquivos que não existem mais).
4. **Retenção**: manter um histórico curto de versões (ex. últimos 14
   dias + um snapshot mensal) — o suficiente para recuperar de erros
   humanos ("importei o arquivo errado", "publiquei a tabela errada")
   sem acumular indefinidamente.
5. **Local de armazenamento**: fora da máquina onde a aplicação roda
   (ex. outro disco, ou um destino de rede/armazenamento gerenciado) —
   um backup que mora no mesmo disco que o original não protege contra
   a falha mais comum (perda do disco).
6. **Verificação periódica**: testar a restauração de um backup de
   tempos em tempos — um backup nunca testado é, na prática, uma
   suposição não verificada (o mesmo princípio de "não confie sem
   checar" que orienta `docs/05-…` para os dados do catálogo se aplica,
   aqui, à infraestrutura).

---

## 13. Estratégia de autenticação simples

O sistema **precisa** de autenticação — não pelo volume de dados, mas
porque várias regras de negócio e telas dependem de **saber quem está
agindo** (RN-09 exige justificativa de desconto atribuível a alguém;
`import_review_decisions.reviewed_by_user_id` e
`quotes.created_by_user_id` só fazem sentido com um usuário
identificado; e a tabela de papéis de `docs/04-…` — Importador, Revisor,
Aprovador/Admin, Vendedor, Auditor — define o que cada um pode fazer).

**Proposta — autenticação simples baseada em sessão**:
1. **Login** (`POST /api/v1/auth/login`): usuário/senha (ou e-mail/
   senha) contra a tabela `users`; senha armazenada com *hash*
   adequado (ex. `bcrypt`/`argon2` — nunca texto puro nem *hash* fraco
   como MD5/SHA1 simples).
2. **Sessão**: cookie HTTP-only, assinado, com expiração — o backend
   resolve o usuário autenticado a partir do cookie em cada requisição
   (sem o frontend precisar gerenciar token nenhum). Adequado a uma
   aplicação interna acessada por navegador, dentro de uma rede
   confiável.
3. **Autorização por papel**: o campo `users.role`
   (`admin`/`importador`/`revisor`/`vendedor`/`colaborador`) é
   verificado em cada endpoint sensível — ex. só `importador`/`admin`
   pode disparar processamento; só `revisor`/`admin` pode decidir sobre
   um item extraído; só `admin` (ou um papel equivalente a
   "Aprovador", conforme a tabela de papéis de `docs/04-…`) pode
   publicar uma tabela no catálogo. Essa checagem mora num único lugar
   (`shared/auth.py`, como *dependency*/decorator reutilizável) — não
   espalhada e reimplementada em cada `router`.
4. **Por que não OAuth/SSO/JWT desde já**: são mecanismos pensados para
   múltiplos sistemas/serviços ou acesso de fora da rede confiável —
   complexidade que esta aplicação **interna e de uso por uma equipe
   pequena** não demanda no MVP. Sessão por cookie é mais simples de
   implementar, depurar e operar, e cobre o requisito real ("saber quem
   fez o quê, e restringir o que cada papel pode fazer"). Se no futuro
   o sistema precisar se integrar a um provedor de identidade
   corporativo (SSO), essa é uma extensão localizada na camada `auth` —
   o resto da aplicação já depende apenas de "existe um usuário
   autenticado com um papel", não de *como* ele se autenticou.

---

## 14. Contratos REST

> Convenções comuns a todos os endpoints abaixo:
> - Toda resposta de erro segue o envelope da seção 9
>   (`{"error": {"code", "message", "details"}}`).
> - Endpoints de listagem aceitam `page`/`page_size` e respondem
>   `{"items": [...], "page", "page_size", "total"}`.
> - Datas em ISO-8601; valores monetários como número decimal +
>   `currency` separado (nunca string formatada).
> - `{id}` sempre se refere à chave primária numérica da entidade.

### 14.1 — Upload de PDF
**`POST /api/v1/imports`**

Recebe um arquivo PDF e cria o registro de importação (não processa
ainda — ver 14.3).

*Request* — `multipart/form-data`:
| campo | tipo | obrigatório | descrição |
|---|---|---|---|
| `file` | arquivo (PDF) | sim | o documento a importar |
| `notes` | string | não | observação livre sobre esta importação |

*Response* `201 Created`:
```json
{
  "id": 17,
  "original_filename": "tabela-precos-01-2025.pdf",
  "file_hash": "9f1c3a...e02b",
  "page_count": null,
  "status": "recebido",
  "imported_at": "2026-06-08T14:32:00",
  "imported_by": { "id": 3, "name": "Marina Souza" }
}
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ARQUIVO_INVALIDO` | 400 | conteúdo não é um PDF válido/legível |
| `ARQUIVO_MUITO_GRANDE` | 413 | excede o limite configurado |
| `ARQUIVO_DUPLICADO` | 409 | já existe importação com o mesmo `file_hash` (`details.existing_import_id` aponta para ela) |
| `CAMPO_OBRIGATORIO_AUSENTE` | 422 | corpo sem o campo `file` |

---

### 14.2 — Listagem de importações
**`GET /api/v1/imports?status=&page=&page_size=`**

*Query*: `status` (opcional — filtra por
`recebido`/`processando`/`concluido`/`erro`), `page`, `page_size`.

*Response* `200 OK`:
```json
{
  "items": [
    {
      "id": 17,
      "original_filename": "tabela-precos-01-2025.pdf",
      "status": "concluido",
      "page_count": 480,
      "imported_at": "2026-06-08T14:32:00",
      "items_extracted": 1532,
      "items_pending_review": 24,
      "linked_price_table": { "id": 6, "code": "01-2025", "status": "vigente" }
    }
  ],
  "page": 1, "page_size": 20, "total": 8
}
```

*Erros*: `PARAMETRO_INVALIDO` (`400`) — ex. `status` fora do conjunto
permitido.

---

### 14.3 — Processamento de importação
**`POST /api/v1/imports/{id}/process`**

Dispara a extração em segundo plano (seção 7).

*Request*:
```json
{ "strategy": "pymupdf" }
```
(`strategy` é opcional — usa o padrão configurado, conforme avaliação
do spike em `docs/02-…`, quando omitido)

*Response* `202 Accepted`:
```json
{ "id": 17, "status": "processando", "started_at": "2026-06-08T14:35:10" }
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `IMPORTACAO_NAO_ENCONTRADA` | 404 | `{id}` não existe |
| `STATUS_INVALIDO` | 409 | já está `processando`, ou já `concluido` (reprocessar exige uma ação explícita e diferente — não um novo POST silencioso) |
| `ESTRATEGIA_INDISPONIVEL` | 422 | `strategy` informada não é suportada |

---

### 14.4 — Consulta de status
**`GET /api/v1/imports/{id}/status`**

*Response* `200 OK`:
```json
{
  "id": 17,
  "status": "processando",
  "progress": { "pages_total": 480, "pages_processed": 210 },
  "started_at": "2026-06-08T14:35:10",
  "finished_at": null,
  "summary": { "items_extracted": 612, "warnings": 9 },
  "error": null
}
```
Quando `status = "erro"`, o campo `error` traz
`{"code", "message"}` explicando a falha (ex. página corrompida).

*Erros*: `IMPORTACAO_NAO_ENCONTRADA` (`404`).

---

### 14.5 — Consulta de itens extraídos
**`GET /api/v1/imports/{id}/items?review_status=&confidence_level=&page_number=&search=&page=`**

*Query*: todos os filtros são opcionais e combináveis — `review_status`
(`pendente`/`revisado`/`aprovado`/`rejeitado`/`corrigido`),
`confidence_level` (`alta`/`media`/`baixa`), `page_number` (filtra por
página de origem), `search` (busca textual em descrição/SKU/preço bruto).

*Response* `200 OK`:
```json
{
  "items": [
    {
      "id": 4821,
      "imported_page_id": 203,
      "page_number": 432,
      "family_raw": "Mesas Redondas",
      "component_type_raw": "Pé Disco",
      "dimension_raw": "1100MM",
      "finish_raw": "Argila",
      "sku_raw": "398101456",
      "price_raw": null,
      "confidence_level": "baixa",
      "review_status": "pendente",
      "source_text": "Reunião Redonda 1100MM — Pé Disco — Argila — 398101456"
    }
  ],
  "page": 1, "page_size": 50, "total": 1532
}
```

*Erros*: `IMPORTACAO_NAO_ENCONTRADA` (`404`), `PARAMETRO_INVALIDO` (`400`).

---

### 14.6 — Aprovação / rejeição / correção de item extraído
**`POST /api/v1/extracted-items/{id}/review`**

Um único endpoint, com o corpo determinando a decisão — espelha
exatamente o que `import_review_decisions.decision` registra, e gera
**um** registro de decisão por chamada (trilha de auditoria íntegra).

*Request* — três formatos possíveis, conforme `decision`:
```json
// aprovar
{ "decision": "aprovado", "notes": "Conferido contra o PDF, página 432." }

// rejeitar (motivo é obrigatório)
{ "decision": "rejeitado", "notes": "Linha duplicada — já existe item idêntico aprovado (id 4790)." }

// corrigir (campo + valores obrigatórios)
{
  "decision": "corrigido",
  "field": "price_raw",
  "previous_value": null,
  "corrected_value": "412.90",
  "notes": "Valor confirmado na página seguinte da mesma seção."
}
```

*Response* `200 OK`:
```json
{
  "id": 4821,
  "review_status": "corrigido",
  "decision": {
    "id": 991,
    "decision": "corrigido",
    "field_corrected": "price_raw",
    "previous_value": null,
    "corrected_value": "412.90",
    "reviewed_by": { "id": 5, "name": "Carlos Lima" },
    "reviewed_at": "2026-06-08T15:02:44"
  }
}
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ITEM_NAO_ENCONTRADO` | 404 | `{id}` não existe |
| `STATUS_INVALIDO` | 409 | item já tem decisão final (`aprovado`/`rejeitado`) — reabrir exige uma ação explícita e distinta, não uma nova revisão silenciosa |
| `CAMPO_OBRIGATORIO_AUSENTE` | 422 | rejeição sem `notes`, ou correção sem `field`/`corrected_value` |
| `CAMPO_NAO_CORRIGIVEL` | 422 | `field` informado não é um campo elegível para correção (ex. tentar "corrigir" `id`) |
| `VALOR_INCOMPATIVEL` | 422 | `corrected_value` não pode ser convertido para o tipo esperado do `field` (ex. preço não-numérico) |

---

### 14.7 — Publicação dos dados aprovados no catálogo
**`POST /api/v1/price-tables/{id}/publish`**

Promove os `extracted_items` aprovados de uma versão de tabela para o
catálogo normalizado (`component_variants`/`skus`/`prices`) e marca a
versão como `vigente` (arquivando a anterior — RN-15).

*Request*:
```json
{ "confirm": true }
```

*Response* `200 OK`:
```json
{
  "price_table_id": 6,
  "code": "02-2025",
  "status": "vigente",
  "items_published": 1508,
  "previous_vigente": { "id": 5, "code": "01-2025", "new_status": "substituida" }
}
```

> Implementado de forma síncrona (transação única) — o volume real (até
> a ordem de milhares de itens por tabela) não justificou a infra de
> processamento assíncrono prevista originalmente (`202 Accepted` +
> `status: "publicando"`). Se o volume crescer a ponto de tornar a
> publicação lenta, reavaliar.

Para cada `extracted_item` aprovado, família/produto/tipo de
componente/dimensão são resolvidos por nome — criando o registro no
catálogo se ainda não existir. **Acabamentos não seguem essa regra**:
se `finish_raw` não corresponder a um `finishes.name` já cadastrado, a
publicação é bloqueada com `ACABAMENTO_NAO_CADASTRADO` — cadastre o
acabamento em `/catalog/finishes` antes de publicar (preserva o
vocabulário fechado de acabamentos da Fase 6).

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `TABELA_NAO_ENCONTRADA` | 404 | `{id}` não existe |
| `ITENS_PENDENTES_DE_REVISAO` | 409 | existem itens com `review_status` diferente de uma decisão final — bloqueia a publicação (`details.pending_count`, `details.review_url`) |
| `STATUS_INVALIDO` | 409 | tabela já está `vigente`/`substituida` — publicar de novo exige um fluxo de correção explícito, não um novo POST |
| `CONFIRMACAO_AUSENTE` | 422 | corpo sem `"confirm": true` — operação de alto impacto exige confirmação explícita |
| `ACABAMENTO_NAO_CADASTRADO` | 422 | `finish_raw` de um item aprovado não corresponde a nenhum acabamento cadastrado |
| `ITEM_PUBLICACAO_INVALIDO` | 422 | item aprovado sem `component_type_raw`/`sku_raw`/`price_raw`, ou `price_raw` não numérico |

---

### 14.7a — Importação via contrato JSON (planilhas)
**`POST /api/v1/imports/json`**

Caminho alternativo ao pipeline de PDF (14.1-14.7), para fontes em
planilha Excel normalizadas por um agente de IA externo no contrato
JSON v1.0 (`docs/10-contrato-importacao-json.md`). Cada item do
envelope gera uma linha em `extracted_items` (mesma trilha de auditoria
do pipeline de PDF) e segue **revisão por exceção**:

- **Fast path** (`review_status: "aprovado"`): `confidence >= 0.9`,
  `notes` ausente e `family`/`product_context`/`component_type`/`finish`
  já existem no catálogo — o item é publicado imediatamente em
  `component_variants`/`skus`/`prices` (reaproveita a mesma lógica de
  resolução/criação por nome de 14.7).
- Qualquer outro caso → `review_status: "pendente"`, com um
  `import_warning` por motivo (confiança baixa/média, `notes` do
  agente, ou entidade nova) — segue o fluxo normal de revisão (14.5/14.6)
  e publicação (14.7).

`price_table.code`: se já existir, os itens novos são adicionados/
atualizados nessa mesma versão (ainda em `rascunho`); senão, uma nova
`price_tables` é criada em `rascunho`. Reimportar um SKU já publicado
para a mesma `price_table.code` **atualiza o preço** (upsert por
`(component_variant_id, price_table_id)`), sem gerar erro de duplicidade.

Não há páginas reais para imports JSON — é criada uma única
`imported_pages` sintética (`page_profile: "json_import"`).

*Request* (resumido — ver contrato completo em docs/10):
```json
{
  "contract_version": "1.0",
  "price_table": { "code": "01-2026", "name": "Tabela de Preços 01-2026" },
  "source": { "description": "TABELA DE PRECO 01-2026_REUNIOES.xlsx", "generated_by": "agente-ia-externo" },
  "items": [
    {
      "ref": "REUNIOES.xlsx!P900!L6,9",
      "family": "Mesas de Reunião",
      "product_context": "Reunião 1200x900",
      "component_type": "Tampo",
      "dimension": "1200x900",
      "finish": "Argila",
      "sku": "3981113028",
      "price": 421.03,
      "confidence": 0.97,
      "notes": null
    }
  ]
}
```

*Response* `201 Created`:
```json
{
  "imported_file_id": 42,
  "price_table": { "id": 7, "code": "01-2026", "status": "rascunho" },
  "items_total": 1,
  "items_published": 1,
  "items_pending_review": 0,
  "warnings_count": 0,
  "items": [
    { "ref": "REUNIOES.xlsx!P900!L6,9", "extracted_item_id": 501, "review_status": "aprovado", "reasons": null }
  ]
}
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ARQUIVO_DUPLICADO` | 409 | já existe um import com o mesmo conteúdo JSON (`details.existing_import_id`) |
| `422` (validação padrão do FastAPI) | 422 | corpo fora do contrato (ex.: `contract_version` diferente de `"1.0"`, `items` vazio, `price < 0`, `confidence` fora de `[0,1]`) |

---

### 14.8 — Busca de catálogo
**`GET /api/v1/catalog/search?family=&product=&component=&dimension=&finish=&q=&page=`**

*Query*: todos os filtros são opcionais e combináveis; `q` faz busca
textual livre (descrição, SKU); os demais filtram por id ou nome exato
das respectivas entidades.

*Response* `200 OK`:
```json
{
  "items": [
    {
      "component_variant_id": 881,
      "family": "Mesas de Reunião",
      "product": "Reunião 1200x900",
      "component": "Tampo",
      "descriptor": "Inteiro Simples",
      "dimension": { "width_mm": 1200, "depth_mm": 900, "raw_label": "1200x900" },
      "finish": "Carvalho",
      "sku": "3981144789",
      "price": { "amount": 493.80, "currency": "BRL" },
      "price_table": { "id": 6, "code": "02-2025", "status": "vigente" }
    }
  ],
  "page": 1, "page_size": 50, "total": 233
}
```

*Erros*: `PARAMETRO_INVALIDO` (`400`) — ex. `dimension` em formato não
reconhecido.

---

### 14.9 — CRUD manual de componentes
Cobre criação/edição/remoção de **variações vendáveis**
(`component_variants`, com seu SKU e preço associados) diretamente no
catálogo — usado para preencher lacunas pontuais (ex. casos de
"código sem preço" identificados pela auditoria) sem depender de um
novo ciclo completo de importação.

**`GET /api/v1/components?...`** — mesmos filtros e formato de resposta
de 14.8 (reaproveita a busca de catálogo).

**`POST /api/v1/components`**

*Request*:
```json
{
  "product_id": 12,
  "component_id": 3,
  "dimension_id": 45,
  "finish_id": 7,
  "descriptor": "Inteiro Simples",
  "description": "Cadastro manual — confirmação telefônica com o fabricante em 08/06/2026",
  "sku": { "code": "3981199999", "notes": "Novo código informado pelo fabricante" },
  "price": { "amount": 510.00, "currency": "BRL", "price_table_id": 6 }
}
```

*Response* `201 Created`: objeto completo da variação criada, no mesmo
formato dos itens de 14.8, com `"source": "cadastro_manual"`.

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `REFERENCIA_INVALIDA` | 422 | `product_id`/`component_id`/`dimension_id`/`finish_id` não existe |
| `VARIACAO_DUPLICADA` | 409 | já existe `component_variant` idêntica (mesma combinação produto+componente+dimensão+acabamento+descritor — `UNIQUE` do schema) |
| `PRECO_DUPLICADO` | 409 | já existe preço para esta variação nesta versão de tabela (`UNIQUE(component_variant_id, price_table_id)`) |
| `CAMPO_OBRIGATORIO_AUSENTE` | 422 | corpo incompleto |

**`GET /api/v1/components/{id}`** — detalhe de uma variação (mesmo
formato; inclui histórico de preços por versão de tabela).
*Erros*: `COMPONENTE_NAO_ENCONTRADO` (`404`).

**`PATCH /api/v1/components/{id}`**

*Request* (campos parciais — ex.):
```json
{ "finish_id": 8, "descriptor": "Inteiro Encabeçado" }
```
*Response* `200 OK`: variação atualizada.
*Erros*: `COMPONENTE_NAO_ENCONTRADO` (404), `VARIACAO_DUPLICADA` (409 —
a alteração colidiria com outra variação existente), `REFERENCIA_INVALIDA` (422).

**`DELETE /api/v1/components/{id}`**

*Response*: `204 No Content`.
*Erros*:
| código | HTTP | quando |
|---|---|---|
| `COMPONENTE_NAO_ENCONTRADO` | 404 | `{id}` não existe |
| `COMPONENTE_EM_USO` | 409 | a variação está referenciada por `prices` de outra versão de tabela e/ou por orçamentos existentes (`details.referenced_by` lista onde) — a remoção é bloqueada para preservar a rastreabilidade (RN-16); a alternativa correta é **arquivar/descontinuar**, não excluir |

---

### 14.10 — Criação de orçamento
**`POST /api/v1/quotes`**

Cria um orçamento em `rascunho`, automaticamente ancorado à versão de
tabela `vigente` no momento da criação (RN-15 — campo não é escolhido
pelo cliente da API).

*Request*:
```json
{ "customer_id": 88, "valid_until": "2026-07-08", "notes": "Cliente pediu proposta para nova sede." }
```

*Response* `201 Created`:
```json
{
  "id": 245,
  "quote_number": "ORC-2026-0245",
  "status": "rascunho",
  "customer": { "id": 88, "name": "Studio Almeida Arquitetura" },
  "price_table": { "id": 6, "code": "02-2025", "status": "vigente" },
  "created_by": { "id": 7, "name": "Beatriz Nunes" },
  "created_at": "2026-06-08T16:10:00",
  "valid_until": "2026-07-08"
}
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `CLIENTE_NAO_ENCONTRADO` | 404 | `customer_id` não existe |
| `NENHUMA_TABELA_VIGENTE` | 409 | catálogo não tem nenhuma versão marcada `vigente` — bloqueia a criação (não há a partir de que preço orçar) |
| `CAMPO_OBRIGATORIO_AUSENTE` | 422 | corpo sem `customer_id` |

---

### 14.11 — Adição de componente ao orçamento
**`POST /api/v1/quotes/{quoteId}/items`**

Cria uma nova linha (`quote_item`) já com seus componentes físicos
iniciais — o caso de uso central da tela de montagem (`docs/04-…`,
tela 7). Cada componente é **validado e congelado** (RN-12/13/16) no
mesmo passo, de forma atômica: ou a linha inteira é criada com todos
os componentes precificados, ou nada é criado.

*Request*:
```json
{
  "product_id": 12,
  "label": "Reunião 1200x900 — Carvalho/Prata",
  "quantity": 2,
  "components": [
    { "component_variant_id": 881, "sku_id": 340 },
    { "component_variant_id": 902, "sku_id": 355 }
  ]
}
```

*Response* `201 Created`:
```json
{
  "id": 512,
  "quote_id": 245,
  "label": "Reunião 1200x900 — Carvalho/Prata",
  "quantity": 2,
  "components": [
    { "id": 1090, "component_variant_id": 881, "sku": "3981144789", "frozen_unit_price": 493.80, "frozen_currency": "BRL", "frozen_at": "2026-06-08T16:14:02" },
    { "id": 1091, "component_variant_id": 902, "sku": "398250071", "frozen_unit_price": 612.40, "frozen_currency": "BRL", "frozen_at": "2026-06-08T16:14:02" }
  ],
  "line_subtotal": 2212.40
}
```

Para adicionar um componente **opcional** a uma linha já existente
(ex. um Apoio/Credenza depois — `docs/05-…`, exemplo 2), usa-se:
**`POST /api/v1/quotes/{quoteId}/items/{itemId}/components`** — mesmo
formato de item de `components[]` acima, mesma resposta de componente
congelado, mesmas validações e códigos de erro.

*Erros* (válidos para ambos os endpoints acima):
| código | HTTP | quando |
|---|---|---|
| `ORCAMENTO_NAO_ENCONTRADO` / `ITEM_NAO_ENCONTRADO` | 404 | identificadores na URL não existem |
| `VARIACAO_NAO_ENCONTRADA` | 404 | `component_variant_id`/`sku_id` informado não existe no catálogo |
| `STATUS_INVALIDO` | 409 | orçamento não está em `rascunho` (não se edita um orçamento `enviado`/`aprovado` — RN-18) |
| `ITEM_SEM_PRECO` | 422 | a variação não tem preço na tabela vigente do orçamento (RN-12) — `details` aponta exatamente o componente e sugere alternativas |
| `ITEM_SEM_SKU` | 422 | a variação não tem SKU associado (RN-13) |
| `COMPONENTE_OBRIGATORIO_AUSENTE` | 422 | a composição enviada não atende o mínimo definido para o tipo de produto (ex. "Reunião" sem Estrutura — RN-07); `details.missing_component_types` lista o que falta |
| `DESCRITOR_INCOMPATIVEL` | 422 | combinação tampo↔estrutura fora do mapeamento de compatibilidade (RN-04) |
| `DIMENSAO_INCOMPATIVEL` | 422 | componente não existe para a dimensão do produto-base selecionado (RN-03) |

---

### 14.12 — Atualização de quantidade / desconto / acabamento
Duas operações distintas, em granularidades diferentes do modelo:

**`PATCH /api/v1/quotes/{quoteId}/items/{itemId}`** — quantidade,
desconto e observações da **linha**.

*Request* (campos parciais):
```json
{ "quantity": 3, "discount_percent": 5, "discount_reason": "Negociação — pedido recorrente do cliente.", "notes": "Entrega prevista para agosto." }
```

*Response* `200 OK`: linha atualizada, com `line_subtotal` recalculado
(propagação de quantidade aos componentes — RN-08).

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ITEM_NAO_ENCONTRADO` | 404 | — |
| `STATUS_INVALIDO` | 409 | orçamento fora de `rascunho` |
| `QUANTIDADE_INVALIDA` | 422 | valor não-positivo |
| `DESCONTO_SEM_JUSTIFICATIVA` | 422 | `discount_percent`/`discount_amount` informado sem `discount_reason` (RN-09) |
| `DESCONTO_INVALIDO` | 422 | percentual e valor fixo informados simultaneamente, ou fora da faixa permitida |

**`PATCH /api/v1/quotes/{quoteId}/items/{itemId}/components/{componentId}`**
— troca de **acabamento/variação** de um componente já incluído (ex.
"trocar de Carvalho para Amêndoa"). Dispara **recongelamento explícito**
(RN-06/16): o novo preço de catálogo é copiado, e a resposta mostra o
valor anterior lado a lado com o novo, para conferência.

*Request*:
```json
{ "component_variant_id": 905, "sku_id": 360 }
```

*Response* `200 OK`:
```json
{
  "id": 1090,
  "component_variant_id": 905,
  "sku": "3981149472",
  "previous_frozen_unit_price": 493.80,
  "frozen_unit_price": 472.85,
  "frozen_currency": "BRL",
  "frozen_at": "2026-06-08T16:40:11",
  "price_changed": true
}
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `COMPONENTE_NAO_ENCONTRADO` | 404 | `{componentId}` não existe na linha |
| `STATUS_INVALIDO` | 409 | orçamento fora de `rascunho` |
| `ITEM_SEM_PRECO` / `ITEM_SEM_SKU` | 422 | a nova variação não tem preço/SKU válido (RN-12/13 — a troca não se efetiva) |
| `VARIACAO_INCOMPATIVEL` | 422 | a nova variação não é do mesmo tipo de componente do item original (ex. tentar "trocar" um Tampo por uma Estrutura) |

---

### 14.13 — Cálculo de total
**`GET /api/v1/quotes/{quoteId}/totals`**

Calcula o total **ao vivo**, a partir dos `quote_item_components`
atuais — útil para conferência durante a montagem (não é o valor
"oficial" registrado, ver abaixo).

*Response* `200 OK`:
```json
{
  "quote_id": 245,
  "subtotal": 2774.90,
  "discount_percent": 5,
  "discount_amount": 138.75,
  "tax_amount": 0,
  "freight_amount": 0,
  "total": 2636.15,
  "currency": "BRL",
  "is_snapshot": false,
  "calculated_at": "2026-06-08T16:45:00",
  "warnings": [
    { "code": "VERSOES_DE_TABELA_MISTAS", "message": "Este orçamento contém itens precificados nas tabelas 01-2025 e 02-2025." }
  ]
}
```

**`POST /api/v1/quotes/{quoteId}/totals/freeze`** — calcula **e grava**
o snapshot oficial em `quote_totals` (o "congelamento do total" — RN-16,
tipicamente acionado ao avançar para `enviado`, dentro do fluxo de
revisão final RN-18). Mesmo formato de resposta, com `"is_snapshot":
true`.

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ORCAMENTO_NAO_ENCONTRADO` | 404 | — |
| `ORCAMENTO_VAZIO` | 409 | orçamento sem nenhuma linha — não há o que totalizar/congelar |
| `REVISAO_PENDENTE` | 409 | (apenas em `/freeze`) checklist de revisão final (RN-18) aponta pendências — `details.checklist` lista cada uma, nomeada e acionável |

---

### 14.14 — Exportação de orçamento
**`GET /api/v1/quotes/{quoteId}/export?format=pdf`**

Gera o documento final do orçamento (tela 9 de `docs/04-…`) a partir do
**snapshot congelado** (`quote_totals` + `quote_item_components`) — nunca
recalcula na hora de exportar, preservando exatamente o que foi (ou
será) comunicado ao cliente.

*Query*: `format` — `pdf` (padrão) ou `xlsx`.

*Response* `200 OK` — `Content-Type: application/pdf` (ou
`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`),
corpo binário, com `Content-Disposition: attachment;
filename="ORC-2026-0245.pdf"`.

Alternativamente — para o frontend que prefere abrir em nova aba sem
forçar download — `?as=link` retorna:
```json
{ "url": "/files/exports/orc-245-v3.pdf", "format": "pdf", "generated_at": "2026-06-08T17:02:30" }
```

*Erros*:
| código | HTTP | quando |
|---|---|---|
| `ORCAMENTO_NAO_ENCONTRADO` | 404 | — |
| `TOTAIS_NAO_CALCULADOS` | 409 | orçamento ainda não tem snapshot em `quote_totals` — exporta-se o **oficial**, não um cálculo ao vivo; é preciso congelar primeiro (`/totals/freeze`) |
| `FORMATO_INVALIDO` | 422 | `format` fora do conjunto suportado |

---

## 15. O que este documento deliberadamente não resolve

- **Escolha definitiva de framework**: FastAPI/React são a recomendação
  fundamentada (ver introdução), não uma imposição — qualquer stack que
  respeite a separação de camadas da seção 1 atende ao desenho.
- **Geração do PDF/planilha de exportação** (seção 14.14): o **contrato**
  está definido; a biblioteca/*template* de geração é uma decisão de
  implementação a ser tomada quando a tela 9 for construída.
- **Política de retenção de logs e backups em produção** (volumes,
  prazos exatos, onde ficam fisicamente): depende de decisões de
  infraestrutura da organização, fora do escopo de uma proposta de
  arquitetura de aplicação.
- **Testes de carga/performance**: não há indício, em nenhum documento
  anterior, de volume que justifique esse investimento agora — vale
  revisitar se o uso real revelar o contrário.
