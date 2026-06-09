# Auditoria técnica — `data/source.pdf` (Tabela de Preço de Mesas de Reunião 01-2025)

> Documento gerado a partir de inspeção exploratória do PDF (`pypdf`, leitura por
> coordenadas/Y) e de um arquivo correlato encontrado em `data/prices.xlsx`, que parece ser
> o resultado de uma **tentativa anterior de extração estruturada deste mesmo PDF**
> (ver seção 7). Scripts descartáveis usados: `scripts/spikes/01..10_*.py`.

---

## 1. Estrutura geral do PDF

**Metadados do arquivo**: `Title = "TABELA DE PRECO 01-2025_REUNIÕES.xlsx"`,
`Producer = GPL Ghostscript 8.15`, `Author = Micro23`. Ou seja: **não é um PDF escaneado** —
é uma planilha Excel impressa em PDF via Ghostscript. Todo o texto está embutido como
texto real (há camada de texto), o que é uma boa notícia para extração (não depende de OCR).

- **Número de páginas**: **435** (exato, não aproximado).
- **Existência de índice**: **sim**, a página 1 é um sumário ("ÍNDICE (TABELA 01-2025) -
  REUNIÕES — MESAS DE REUNIÃO") que mapeia faixas de página a seções.
- **Principais seções (conforme o índice da pág. 1)**:

  | Seção | Páginas |
  |---|---|
  | Tampo + Estruturas Reunião + Estrutura Apoio — **profundidade 900mm** | 02–44 |
  | ... 1000mm | 45–87 |
  | ... 1100mm | 88–130 |
  | ... 1200mm | 131–173 |
  | ... 1300mm | 174–216 |
  | ... 1400mm | 217–259 |
  | ... 1500mm | 260–302 |
  | ... 1600mm | 303–345 |
  | ... 1700mm | 346–388 |
  | ... 1800mm | 389–432 |
  | Reuniões Redonda – Lounge – Componível | 432–435 |
  | Acessórios Reuniões | 435 |

  Note que a última faixa de profundidade (1800mm) e a seção "Redonda/Lounge/Componível"
  **se sobrepõem na página 432** — o índice já não é 100% preciso quanto aos limites exatos
  de página (risco a considerar, ver seção 4).

- **Padrão de repetição das páginas**: extremamente regular.
  - 430 das 435 páginas (≈ 99%) repetem **o mesmo cabeçalho de página**:
    `"TAMPOS + ESTRUTURAS REUNIÕES + ESTRUTURA APOIO"` + aviso
    `"*imagens meramente ilustrativas."` + a mesma linha de cabeçalho de colunas
    `"MODELO DESCRIÇÃO ARGILA BRANCO PRETO GIANDUIA AMENDOA CARVALHO NOGUEIRA / CADIZ
    GRAFITE ITAPUA"`.
  - As 4 últimas páginas (432–435) trocam o cabeçalho para `"REUNIÕES"`, mas mantêm a
    mesma linha de colunas `"MODELO DESCRIÇÃO <acabamentos>"`.
  - Cada bloco de "profundidade" tem **43 páginas** e cobre as larguras de mesa de
    1200mm a 5400mm em passos de 100mm (≈ 33 larguras). A última (ou penúltima) página
    da maioria dos blocos (44, 87, 130, 173, 216, 259, 302, 388, 431) contém uma seção
    textual livre `"DESCRIÇÃO TÉCNICA:"` com informações de material/acabamento — a
    única "fuga" relevante do padrão tabular dentro de cada bloco. **Atenção**: a página
    345 (fim do bloco de 1600mm, faixa 303–345) **não** apresentou esse bloco na
    amostragem — ou o texto está deslocado para outra página, ou o padrão não é 100%
    uniforme; vale conferir página a página antes de usar "tem Descrição Técnica" como
    heurística de fim-de-seção.
  - Dentro de cada largura, o padrão de blocos é: **Tampo Inteiro** (Simples/Encabeçado,
    variando "Caixa de Tomada" Fosco/Preto/Branco/Brilhante) → **Estruturas Reunião 5050**
    (variações de pé: Aço 5050, Painel, Alum Atto Fosco/Preto/Branco/Brilhante, Painel
    Diret) → **Apoio Credenza 5050**. A partir de larguras maiores (~2300mm), o "Tampo
    Inteiro" é substituído por **"Tampo Bi-Partido"**/**"Tampo Tri-Partido"**, com layout de
    linha **diferente** (ver seção 4 — "Variações por página").

- **Exemplos de categorias identificadas** (nomes literais encontrados no texto):
  `TAMPOS`, `ESTRUTURAS REUNIÃO 5050`, `APOIO CREDENZA 5050`, `REUNIÕES REDONDA`,
  `REUNIÃO LOUNGE`, `REUNIÃO STAFF` / `CONEXÃO STAFF` (seção tratada como "componível"/
  "acessórios" pelo índice), e a macro-categoria única do documento inteiro: **"Reuniões"**
  (mesas de reunião — não há outras famílias de produto neste arquivo).

---

## 2. Entidades de negócio identificadas

| Entidade | Onde aparece / exemplo concreto no PDF |
|---|---|
| **Linha/família** | "Mesas de Reunião" — única família coberta pelo documento inteiro (campo `categoria` só assume o valor "Reuniões" em toda a extração de referência). |
| **Produto base** | Combinação largura × profundidade que ancora um bloco de linhas, ex.: `"Reunião 1200x900"`, `"Reunião 5400x1800"`. É o que mais se aproxima de um "modelo" no sentido comercial. |
| **Componente vendável** | Cada linha de tabela é, na prática, um item com código e preço próprios: `"Tampo Inteiro Simples"`, `"Tampo Inteiro Encabeçado"`, `"Tampo Bi-Partido Simples"`, `"Estrutura Reunião Tampo Inteiro"`, `"Estrutura Apoio Credenza"`, `"Reunião Redonda ... Lounge Baixa"`, `"Conexão STAFF"`. |
| **Dimensão** | Aparece de 3 formas: (a) embutida no "MODELO" — `"Reunião 1200x900"`; (b) isolada em texto — `"1200x900"`, `"900MM"`, `"Diam 1350mm"`; (c) em 3 eixos para conectores — `"1500 x 600 x 740 mm"` (L × P × A). |
| **Acabamento/cor** | Duas famílias de acabamento coexistem na mesma tabela: (1) 9 acabamentos "madeirados" para tampos — `Argila, Branco, Preto, Gianduia, Amêndoa, Carvalho, Nogueira Cádiz, Grafite, Itapuã`; (2) 3 acabamentos metálicos para estruturas de aço — `Prata, Preto, Branco`; e ainda variações de material/acabamento do **pé** da estrutura (`Aço 5050`, `Painel`, `Alum Atto Fosco/Polido/Preto/Branco/Brilhante`, `Painel Diret`). |
| **Código/SKU** | Sequências numéricas de 10 dígitos, ex.: `3981113028`, `398250001`, `3982510074`. Aparecem em blocos de 9 valores alinhados às 9 colunas de acabamento. |
| **Preço** | Números decimais em formato BR (vírgula decimal), ex.: `382,75`; também em blocos de 9 valores, na linha imediatamente abaixo dos códigos, na mesma ordem das colunas de acabamento. |
| **Observação/regra** | Texto livre intercalado com os dados: `"Para Estrutura Reunião"`, `"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"`, `"*imagens meramente ilustrativas."`, e blocos `"DESCRIÇÃO TÉCNICA: Tampo: Em MDP liso e madeirado..."` ao final de cada seção de profundidade. |
| **Acessório** | Seção final (pág. 435) — `"Conexão STAFF Componível Mod. Angular/Retangular/Trapezoidal"` — peças de conexão entre módulos, indexadas como "Acessórios Reuniões". |
| **Estrutura** | `"Estrutura Reunião Tampo Inteiro"` / `"Estrutura Reunião Tampo Tri-Partido"`, com variações de pé (material/cor) que mudam o código e o preço, mas não a "DESCRIÇÃO" base. |
| **Apoio** | `"Estrutura Apoio Credenza 5050"` — um item de suporte/aparador vendido com código e preço próprios, acompanhando a mesma largura da mesa principal. |

---

## 3. Hipóteses sobre a estrutura da tabela

1. **Quais colunas representam acabamentos**: a linha de cabeçalho repetida em quase
   toda página lista, após `"MODELO DESCRIÇÃO"`, uma sequência de **9 nomes** que se
   estendem por duas linhas de texto (`"... CARVALHO NOGUEIRA"` seguido por `"CADIZ
   GRAFITE ITAPUA"` na linha seguinte). A extração de referência (seção 7) já resolveu
   essa quebra como **um único nome composto "Nogueira Cádiz"** — e isso bate
   exatamente: 9 nomes de cabeçalho ⇄ 9 códigos ⇄ 9 preços por linha de produto. Cada
   coluna de acabamento, portanto, define **um par (código, preço)** por linha de
   produto. Para os blocos `ESTRUTURAS`/`APOIO`, o conjunto de acabamentos muda para
   apenas 3 (`Prata, Preto, Branco`), e o número de pares cai de 9 para 3.

2. **Quais valores representam códigos**: strings numéricas de **10 dígitos** (às vezes
   9, em itens de estrutura — ex. `398250001`), sempre aparecendo **em blocos
   consecutivos de N valores** (N = 9 para tampos, N = 3 para estruturas/apoio em aço),
   na mesma linha de texto que o nome do componente (`"Tampo Inteiro Simples 3981113028
   3981113029 ..."`).

3. **Quais valores representam preços**: números decimais com **vírgula como separador
   decimal** (`"382,75"`, `"2.095,46"` em valores maiores aparecem sem separador de
   milhar consistente — checar amostras grandes), sempre em **blocos de N valores**
   alinhados 1:1 com o bloco de códigos da mesma linha lógica de produto, porém
   **na linha de texto seguinte/abaixo** (e não na mesma linha do código).

4. **Como uma linha textual se relaciona com múltiplos SKUs e múltiplos preços**: cada
   "linha lógica de produto" no PDF não é uma única linha de texto, mas um **bloco
   vertical de 2 a 5 linhas de texto** que tipicamente contém, nesta ordem:
   1. nome do componente + bloco de N códigos (ex.: `"Tampo Inteiro Simples 3981113028
      ... 3981149472"`);
   2. uma ou mais linhas de **observação/contexto** (ex.: `"Para Estrutura Reunião"`,
      `"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"`);
   3. variante/cor do componente + bloco de N preços (ex.: `"Caixa de Tomada Fosco
      382,75 374,45 ... 493,80"`).

   Ou seja: **1 bloco de texto = 1 combinação (componente × variante) × N acabamentos**,
   cada acabamento contribuindo um par (código, preço) posicional. É essa relação
   posicional — "o k-ésimo código corresponde ao k-ésimo preço, que corresponde ao
   k-ésimo acabamento do cabeçalho" — que sustenta toda a extração.

5. **Como identificar modelo, descrição, dimensão e componente**:
   - **Modelo** = o primeiro token reconhecível do bloco — nome da família + dimensão
     (`"Reunião 1200x900"`, `"Reunião Redonda"`, `"Reunião STAFF"`).
   - **Componente** = identificável por palavras-chave fixas que se repetem em todo o
     documento: `Tampo` (tampo/topo), `Estrutura` (base/estrutura), `Apoio`/`Credenza`
     (apoio), `Conexão` (acessório de ligação). Esse vocabulário controlado é a âncora
     mais confiável para classificação automática.
   - **Dimensão** = token no formato `NNNNxNNNN` (ex. `1200x900`) ou `Diam NNNNmm`
     (mesas redondas) ou `NNNN x NNNN x NNNN mm` (conectores STAFF, 3 eixos).
   - **Descrição** = o restante do texto do bloco que não é modelo, dimensão, código,
     preço ou observação reconhecida — texto livre de "cauda longa" que precisa ser
     remontado a partir de várias linhas físicas.

---

## 4. Riscos de interpretação (com evidências concretas encontradas)

| Risco | Evidência encontrada | Severidade |
|---|---|---|
| **Quebras de linha** | Uma "linha lógica de produto" é sempre fragmentada em 3–5 linhas físicas de texto (nome+códigos / observação / variante+preços). Sem reconstrução por coordenada Y, a extração de texto simples embaralha tudo numa sopa só. | **Alta** |
| **Cabeçalhos repetidos** | A linha `"MODELO DESCRIÇÃO ARGILA BRANCO PRETO ... ITAPUA"` se repete em ~430 páginas — precisa ser detectada e descartada (ou usada como referência de ordem de colunas) e não tratada como linha de produto. | Média (fácil de detectar, mas onipresente) |
| **Células mescladas / quebra de cabeçalho em 2 linhas** | O nome de acabamento `"Nogueira Cádiz"` é impresso partido em duas linhas físicas (`"... CARVALHO NOGUEIRA"` / `"CADIZ GRAFITE ITAPUA"`), sugerindo célula com texto quebrado (wrap) — fácil de interpretar como **dois** acabamentos distintos quando na verdade é **um só**. Confirmamos isso cruzando contagem de nomes do cabeçalho (9, se "Nogueira Cádiz" for um só) com o número de códigos/preços por linha (sempre 9). | **Alta** (gera ambiguidade sistemática se não detectada) |
| **Texto vertical ou lateral** | Não detectado nas páginas amostradas (é um PDF gerado digitalmente a partir de planilha, sem rotação aparente). Risco **baixo**, mas vale checar páginas com imagens ilustrativas, caso existam blocos de imagem com texto embutido em outra orientação. | Baixa (a confirmar por amostragem) |
| **Observações misturadas com dados** | Frases inteiras aparecem **dentro** do fluxo de dados, na mesma região onde se esperaria só números: `"Para Estrutura Reunião"`, `"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"`, `"*imagens meramente ilustrativas."`. Um parser ingênuo por regex pode capturar pedaços dessas frases como parte da descrição do componente seguinte. | **Alta** |
| **Preços sem código / código sem preço** | Uma extração de referência já catalogou **45 ocorrências** do tipo `"código_sem_preço"`, **100% concentradas nas páginas 432–435** (seções Redonda/Lounge/Componível/STAFF) — exatamente a região onde o layout de linha muda (ver linha abaixo). Ex.: linhas `"Reunião Redonda"` e `"Conexão STAFF"` cujo bloco de preço não foi pareado automaticamente. | **Alta**, porém **localizada** (4 páginas de 435) |
| **Variações por página / por seção** | Identificamos pelo menos **três layouts de linha distintos** dentro do mesmo documento: <br>(1) larguras "padrão" (1200–2200mm aprox.) usam **"Tampo Inteiro"**, com o padrão de 3 linhas descrito na seção 3; <br>(2) larguras grandes (≥ 2300mm) usam **"Tampo Bi-Partido"/"Tampo Tri-Partido"**, cujas linhas de texto vêm com nome+códigos numa linha e só números soltos (sem rótulo de variante) na linha de preço — uma extração de referência classificou **2.899 linhas / ~322 combinações de modelo** (≈ 4% da base) num grupo "híbrido" `TAMPOS / ESTRUTURAS / APOIO` por não conseguir decidir o tipo de componente, espalhadas por **~250 páginas** de todas as 10 seções de profundidade; <br>(3) páginas 432–435 (redondas/lounge/componível/STAFF) usam um layout de uma linha por variante, com cabeçalho `"REUNIÕES"` (não `"TAMPOS + ESTRUTURAS..."`) e dimensão como `"900MM"`/`"Diam 1350mm"`/`"1500 x 600 x 740 mm"`. | **Alta** |
| **Componentes repetidos com mesmo código entre seções de profundidade** | Encontramos **9.287 códigos** (de ~60 mil distintos) que aparecem em **2 ou 3 seções de profundidade diferentes com o mesmo preço** — ex. o código `3982528494` aparece rotulado como pertencente a `"Reunião 1200x900"` (pág. 2), `"Reunião 1200x1000"` (pág. 45) e `"Reunião 1200x1100"` (pág. 88), sempre custando `R$ 397,57`. Isso sugere que **a "Estrutura"/"Apoio" não muda com a profundidade da mesa** — o mesmo componente físico é reimpresso em cada bloco de profundidade. Uma extração ingênua criaria 2-3 "produtos" diferentes para o que é fisicamente **o mesmo componente vendável**. | **Alta** (impacta diretamente o modelo de dados/catálogo) |
| **OCR ruim ou extração desalinhada** | **Não há problema de OCR** (o texto é nativo/embutido, gerado via Ghostscript a partir de Excel — confirmado pelos metadados e pela presença de uma camada de texto legível). Existe, porém, um **problema de mapeamento de glifos/encoding**: todo caractere acentuado (ã, õ, ç, á, ê, é...) é extraído como `U+FFFD` ("�") pelo `pypdf` — ex. `"REUNI�ES"` em vez de `"REUNIÕES"`, em **100% das páginas**. Esse problema persiste até na extração de referência da seção 7 (ela preservou os mesmos `�`). Isso não impede a extração de números/códigos, mas exige normalização de texto livre (descrições, observações, nomes de acabamento) — provavelmente via dicionário de correção de termos do domínio (lista finita e conhecida: nomes de acabamento, "Reunião", "Estrutura", "Caixa de Tomada" etc.) em vez de depender de decodificação Unicode "correta". | **Alta**, mas **contornável** com dicionário de termos |

---

## 5. Decisões que precisam ser validadas com você

Antes de desenhar telas, banco de dados ou API, preciso que você decida (ou confirme
minha leitura) sobre os seguintes pontos — eles mudam fundamentalmente o modelo de dados:

1. **O que deve ser considerado "produto final"?**
   A tabela não vende "uma mesa pronta": ela precifica **separadamente** o tampo, a
   estrutura e o apoio/credenza para cada combinação de largura × profundidade. Um
   "produto final" no orçamento seria a composição escolhida pelo cliente
   (tampo + estrutura [+ apoio opcional]), ou existe (em algum lugar não capturado por
   esta amostra) um "código de kit" que já agrega os três? Minha leitura inicial é que
   **não existe item fechado** — cada componente tem seu próprio código/preço — mas
   gostaria de confirmar isso com você (ou com alguém da área comercial).

2. **O que deve ser considerado "componente"?**
   Pela estrutura observada, os candidatos naturais a "componente" são: **Tampo**,
   **Estrutura** (com sub-variação por tipo de pé/material) e **Apoio/Credenza**. Mesas
   redondas/lounge e os conectores STAFF parecem ser **produtos à parte** (vendidos como
   unidade única, sem composição tampo+estrutura separada). Confirma essa divisão?

3. **O orçamento será por composição de componentes ou por item fechado?**
   Decorre diretamente da pergunta 1. Se for composição, o sistema precisa somar
   preços de componentes compatíveis (mesma largura/profundidade); se for item fechado,
   seria necessário definir manualmente quais combinações formam "kits" vendáveis —
   o que a tabela, sozinha, não define.

4. **O acabamento deve ser único para todos os componentes do orçamento, ou
   selecionável por componente?**
   Achei evidências de que **o catálogo permite combinações diferentes**: o tampo tem
   9 opções de acabamento "madeirado", mas a estrutura de aço só tem 3 opções metálicas
   (`Prata/Preto/Branco`) — fisicamente não é possível pedir uma estrutura "Carvalho".
   Isso sugere que o seletor de acabamento deveria ser **por componente, com opções
   filtradas pelo tipo de componente** — mas pode haver uma regra de negócio (ex.: "o
   cliente sempre escolhe um acabamento principal e o sistema mapeia para a opção
   metálica mais próxima") que só você conhece.

5. **Os preços importados poderão ser editados manualmente?**
   A tabela tem nome ("Tabela 01-2025") e data de geração — sugerindo que é uma
   referência **versionada e datada**, sujeita a reajuste periódico. Preciso saber se o
   sistema deve (a) tratar o PDF como fonte de verdade somente-leitura, recarregada a
   cada nova versão da tabela, ou (b) permitir edição manual pontual (ex. para
   negociações específicas) sem perder rastreabilidade da origem.

6. **Haverá margem, desconto, impostos ou frete?**
   **Nada disso aparece no PDF** — ele contém apenas preços de tabela "secos". Preciso
   saber se essas variáveis (a) serão aplicadas em uma camada separada do orçamento,
   (b) têm regras de negócio específicas por cliente/região/canal, e (c) se há percentuais
   ou faixas predefinidas que devo conhecer antes de desenhar o cálculo do orçamento.

---

## 6. Observação sobre o índice vs. conteúdo real

O índice da página 1 rotula a última seção como **"Acessórios Reuniões — pág. 435"**,
mas o conteúdo real da página 435 é, na verdade, a família **"Reunião STAFF"/"Conexão
STAFF"** (mesas e conectores componíveis com pé de aço 5050), além do bloco de
"Descrição Técnica" final. Ou seja, **o termo "acessório" no índice não corresponde a um
catálogo de acessórios genéricos** (parafusos, calhas, etc.), e sim a peças de conexão
entre módulos de um sistema componível. Vale alinhar a terminologia com você antes de
nomear essa entidade no sistema.

---

## 7. Achado relevante: já existe uma tentativa de extração estruturada (`data/prices.xlsx`)

Durante a auditoria, encontrei `data/prices.xlsx` na mesma pasta do PDF. Ele **não é a
planilha original que gerou o PDF** — é, pelas evidências internas, **o resultado de uma
extração automatizada anterior deste mesmo documento** (435 páginas detectadas, mesmo
domínio "Reuniões", mesmos códigos/preços, mesmos artefatos de encoding `�`):

- **Metadados (`aba meta`)**: `arquivo_origem = pdf-precos.pdf` (nome de arquivo
  diferente do nosso `source.pdf`, mas com 435 páginas — quase certamente o mesmo
  documento renomeado), `gerado_em = 2026-05-08`, `registros_produtos_mcp = 72.137`,
  `issues_extracao = 45`, e a observação **"Extração feita por coordenadas e texto
  embutido do PDF; não dependeu de OCR"** — o que confirma de forma independente nossa
  leitura de que este é um PDF "de texto", não escaneado.
- **Schema proposto pela extração anterior** (aba `produtos_mcp`, 72.137 linhas — uma
  linha por combinação componente×acabamento×preço): `record_id, categoria, grupo,
  modelo_base, dimensao, descricao_comercial, acabamento, codigo_produto, preco_tabela,
  moeda, tabela_preco, fonte_pdf, pagina_pdf, confianca_extracao, observacoes_mcp`.
  Esse vocabulário é um ótimo ponto de partida (e validação cruzada) para o nosso
  próprio modelo de domínio — vale revisar com cuidado, não adotar cegamente.
- **Aba `issues_extracao`**: lista as 45 linhas problemáticas citadas na seção 4
  (todas tipo `codigo_sem_preco`, todas nas páginas 432–435).
- **Aba `raw_rows`** (38.695 linhas — texto agrupado por página/coordenada Y): é um log
  de auditoria valioso para entender *como* o texto chega bruto do PDF (inclusive
  evidenciando, na própria página 1/índice, blocos de texto totalmente ilegíveis —
  prováveis glifos decorativos/símbolos do template Excel original que viraram lixo
  binário na extração).
- **Limitações observadas nesse arquivo** (a não herdar sem revisão):
  - Mesmo problema de encoding (`Reuni�o`, `�NDICE`) em 100% dos textos livres;
  - Grupo "guarda-chuva" `TAMPOS / ESTRUTURAS / APOIO` usado em 2.899 linhas (≈ 4%) —
    sinal de que o classificador automático não conseguiu decidir o tipo de componente
    nessas linhas (concentradas nas variantes "Bi/Tri-Partido");
  - A aba `raw_rows` (sheet5.xml) contém **caracteres de controle inválidos para XML**
    (bytes de glifos não mapeáveis do PDF), o que quebra leitores XLSX padrão
    (`openpyxl` falha com `ParseError: not well-formed`) — qualquer pipeline que
    consuma esse arquivo precisa sanitizar o XML antes de abrir.

**Recomendação**: tratar `data/prices.xlsx` como **insumo de referência e checagem
cruzada** (ele já fez o trabalho pesado de extração por coordenadas e documentou os
próprios pontos cegos), mas não como fonte de verdade definitiva — vale revalidar uma
amostra por seção/página antes de qualquer uso comercial, como o próprio arquivo
recomenda em `schema_mcp.instrucao_mcp`.

---

## 8. Scripts exploratórios usados (descartáveis)

Em `scripts/spikes/`:
- `01_overview.py` — contagem de páginas, metadados, amostra de texto bruto.
- `02_encoding_and_sections.py` — varredura de cabeçalhos/palavras-chave por página,
  detecção do problema de encoding (`U+FFFD`).
- `03_detail_pages.py` — leitura de páginas especiais (fim de seção "Descrição
  Técnica", seção redonda/lounge/componível).
- `04_check_xlsx_source.py` / `05_xlsx_raw_peek.py` — primeira inspeção do
  `prices.xlsx` (detectou que `openpyxl` falha ao abrir e mapeou as abas via XML cru).
- `06_xlsx_deep_dive.py` — leitura incremental (`iterparse`) do `prices.xlsx`:
  schema, contagens, amostras, estatísticas de acabamento/confiança/grupo.
- `07_xlsx_more.py` / `07b_hybrid_group.py` — investigação do grupo híbrido
  `TAMPOS / ESTRUTURAS / APOIO` (paginas e modelos envolvidos).
- `08_raw_rows_fix.py` — sanitização do XML inválido da aba `raw_rows` e leitura de
  amostra (texto agrupado por coordenada Y — evidência do "bloco vertical" da seção 3).
- `09_xlsx_models_dims.py` — contagem de modelos/dimensões/códigos distintos,
  detecção de códigos duplicados.
- `10_duplicate_codes.py` — confirmação de que códigos duplicados entre seções de
  profundidade têm sempre o mesmo preço (mesmo componente físico reimpresso).
