# Helence Orçamento — guia de implementação

> Documento consolidado para quem vai **começar a codar este projeto agora**,
> sem ter participado das discussões anteriores. Reúne, em um só lugar, o
> essencial dos documentos `docs/01` a `docs/09` e do diretório
> `docs/samples/`. Sempre que precisar de detalhe adicional, os documentos de
> origem são referenciados por número.
>
> **Documentos de origem**:
> - `docs/01-auditoria-pdf-dominio.md` — auditoria do PDF de origem e do domínio
> - `docs/02-spike-extracao-pdf.md` — prova de conceito da extração
> - `docs/03-modelagem-sqlite.md` — modelo de dados (24 tabelas)
> - `docs/04-ux-operacional.md` — telas e fluxos operacionais (10 telas)
> - `docs/05-regras-orcamento.md` — regras de negócio RN-01 a RN-18
> - `docs/06-arquitetura-api.md` — arquitetura backend/frontend/API
> - `docs/07-plano-implementacao.md` — plano de fases (Fase 0 a 12)
> - `docs/08-testes-qualidade.md` — estratégia de testes e critérios de qualidade
> - `docs/09-implantacao-operacao.md` — instalação, operação e deploy
> - `docs/samples/extracao-amostra.json` — gabarito de extração (páginas 1, 2, 432)
> - `docs/samples/fixtures-orcamento.json` — fixtures de teste

---

## 1. Visão geral do sistema

O **Helence Orçamento** é um sistema interno para:

1. **Importar** tabelas de preços de mesas de reunião, publicadas pelo
   fabricante em PDF (atualmente um arquivo de 435 páginas, gerado a partir de
   uma planilha Excel via Ghostscript — texto nativo, sem OCR).
2. **Extrair, normalizar e revisar** os dados dessas tabelas (modelos,
   componentes, dimensões, acabamentos, SKUs e preços), com forte ênfase em
   **rastreabilidade** e **revisão humana** antes de qualquer dado virar
   "verdade" no catálogo.
3. **Manter um catálogo normalizado** de produtos, componentes, variantes,
   acabamentos e preços, versionado por **tabela de preços** (ex.: `01-2025`,
   `02-2025`), com histórico.
4. **Montar orçamentos** para clientes, compondo produtos a partir de
   componentes do catálogo (tampo + estrutura + apoio, por exemplo), com
   **preços congelados** no momento em que o item é adicionado ao orçamento.
5. **Auditar** a origem de qualquer preço — do orçamento até a linha exata do
   PDF de onde ele veio.

O sistema é usado por uma **equipe interna pequena** (Importador, Revisor,
Aprovador/Admin, Vendedor, Auditor) — não é voltado ao cliente final. O
cliente recebe apenas o PDF/relatório final do orçamento (tela 9 de
`docs/04`).

---

## 2. Problema que o sistema resolve

A tabela de preços do fabricante (`data/source.pdf`, 435 páginas) tem
características que tornam **impossível usá-la diretamente** para orçamentos
confiáveis (ver `docs/01`, seções 1–4):

- **Não é uma lista de produtos prontos**: cada componente (tampo, estrutura,
  apoio/credenza) tem código e preço **próprios**; não existe "código de mesa
  completa".
- **Layout tabular fragmentado**: cada "linha lógica de produto" vira de 3 a 5
  linhas físicas de texto no PDF (nome+códigos / observações / variante+preços),
  exigindo reconstrução por coordenadas.
- **Ambiguidades sistemáticas**: nomes de acabamento quebrados em duas linhas
  (ex. "Nogueira Cádiz" vira "...CARVALHO NOGUEIRA" + "CADIZ GRAFITE..."),
  problema de encoding (`U+FFFD`/`�` em 100% dos textos livres com acento).
- **Inconsistências reais nos dados**: 45 ocorrências de "código sem preço"
  (concentradas nas páginas 432–435), 9.287 códigos duplicados entre seções de
  profundidade (mesmo componente físico reimpresso com o mesmo preço — não são
  produtos diferentes), variações de layout entre seções (tampo inteiro vs.
  bi/tri-partido vs. redondas/lounge/STAFF).
- **Múltiplas versões ao longo do tempo**: a tabela é reajustada
  periodicamente (`01-2025`, `02-2025`, ...) e os orçamentos já emitidos **não
  podem mudar de preço retroativamente** quando uma nova tabela é publicada
  (RN-16, congelamento).

O sistema resolve isso construindo, em etapas controladas e auditáveis:
**extração → normalização → revisão humana → catálogo confiável → orçamento
com preço congelado e rastreável até a origem**.

---

## 3. Escopo do MVP

Com base em `docs/07` (plano de fases) e `docs/06`/`docs/08`/`docs/09`, o MVP
cobre:

- **Modelo de dados completo** (24 tabelas, `docs/03`) com `PRAGMA
  foreign_keys = ON` e migrations numeradas.
- **Catálogo normalizado**: famílias de produto, produtos/dimensões,
  componentes, variantes de componente, acabamentos, SKUs, preços por tabela
  de versão.
- **Importação de PDF**: upload, extração via `pymupdf`, normalização em
  `extracted_items`, com `extracted_rows`/`extracted_item_source_rows` para
  rastreabilidade até o texto bruto.
- **Fila de revisão humana**: triagem por nível de confiança, comparação
  origem×normalizado, edição campo a campo (SKU, preço, acabamento, dimensão,
  componente), aprovação/rejeição individual e em **lote com pré-visualização**
  e **rede de segurança contra sobrescrever decisões humanas** (`docs/04`,
  telas 3–4).
- **Publicação de versão de tabela** no catálogo (tela 5), de forma atômica
  (tudo ou nada).
- **Consulta ao catálogo** com filtros por família/componente/acabamento/
  dimensão e histórico de preço entre versões (tela 6).
- **Montagem de orçamento**: composição de componentes compatíveis,
  acabamento filtrado por tipo de componente, **preço congelado no momento da
  adição** (RN-16), bloqueio de itens sem preço cadastrado (tela 7).
- **Edição de item de orçamento** com aviso explícito de recongelamento ao
  trocar variante/acabamento (tela 8).
- **Exportação/visualização do orçamento** (PDF, status, histórico — tela 9).
- **Auditoria de origem de preço**: linha do tempo extração → revisão →
  publicação → uso em orçamento (tela 10).
- **Suporte a múltiplas versões de tabela de preço** (`status`:
  `rascunho`/`vigente`/`substituida`/`arquivada`) e aviso de
  `VERSOES_DE_TABELA_MISTAS` em orçamentos.
- **Autenticação por sessão** com papéis (Importador/Revisor/Aprovador/
  Vendedor/Auditor).
- **Backup/restauração de SQLite**, logging estruturado, tratamento de erro
  padronizado.
- **Suíte de testes** cobrindo as 14 categorias de `docs/08`.

---

## 4. Fora de escopo do MVP

Listado em `docs/09` (seção 19) e consolidado aqui:

- **Margem, desconto, impostos, frete** — não existem no PDF de origem; RN-09/
  RN-10 (`docs/05`) ficam **pendentes de definição com a área comercial**
  (ver seção 15 deste documento).
- **OCR** — o PDF tem texto nativo; não é necessário processamento de imagem.
- **Multi-idioma / múltiplas moedas** — sistema fixo em pt-BR / BRL.
- **SSO, MFA, gestão avançada de usuários** — autenticação por sessão simples
  é suficiente para o MVP.
- **Fila de processamento distribuída (Celery/Redis), retries automáticos
  robustos** — processamento assíncrono em processo, com endpoint de status
  por polling.
- **Observabilidade externa (Sentry, Datadog, Prometheus)** — logging
  estruturado em arquivo é suficiente.
- **Notificações por e-mail/push**.
- **Alta concorrência de escrita** — SQLite é single-writer; aceitável para o
  volume de uso interno do MVP. Migração futura para PostgreSQL é discutida em
  `docs/06` (seção 11), mas não faz parte do MVP.
- **Testes de carga/performance e testes E2E de UI** (`docs/08`, seção 4).
- **Compatibilidade física tampo↔estrutura totalmente modelada** — RN-04
  trata isso como regra inferida/heurística no MVP, não como tabela de
  compatibilidade completa e validada com o fabricante.
- **Migrações destrutivas de schema automatizadas** — mudanças estruturais
  grandes no SQLite são tratadas manualmente, com backup prévio.

---

## 5. Stack técnica

(`docs/06`, seções 1–4)

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11+, **FastAPI** |
| Banco de dados | **SQLite** (arquivo único, `PRAGMA foreign_keys = ON` por conexão) |
| Extração de PDF | **pymupdf (fitz)** — `get_text("words")` / `get_text("rawdict")` com bbox e vetores de direção |
| Frontend | **React + TypeScript + Vite** |
| Comunicação | REST/JSON sob `/api/v1`, tipos TS gerados a partir do OpenAPI do FastAPI |
| Processamento assíncrono | In-process (sem fila externa), com endpoint de status via polling |
| Logging | JSON estruturado, 3 focos (request / domínio / erro), correlação por `request_id` |
| Autenticação | Sessão (cookie), papéis: Importador/Revisor/Aprovador/Vendedor/Auditor |
| Migrations | SQL numerado + tabela `schema_migrations`, aplicado no startup, idempotente |
| Backup | SQLite Online Backup API / `sqlite3 .backup` |
| Containerização (opcional) | Docker Compose |

**Por que pymupdf** (`docs/02`): é a única das bibliotecas avaliadas
(pypdf, pdfplumber, pymupdf, camelot, tabula-py) que permite isolar
programaticamente texto rotacionado/vertical e fornece bbox + vetor de direção
por palavra, essenciais para reconstruir os blocos verticais de 3–5 linhas do
PDF de origem.

**Por que SQLite no MVP** (`docs/03`, `docs/06`): zero infraestrutura extra,
arquivo único fácil de versionar/copiar/backup, suficiente para o volume e
concorrência de uma equipe interna pequena. O modelo já foi desenhado para
migração futura a PostgreSQL ser viável (tipos, constraints e nomes
compatíveis).

---

## 6. Arquitetura

(`docs/06`, seções 2–9)

### 6.1 Estrutura de diretórios (alvo)

```
helence-orcamento/
├── backend/
│   ├── app/
│   │   ├── api/            # routers FastAPI (v1)
│   │   ├── db/              # conexão, migrations, schema.sql
│   │   ├── domain/           # regras de negócio (RN-01..18)
│   │   ├── extraction/       # pipeline de extração de PDF
│   │   ├── schemas/           # modelos Pydantic (request/response)
│   │   └── services/          # orquestração (importação, revisão, orçamento)
│   ├── data/                  # banco SQLite + uploads (não versionado)
│   ├── logs/                  # logs (não versionado)
│   ├── migrations/            # 0001_initial.sql, 0002_..., etc.
│   ├── scripts/                # backup.sh, restore.sh, seed
│   └── tests/                  # unit / integration
├── frontend/
│   ├── src/
│   │   ├── api/                # cliente gerado a partir do OpenAPI
│   │   ├── pages/               # telas 1–10 de docs/04
│   │   ├── components/
│   │   └── ...
│   └── ...
├── data/
│   ├── source.pdf               # PDF de origem (amostra)
│   └── prices.xlsx               # extração de referência anterior
├── docs/
└── scripts/spikes/                # scripts exploratórios descartáveis
```

> **Nota**: `backend/` e `frontend/` ainda **não existem** no repositório —
> o projeto está na fase "Fase 0" do plano (`docs/07`). Esta estrutura é o
> **alvo**, descrito também em `docs/09` (seção 2).

### 6.2 Camadas e fluxo de dados

Arquitetura em **3 camadas de dados** com dependência **unidirecional**
(`docs/03`, seção 1):

```
Importação/Origem  ──►  Catálogo Normalizado  ──►  Orçamentos
(imported_files,         (product_families,        (quotes,
 imported_pages,          products, dimensions,      quote_items,
 extracted_rows,          product_components,        quote_item_components)
 extracted_items,         component_variants,
 extracted_item_         finishes, skus, prices,
 source_rows,            price_tables)
 import_review_decisions)
```

- A camada de **Importação/Origem** nunca é lida diretamente pelos fluxos de
  orçamento — serve apenas para auditoria/rastreabilidade.
- A camada de **Catálogo** é a única fonte usada para montar orçamentos.
- A camada de **Orçamentos** referencia o catálogo, mas **congela** os valores
  no momento do uso (RN-16) — mudanças futuras no catálogo não alteram
  orçamentos já criados.

### 6.3 Comunicação frontend/backend

- API REST/JSON sob `/api/v1`, documentada via OpenAPI (FastAPI gera
  automaticamente).
- Tipos TypeScript do frontend são **gerados a partir do schema OpenAPI**
  (evita duplicação manual de contratos).
- Envelope de erro padronizado:
  ```json
  { "error": { "code": "ITEM_SEM_PRECO", "message": "...", "details": { } } }
  ```
  com exceções de domínio nomeadas mapeadas para códigos HTTP (`docs/06`,
  seção 9). A lista completa de ~22 códigos de erro nomeados (ex.
  `ARQUIVO_DUPLICADO`, `ARQUIVO_INVALIDO`, `ARQUIVO_MUITO_GRANDE`,
  `VERSAO_DUPLICADA`, `ITEM_SEM_PRECO`, `VARIACAO_INDISPONIVEL`,
  `VERSOES_DE_TABELA_MISTAS`, `CONFLITO_DE_EDICAO`, etc.) deve estar 100%
  coberta por testes (`docs/08`, seção 3.1).

### 6.4 Processamento assíncrono

- Importação de PDF roda em **background in-process** (sem Celery/Redis).
- Frontend faz **polling** num endpoint de status (tela 2 de `docs/04`),
  recebendo progresso por página, contagens por nível de confiança e feed de
  atividade recente.
- Falha total → erro dedicado; falha parcial por página → página marcada com
  `confidence_level = baixa` e segue para revisão.

### 6.5 Logging e tratamento de erros

- JSON estruturado, 3 focos: **request** (método, rota, status, duração,
  `request_id`), **domínio** (eventos de negócio: importação concluída, item
  aprovado, orçamento publicado), **erro** (stacktrace + contexto, nunca dados
  sensíveis).
- `request_id` correlaciona logs entre as 3 categorias e aparece nas respostas
  de erro (`Ver detalhes técnicos` na UI).

### 6.6 Autenticação e papéis

Sessão por cookie. Papéis e permissões (`docs/04`, seção 0):

| Papel | Acesso |
|---|---|
| Importador | Telas 1–2 (upload, processamento) |
| Revisor | Telas 3–4 (fila de revisão, correção) + leitura da tela 5 |
| Aprovador/Admin | Telas 5, 10 + tudo do Revisor + ações administrativas |
| Vendedor | Telas 6–9 (catálogo, orçamentos) |
| Auditor | Tela 10 (auditoria de origem) |

---

## 7. Modelo de dados

(`docs/03`, completo — 24 tabelas, 32 índices)

### 7.1 Visão por camada

**Importação/Origem**:
- `imported_files` — arquivo PDF + hash (detecção de duplicidade)
- `imported_pages` — páginas processadas, perfil de layout detectado
- `extracted_rows` — linhas de texto bruto com coordenadas (`y_coordinate`)
- `extracted_items` — itens normalizados (SKU, preço, acabamento, dimensão,
  componente, `confidence_level`, `review_status`, `extraction_notes`)
- `extracted_item_source_rows` — N:N entre item normalizado e linhas brutas
  de origem
- `import_review_decisions` — **log append-only** de decisões humanas
  (aprovado/rejeitado/corrigido), nunca sobrescrito

**Catálogo Normalizado**:
- `price_tables` — versões de tabela (`code`, `status`:
  rascunho/vigente/substituida/arquivada, `valid_from`/`valid_to`)
- `product_families` — ex. "Mesas de Reunião"
- `products` — produto-base (ex. "Reunião 1200x900")
- `dimensions` — dimensões flexíveis (largura×profundidade, diâmetro, ou
  L×P×A para conectores)
- `product_components` — tipos de componente (Tampo, Estrutura, Apoio
  Credenza, Conexão)
- `component_variants` — variações vendáveis (ex. "Tampo Inteiro Simples –
  Carvalho")
- `finishes` — acabamentos com `finish_group` (madeirado/metálico/pé),
  podendo ser `NULL` quando o grupo é ambíguo até revisão
- `skus` — códigos de produto (10 dígitos, podem repetir entre variantes
  fisicamente idênticas)
- `prices` — **tabela fato**: resolve o relacionamento N:N entre `skus` e
  `component_variants`, por `price_table_id`. Liga-se opcionalmente a
  `extracted_items` (origem)

**Orçamentos**:
- `customers`
- `quotes` — cabeçalho do orçamento (cliente, validade, status:
  rascunho/enviado/aprovado)
- `quote_items` — "linhas" do orçamento (composições)
- `quote_item_components` — componentes de cada linha, com
  `frozen_unit_price`/`frozen_currency` (RN-16) e `price_source_id` (FK
  nullable, `ON DELETE SET NULL`, para auditoria)

### 7.2 Cadeia de rastreabilidade

```
quote_item_components
  → prices
    → extracted_items
      → extracted_item_source_rows
        → extracted_rows
          → imported_pages
            → imported_files
```

Esta cadeia é o que alimenta a tela 10 (Auditoria de origem) e deve estar
**sempre navegável** — mesmo quando o preço foi cadastrado manualmente (nesse
caso a cadeia "começa" em `prices` sem `extracted_item`, ver `docs/04` seção
10, "Preço sem origem em PDF").

### 7.3 Constraints essenciais (`docs/03`, seção 5)

- `PRAGMA foreign_keys = ON` deve ser configurado **a cada conexão** (não é
  persistido pelo SQLite) — verificar isso em testes de schema (`docs/08`,
  seção 2.1).
- UNIQUE: `imported_files.file_hash`, `price_tables.code`,
  `(component_variant_id, price_table_id)` em `prices` (mesma variante não
  pode ter dois preços na mesma tabela).
- CHECK: `prices.unit_price >= 0`, `quote_item_components.frozen_unit_price >=
  0`, valores de enum (`status`, `review_status`, `confidence_level`, etc.)
  restritos a listas fechadas.
- `ON DELETE`: cascateamentos cuidadosos na camada de importação (uma
  importação pode ser removida sem quebrar o catálogo já publicado);
  `price_source_id` em `quote_item_components` usa `ON DELETE SET NULL` —
  apagar a origem **nunca** apaga o congelamento do orçamento.

### 7.4 Verificação de integridade

Após qualquer migração ou operação em lote: `PRAGMA foreign_key_check` deve
retornar vazio. Isso é parte dos testes de schema (`docs/08`, seção 2.1) e do
checklist de deploy (`docs/09`, seção 18).

---

## 8. Fluxo de importação

(`docs/04`, telas 1–2; `docs/06`, seções 6–7; `docs/02`)

1. **Upload (tela 1)**: Importador envia um PDF + código da versão (ex.
   `02-2025`) + vigência opcional + observações.
   - Validações: tipo `.pdf`, tamanho máximo, **hash do arquivo** comparado
     com `imported_files.file_hash` (alerta se repetido), **código de versão
     único** em `price_tables.code`.
2. **Processamento (tela 2)**: extração assíncrona in-process via pymupdf.
   - Para cada página: detecta o **perfil de layout** (cabeçalho padrão
     "TAMPOS + ESTRUTURAS..." vs. "REUNIÕES" das págs. 432–435 vs. seções
     bi/tri-partido), extrai blocos verticais de 2–5 linhas, associa N
     códigos × N preços × N acabamentos posicionalmente (N=9 para tampos,
     N=3 para estruturas/apoio em aço).
   - Cada item extraído recebe `confidence_level` (alta/média/baixa) e
     `extraction_notes` (ex. "código sem preço pareado na faixa esperada").
   - Falhas por página não interrompem o processamento — página marcada,
     itens ficam com confiança baixa.
   - Progresso exposto via polling (contagem de páginas, itens por
     confiança, avisos).
3. **Saída**: `extracted_rows` (texto bruto + coordenadas), `extracted_items`
   (normalizado, `review_status = pendente`), `extracted_item_source_rows`
   (rastreabilidade), `import_warnings` (avisos agregados, ex.
   `VERSOES_DE_TABELA_MISTAS` não se aplica aqui — esse é de orçamento; aqui
   seriam avisos como item órfão, código sem preço, acabamento desconhecido).

### 8.1 Particularidades conhecidas a tratar (de `docs/01`)

- **"Nogueira Cádiz"** quebrado em duas linhas de cabeçalho deve ser tratado
  como **um único acabamento** — validar contando 9 nomes ⇄ 9 códigos ⇄ 9
  preços por linha.
- **Encoding `U+FFFD`** em texto livre acentuado: usar **dicionário de
  correção de termos do domínio** (lista finita: nomes de acabamento,
  "Reunião", "Estrutura", "Caixa de Tomada", etc.) em vez de tentar
  "consertar" o Unicode.
- **45 ocorrências de "código sem preço"** nas páginas 432–435: tratar como
  `extracted_items` com `unit_price = NULL` e `confidence_level = baixa`,
  nunca descartar silenciosamente.
- **9.287 códigos duplicados** entre seções de profundidade com o mesmo
  preço: **não criar produtos duplicados** — o componente físico é o mesmo;
  modelar via reaproveitamento de `component_variant`/`sku` entre `products`
  diferentes (mesma variante associada a múltiplas dimensões/produtos).
- **Layout "híbrido" (Bi/Tri-Partido)**: ~2.899 linhas (~4%) onde o
  classificador automático pode não decidir o tipo de componente — devem cair
  como `confidence_level = baixa` para revisão manual, nunca como um "tipo de
  componente" inventado.

---

## 9. Fluxo de revisão

(`docs/04`, telas 3–5; `docs/05` RN sobre revisão)

1. **Fila de triagem (tela 3)**: lista todos os `extracted_items` da
   importação, com filtros (busca textual, nível de confiança, status,
   intervalo de página, seção). Ordenação padrão por confiança crescente.
   Permite seleção múltipla e ações em lote diretas (aprovar/rejeitar) para
   casos óbvios.
2. **Correção item a item (tela 4)** — tela central do fluxo:
   - Painel esquerdo: render da página original do PDF, com a linha do item
     destacada via `y_coordinate`.
   - Painel direito: linha bruta de origem (com toggle para contexto
     vizinho) **ao lado** do item normalizado editável (SKU, preço,
     acabamento, dimensão, componente).
   - Edição de **acabamento**: combo restrito ao vocabulário fechado de
     `finishes`, com opção "cadastrar novo acabamento" (fica marcado para
     atenção do Aprovador).
   - Edição de **preço**: máscara BRL, normaliza ruídos de espaçamento
     (`"744 ,22"` → `744,22`), alerta (não bloqueia) se valor distante da
     média de itens semelhantes.
   - Edição de **SKU**: valida 9–10 dígitos; se já associado a outra
     variação, **avisa mas não bloqueia** (padrão esperado, conforme achado
     dos 9.287 códigos duplicados).
   - **Aprovar**: grava `review_status = aprovado` (ou `corrigido`, se houve
     edição) + entrada em `import_review_decisions`.
   - **Rejeitar**: exige justificativa obrigatória; item não segue para o
     catálogo nesta versão.
   - **Correção em lote**: agrupa candidatos pelo **valor bruto original**
     (`*_raw`), com escopo (página/perfil de página/importação inteira),
     pré-visualização obrigatória, e **exclusão automática de itens com
     decisão humana prévia** (nunca sobrescreve silenciosamente).
3. **Aprovação para catálogo (tela 5)** — ponto de não-retorno:
   - Resumo: aprovados / rejeitados / pendentes (pendentes **nunca** entram).
   - Diff do que muda no catálogo: novos acabamentos, SKUs com preço
     atualizado, novos preços.
   - Conflitos bloqueantes (ex. preço 40% maior que versão anterior) devem
     ser resolvidos ou marcados como "esperado" antes de publicar.
   - Publicação é **atômica** (tudo ou nada) — em caso de falha, nenhuma
     alteração é aplicada.
   - Define `valid_from`/`valid_to` e, opcionalmente, marca a versão como
     `vigente` (o que torna a anterior `substituida`).
   - Exclusivo de Aprovador/Admin; Revisor vê em modo somente leitura.

---

## 10. Fluxo de orçamento

(`docs/04`, telas 6–10; `docs/05` RN-01 a RN-18)

1. **Consulta do catálogo (tela 6)**: busca/filtros por família, componente,
   acabamento, dimensão; seleção de versão de tabela (padrão: vigente);
   histórico de preço entre versões.
2. **Montagem (tela 7)**:
   - Seleciona cliente, validade, tabela-base (padrão = vigente; usar versão
     arquivada gera aviso explícito no orçamento final).
   - Cada "linha" agrega 1+ componentes (ex. tampo + estrutura + apoio).
   - **Acabamento filtrado por tipo de componente** — restrição de opções,
     não validação pós-erro (ex. Tampo só mostra os 9 acabamentos
     "madeirados"; Estrutura só os 3 metálicos).
   - Item sem preço na tabela-base: **adição bloqueada** com mensagem
     explicativa (caso real das págs. 432–435).
   - **Preço congelado no momento da adição** (RN-16): `frozen_unit_price` e
     `frozen_currency` são gravados em `quote_item_components` e **não mudam**
     se o catálogo for atualizado depois.
3. **Edição de item (tela 8)**:
   - Trocar variante/acabamento recalcula o preço a partir da tabela-base do
     orçamento e **mostra o aviso de recongelamento** (valor antigo vs. novo)
     antes de salvar.
   - Orçamentos com status `enviado`/`aprovado` exigem reabertura explícita
     antes de editar.
4. **Exportação (tela 9)**: pré-visualização fiel ao PDF final, com
   subtotal/desconto/total; ações de exportar PDF, copiar link, marcar como
   enviado, duplicar. Dados internos (confiança de extração, notas de
   revisão) **nunca** aparecem na visão do cliente.
5. **Auditoria (tela 10)**: a partir de qualquer SKU/preço/orçamento,
   reconstrói a linha do tempo extração → revisão → publicação → uso em
   orçamento, com link para a página original do PDF.

### 10.1 Regras de negócio centrais (RN-01 a RN-18, `docs/05`)

As regras completas estão em `docs/05`; as mais estruturais para o MVP:

- **RN-16 (congelamento de preço)**: preço gravado em
  `quote_item_components.frozen_unit_price` no momento da adição/edição;
  imutável até nova edição explícita do item.
- **Compatibilidade componente×dimensão**: só é possível compor componentes
  cuja `dimension_id`/`product_id` seja compatível com a linha do orçamento
  (ver categoria 14 de testes em `docs/08`).
- **Múltiplas versões de tabela**: orçamento pode ter itens de versões
  diferentes se o vendedor explicitamente trocar a tabela-base de uma linha —
  isso gera o aviso `VERSOES_DE_TABELA_MISTAS`.
- **Item sem preço**: nunca permite adicionar ao orçamento (RN-12 em
  `docs/05`/`docs/08`).
- Os **4 exemplos completos** (Exemplo 1–4) em `docs/05` espelham os
  `quote_scenarios` de `docs/samples/fixtures-orcamento.json` e devem virar
  testes E2E.

---

## 11. Estratégia de extração de PDF

(`docs/02`, `docs/01` seções 1–4 e 8)

- **Biblioteca**: `pymupdf` (fitz), usando `get_text("words")` ou
  `get_text("rawdict")` para obter bbox + vetor de direção por palavra —
  necessário para reconstruir blocos verticais e (potencialmente) texto
  rotacionado.
- **Estratégia geral**:
  1. Detectar o **perfil de página** (cabeçalho "TAMPOS + ESTRUTURAS..." vs.
     "REUNIÕES" vs. seção com "DESCRIÇÃO TÉCNICA").
  2. Agrupar palavras em **linhas físicas** por coordenada Y.
  3. Agrupar linhas físicas em **blocos lógicos de produto** (2–5 linhas):
     nome+códigos / observação / variante+preços.
  4. Mapear posicionalmente código↔preço↔acabamento (N=9 para tampos, N=3
     para estrutura/apoio em aço), usando a linha de cabeçalho de colunas
     como referência de ordem (com a correção de "Nogueira Cádiz" = 1 nome).
  5. Extrair `dimensão` do "MODELO" (`NNNNxNNNN`, `Diam NNNNmm`, ou `NNNN x
     NNNN x NNNN mm`).
  6. Classificar `componente` por vocabulário fixo (Tampo/Estrutura/Apoio-
     Credenza/Conexão).
  7. Aplicar dicionário de correção de encoding para texto livre (descrição,
     observações, nomes de acabamento).
- **Gabarito de validação**: `docs/samples/extracao-amostra.json` contém a
  extração de referência das páginas 1, 2 e 432 — usar como teste de
  regressão "golden file" (categoria 10 de `docs/08`, marcado `slow` em
  pytest).
- **`data/prices.xlsx`**: resultado de uma extração anterior (72.137 linhas em
  `produtos_mcp`) — útil como **referência de validação cruzada**, não como
  fonte de verdade. Tem os mesmos problemas de encoding e o mesmo grupo
  "híbrido" de ~4% das linhas. Requer sanitização de XML antes de abrir
  (`openpyxl` falha sem isso).
- **Riscos priorizados** (de `docs/01`, seção 4): quebras de linha (alta),
  cabeçalhos repetidos (média), célula de cabeçalho quebrada (alta),
  observações misturadas com dados (alta), código sem preço (alta, mas
  localizado em 4 páginas), variações de layout por seção (alta), códigos
  duplicados entre seções (alta — afeta o modelo de dados).

---

## 12. Estratégia de testes

(`docs/08`, completo)

### 12.1 Pirâmide de testes

- **Unitários**: regras de negócio puras (RN-01..18), parsing/normalização de
  texto, cálculo de congelamento — sem banco nem PDF.
- **Integração**: SQLite em arquivo temporário (com `PRAGMA foreign_keys =
  ON`), contrato HTTP via FastAPI `TestClient`.
- **E2E**: os 4 `quote_scenarios` de `docs/05`/`fixtures-orcamento.json`,
  exercitando importação → revisão → catálogo → orçamento → auditoria.

### 12.2 As 14 categorias (cada uma com fixtures dedicadas)

1. Schema SQLite (FKs, constraints, `PRAGMA foreign_key_check`)
2. Importação (upload, hash duplicado, processamento, perfis de página)
3. Normalização (parsing de blocos, "Nogueira Cádiz", encoding)
4. Revisão humana (aprovar/rejeitar/corrigir, lote com rede de segurança)
5. Catálogo (consultas, filtros, histórico de preço)
6. Orçamento (composição, compatibilidade, totais)
7. Congelamento de preço (RN-16 — `frozen_unit_price` imutável)
8. Múltiplas versões de tabela (`vigente`/`substituida`/`arquivada`,
   `VERSOES_DE_TABELA_MISTAS`)
9. Dados inconsistentes (preços fora da faixa esperada, conflitos)
10. PDFs com linhas quebradas (gabarito `extracao-amostra.json`, marcado
    `slow`)
11. SKU duplicado (códigos compartilhados entre variantes — não é erro)
12. Preço ausente (`ITEM_SEM_PRECO`, bloqueio na montagem de orçamento)
13. Acabamento ausente/não reconhecido (`finish_group = NULL`, cadastro de
    novo acabamento)
14. Componente incompatível com dimensão (ex. "Bi-Partido" só existe para
    certas larguras)

Cada categoria referencia IDs específicos de
`docs/samples/fixtures-orcamento.json` (price_tables, component_variants,
extracted_items_samples, import_warnings_samples, quote_scenarios) e regras
RN correspondentes.

### 12.3 Critérios mínimos de qualidade do MVP (`docs/08`, seção 3)

- **Cobertura funcional**: todos os ~22 códigos de erro nomeados cobertos por
  pelo menos um teste.
- **Integridade de dados**: RN-16, RN-12, RN-13, RN-15 e `PRAGMA
  foreign_key_check` testados explicitamente.
- **Honestidade sobre incerteza**: itens de baixa confiança e avisos nunca são
  "escondidos" — testes verificam que aparecem na fila e na auditoria.
- **Qualidade da execução da suíte**: testes determinísticos, isolados (DB
  temporário por teste), `slow` marcado para o gabarito de PDF.
- **Auditabilidade**: cadeia completa
  `quote_item_components → ... → imported_files` testada de ponta a ponta em
  pelo menos um cenário E2E.

### 12.4 Fora de escopo de testes

Carga/performance, E2E de UI, autenticação/papéis detalhada, desconto/margem
(pendente de definição de regra).

---

## 13. Estratégia de implantação

(`docs/09`, completo)

- **Pré-requisitos**: Python 3.11+, Node 20 LTS+, npm, SQLite 3.35+, Git;
  Docker opcional.
- **Variáveis de ambiente** principais (backend): `APP_ENV`, `DATABASE_PATH`,
  `UPLOADS_DIR`, `MAX_UPLOAD_SIZE_MB`, `SECRET_KEY`, `SESSION_COOKIE_SECURE`,
  `LOG_LEVEL`, `LOG_DIR`, `CORS_ALLOWED_ORIGINS`, `BACKUP_DIR`; (frontend):
  `VITE_API_BASE_URL`. Convenção `.env.example` em ambos os diretórios.
- **Banco**: inicializado via migrations numeradas (`0001_initial.sql` =
  `docs/schema/schema.sql`), aplicadas automaticamente no startup, com tabela
  `schema_migrations` para idempotência. Seed de dados de referência (Fase 1)
  via comando dedicado.
- **Diretórios não versionados**: `backend/data/` (SQLite), `backend/data/
  uploads/` (PDFs com nome hash, nunca limpos automaticamente),
  `backend/logs/`.
- **Dev**: `uvicorn --reload` + `npm run dev`; testes via `pytest -m "not
  slow"` (gabarito de PDF é `slow`).
- **Produção**: build do frontend (`npm run build`), `uvicorn` com workers
  (atenção: SQLite tem concorrência limitada — preferir 1 worker ou
  coordenar acesso), supervisor opcional. Docker Compose disponível como
  exemplo opcional.
- **Backup**: `scripts/backup.sh` (Online Backup API / `sqlite3 .backup`),
  cobre banco + uploads, frequência diária + manual antes de operações
  sensíveis (ex. publicação de tabela), retenção 14 dias + mensal,
  armazenamento fora do disco da aplicação, verificação periódica de
  integridade.
- **Restauração**: `scripts/restore.sh`, com cópia de segurança do estado
  atual antes de restaurar, checagem de integridade pós-restauração.
- **Logs**: console em dev, arquivo rotacionado em produção, correlação por
  `request_id`, política de retenção, lista de dados que **nunca** devem ser
  logados.
- **Atualização**: backup → `git pull` → deps backend + migrations → build
  frontend → restart, com checklist pós-atualização e procedimento de
  rollback.
- **Troubleshooting**: tabela com 10 problemas comuns (FK pragma, falha de
  migration, "database is locked", `ARQUIVO_DUPLICADO`,
  `ARQUIVO_MUITO_GRANDE`/`ARQUIVO_INVALIDO`, CORS, depuração de
  `ITEM_SEM_PRECO`, logs ausentes, 500 genérico, falha de integridade na
  restauração).
- **Checklist de deploy** (seção 18 de `docs/09`): referencia diretamente os
  critérios de qualidade de `docs/08` seção 3.

### 13.1 Limitações conhecidas do MVP (`docs/09`, seção 19)

SQLite single-writer/concorrência limitada; processamento assíncrono
in-process sem fila/retry robusto; armazenamento local em disco; autenticação
simples sem SSO/MFA; sem observabilidade externa; sem notificações por
e-mail; backups locais exigem agendamento manual (cron/Task Scheduler);
migrações destrutivas de SQLite são arriscadas e manuais; RN-09/RN-10
(desconto/margem) pendentes; RN-04 (compatibilidade tampo↔estrutura) é
heurística; sem i18n, moeda fixa em BRL.

---

## 14. Ordem recomendada de implementação

(`docs/07`, plano completo de Fase 0 a 12 — princípio: **construir o destino
(catálogo + orçamento) antes da origem (extração de PDF)**)

| Fase | Objetivo | Entrega-chave |
|---|---|---|
| **Fase 0** | Setup do projeto | Estrutura de diretórios, FastAPI/React rodando, CI básico |
| **Fase 1** | Schema + migrations | `schema.sql` (24 tabelas), `PRAGMA foreign_keys = ON`, seed de referência (acabamentos, famílias) |
| **Fase 2** | Catálogo (camada 2) — modelos e API somente-leitura | `product_families`, `products`, `dimensions`, `product_components`, `component_variants`, `finishes`, `skus`, `prices`, `price_tables` + endpoints de consulta (tela 6) |
| **Fase 3** | Catálogo — escrita (CRUD administrativo manual) | Permite popular o catálogo **sem** depender de extração de PDF ainda — desbloqueia testes de orçamento |
| **Fase 4** | Clientes e orçamentos (camada 3) — modelos e API | `customers`, `quotes`, `quote_items`, `quote_item_components`, com **congelamento de preço (RN-16)** |
| **Fase 5** | Regras de negócio do orçamento | Compatibilidade componente×dimensão, filtro de acabamento por componente, bloqueio de item sem preço, `VERSOES_DE_TABELA_MISTAS` |
| **Fase 6** | Frontend — catálogo e orçamento | Telas 6–9 de `docs/04`, usando dados semeados manualmente nas fases 2–3 |
| **Fase 7** | Importação (camada 1) — modelos e upload | `imported_files`, `imported_pages`, upload com validações (hash, tipo, tamanho) — tela 1 |
| **Fase 8** | Extração de PDF | Pipeline pymupdf, `extracted_rows`, `extracted_items`, `extracted_item_source_rows`, validado contra `extracao-amostra.json` |
| **Fase 9** | Fila e tela de revisão | `import_review_decisions`, telas 3–4, correção em lote com pré-visualização |
| **Fase 10** | Publicação no catálogo | Tela 5, operação atômica, diffs e conflitos |
| **Fase 11** | Auditoria de origem | Tela 10, cadeia completa de rastreabilidade |
| **Fase 12** | Operação e hardening | Backup/restore, logging final, troubleshooting, checklist de deploy (`docs/09`) |

> Cada fase em `docs/07` tem critérios de aceite, testes mínimos, riscos e
> "o que não fazer ainda" — consultar o documento original antes de iniciar
> cada fase.

---

## 15. Decisões pendentes

Estas perguntas (originadas em `docs/01`, seção 5, e `docs/05`, seção 4) **não
têm resposta definitiva** e devem ser confirmadas com a área comercial/negócio
antes ou durante as fases correspondentes:

1. **"Produto final" é uma composição ou existe um "kit" fechado?** Leitura
   atual: não existe item fechado — cada componente tem código/preço próprios
   (impacta Fase 4–5).
2. **O que conta como "componente"?** Leitura atual: Tampo, Estrutura (com
   sub-variação por pé/material) e Apoio/Credenza; mesas redondas/lounge e
   conectores STAFF são produtos à parte (impacta Fase 2–3).
3. **Acabamento é único por orçamento ou selecionável por componente?**
   Leitura atual: selecionável por componente, com opções filtradas por tipo
   (tampo = madeirados, estrutura = metálicos) — já refletido em RN e nas
   telas 7–8, mas vale confirmação formal.
4. **Preços importados podem ser editados manualmente após publicação?**
   Definir se o PDF é fonte de verdade somente-leitura ou se há edição pontual
   com rastreabilidade (impacta modelagem de `prices` e auditoria).
5. **Margem, desconto, impostos, frete (RN-09/RN-10)**: nada disso está no
   PDF. Definir se são camada separada do orçamento, regras por
   cliente/região/canal, e se há percentuais/faixas predefinidos — **bloqueia
   a implementação completa do fluxo de orçamento financeiro**, embora não
   bloqueie o MVP de catálogo+composição+congelamento.
6. **Compatibilidade tampo↔estrutura (RN-04)**: confirmar se a heurística por
   dimensão é suficiente ou se há regras adicionais do fabricante.
7. **Terminologia "Acessórios" vs. "Conexão STAFF"** (`docs/01`, seção 6):
   alinhar nomenclatura antes de expor essa entidade na UI/catálogo.
8. **Página 345** (`docs/01`, seção 1): bloco de "Descrição Técnica" não
   detectado na amostragem — confirmar se é exceção real ou erro de
   amostragem antes de usar "tem Descrição Técnica" como heurística de fim de
   seção.
9. **Demais perguntas de `docs/05`, seção 4** (10 questões sobre regras de
   orçamento) — revisar uma a uma antes da Fase 5.
10. **Limite de tamanho de upload e política de retenção de uploads** —
    valores operacionais ainda não fixados (`docs/09`, seção 3 traz exemplos,
    não definitivos).

---

## 16. Riscos técnicos

| Risco | Origem | Mitigação recomendada |
|---|---|---|
| **Quebra de linha do PDF mal reconstruída** | `docs/01` §4 (alta) | Pipeline de extração orientado por coordenadas (Fase 8), validado contra gabarito (`extracao-amostra.json`) antes de qualquer uso em produção |
| **Ambiguidade "Nogueira Cádiz" / nomes de acabamento quebrados** | `docs/01` §4 (alta) | Validação cruzada 9 nomes ⇄ 9 códigos ⇄ 9 preços; vocabulário fechado de `finishes` na revisão |
| **Encoding `U+FFFD` em texto livre** | `docs/01` §4 (alta, mas contornável) | Dicionário de correção de termos de domínio; nunca depender de "decodificação correta" |
| **Códigos duplicados entre seções (9.287)** | `docs/01` §4 (alta — impacta modelo de dados) | Modelo já trata `prices` como tabela fato N:N; reaproveitar `component_variant`/`sku` em vez de duplicar produtos |
| **"Código sem preço" (45 ocorrências, págs. 432–435)** | `docs/01` §4 (alta, localizada) | `extracted_items.unit_price = NULL` + `confidence_level = baixa`; bloqueio explícito na montagem de orçamento (RN-12) |
| **Layout híbrido Bi/Tri-Partido (~4% das linhas)** | `docs/01` §4 (alta) | Marcar como confiança baixa em vez de inferir tipo de componente; revisão manual obrigatória |
| **Concorrência SQLite em produção** | `docs/06` §11, `docs/09` §19 | Limitar workers / coordenar escrita; modelo já compatível com migração futura a PostgreSQL se necessário |
| **Publicação de tabela parcial/inconsistente** | `docs/04` tela 5 | Operação atômica (tudo ou nada), com checagem de conflitos bloqueante antes de confirmar |
| **Sobrescrita silenciosa de decisão humana em correção em lote** | `docs/04` tela 4 | Exclusão automática de itens com `import_review_decisions` prévia + pré-visualização obrigatória |
| **Regras financeiras (margem/desconto/frete) indefinidas** | `docs/05` §4 | Tratar como extensão pós-MVP isolada; não acoplar ao congelamento de preço (RN-16) |
| **Dependência de `data/prices.xlsx` com XML inválido** | `docs/01` §7 | Usar apenas como referência de validação cruzada, com sanitização de XML antes de abrir; nunca como fonte de verdade |

---

## 17. Checklist antes de começar a codar

- [ ] Ler `docs/03-modelagem-sqlite.md` por completo e revisar as 24 tabelas,
      índices e constraints (especialmente seção 7 — perguntas em aberto).
- [ ] Ler `docs/05-regras-orcamento.md` (RN-01 a RN-18) e os 4 exemplos
      completos — eles vão virar testes E2E.
- [ ] Ler `docs/07-plano-implementacao.md` e confirmar que a ordem de fases
      (seção 14 deste documento) faz sentido para a equipe — em particular,
      a decisão de **construir catálogo+orçamento antes da extração de PDF**.
- [ ] Levantar com a área comercial as **decisões pendentes** da seção 15
      deste documento — pelo menos os itens 1–6, que afetam diretamente o
      modelo de dados das Fases 2–5.
- [ ] Confirmar pré-requisitos de ambiente (`docs/09` seção 1): Python 3.11+,
      Node 20 LTS+, SQLite 3.35+.
- [ ] Criar a estrutura de diretórios alvo (seção 6.1 deste documento /
      `docs/06` seção 2 / `docs/09` seção 2), incluindo `.env.example` para
      backend e frontend.
- [ ] Configurar `PRAGMA foreign_keys = ON` desde a primeira conexão SQLite —
      e cobrir isso com teste de schema desde o primeiro commit (`docs/08`
      categoria 1).
- [ ] Definir e aplicar a migration `0001_initial.sql` (= `docs/schema/
      schema.sql`) com o mecanismo de `schema_migrations` (`docs/09` seção 7).
- [ ] Configurar logging estruturado (request/domínio/erro) e o envelope de
      erro padrão **antes** de implementar o primeiro endpoint — todos os
      ~22 códigos de erro nomeados devem nascer cobertos por teste.
- [ ] Configurar `pytest` com marcação `slow` para o teste de gabarito de PDF
      (`docs/samples/extracao-amostra.json`) desde o início.
- [ ] Revisar `docs/samples/fixtures-orcamento.json` e garantir que os
      fixtures de teste (price_tables, component_variants, extracted_items,
      quote_scenarios) estão acessíveis aos testes de integração desde a
      Fase 1.
- [ ] Configurar scripts de backup/restore do SQLite (`docs/09` seções 12–13)
      antes de qualquer dado real ser importado — mesmo em ambiente de
      desenvolvimento, para treinar o procedimento.
- [ ] Alinhar com a equipe os **papéis de usuário** (Importador/Revisor/
      Aprovador/Vendedor/Auditor) e como a autenticação por sessão será
      implementada na Fase 0/1, já que permeia todas as telas de `docs/04`.
