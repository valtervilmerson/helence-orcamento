# Spike de extração — prova técnica com amostra de 3 páginas

> Amostra escolhida (representativa dos 3 perfis de página identificados na auditoria —
> ver `docs/01-auditoria-pdf-dominio.md`):
> - **Página 1** — índice (texto livre, fora do padrão tabular).
> - **Página 2** — tabela "simples" (`Tampo Inteiro`, layout regular de 9 colunas de
>   acabamento, o padrão que cobre ~96% das páginas).
> - **Página 432** — tabela "complexa" (`Reunião Redonda`, cabeçalho/dimensão diferentes,
>   uma das 4 páginas com casos documentados de "código sem preço").
>
> Scripts descartáveis: `scripts/spikes/11_lib_comparison.py` (comparação das libs) e
> `scripts/spikes/12_vertical_text_check.py` (confirmação de texto rotacionado — achado
> que **revisa para cima** o risco "texto vertical/lateral" apontado no doc 01).

---

## 1. Bibliotecas testadas/avaliadas

| Biblioteca | Testada? | Como rodou | Observações |
|---|---|---|---|
| **pypdf** | ✅ Sim | `reader.pages[i].extract_text()` | Só texto corrido, sem coordenadas nem detecção de tabela. Mais rápida (~0,02s/página). Mantém a ordem de leitura razoavelmente bem, mas embaralha tudo numa "sopa" de texto sem qualquer noção de coluna. |
| **pdfplumber** | ✅ Sim | `page.extract_text()` + `page.extract_tables()` | Detecta "tabelas" por heurística de espaçamento/linhas. Acerta a **estrutura de cabeçalho** (inclusive reconstrói `"NOGUEIRA\nCADIZ"` como uma única célula — confirma programaticamente a hipótese do doc 01!), mas agrupa o corpo da tabela em **mega-células multilinha** que precisam ser reprocessadas — não entrega "uma linha = um produto". ~0,17s/página. |
| **pymupdf (fitz)** | ✅ Sim | `get_text("text"/"words"/"rawdict")` + `page.find_tables()` | Igual ao pdfplumber em `find_tables()` (mesma limitação de mega-células), **mas** expõe `get_text("words")` (tokens com bbox `x0,y0,x1,y1`) e `get_text("rawdict")` (spans com **vetor de direção** `dir=(dx,dy)`). Foi a **única** das quatro que permitiu detectar e isolar texto rotacionado de forma programática (ver seção 2.4). ~0,2s/página com tabelas. |
| **camelot** | ✅ Sim (`camelot-py 2.0.0`, sem Ghostscript externo) | `read_pdf(flavor="stream")` e `flavor="lattice"` | Funciona sem dependências externas no ambiente atual. `stream` (baseado em espaçamento) deu tabelas mais "quebradas por coluna" que pdfplumber/pymupdf em algumas páginas (ex.: separou par código→preço em colunas), mas a segmentação de linhas não acompanha o agrupamento lógico produto↔variante. `lattice` (baseado em linhas/grade) não encontra grade real (o PDF não tem bordas de tabela desenhadas) e devolve poucas linhas com células gigantes. Mais lenta (0,1–0,5s/página/flavor) e adiciona uma dependência pesada (`opencv`, `ghostscript` opcional) para um ganho marginal sobre pymupdf+pós-processamento. |
| **tabula-py** | ❌ Não testada | — | Requer **JVM (Java)**; o ambiente não tem `java` instalado (`command not found`). Mesmo que funcionasse, depende de detecção de grade similar ao `camelot lattice`, que já vimos não se aplicar bem a este PDF (sem linhas de grade desenhadas). Não vale o custo de configurar Java só para confirmar uma limitação já observada em ferramenta similar. |

---

## 2. Resultado da avaliação

### 2.1 Qual biblioteca é mais adequada para o MVP

**`pymupdf` (fitz)**, usada **não** pelo `find_tables()` (que sofre da mesma limitação de
"mega-células" das outras libs), mas pela combinação:

1. `get_text("words")` / `get_text("rawdict")` → tokens e spans **com coordenadas
   `(x0, y0, x1, y1)` e vetor de direção** — exatamente o que a extração de referência
   encontrada em `data/prices.xlsx` descreve ter usado ("extração por coordenadas... não
   dependeu de OCR"), e o que a seção 3 do doc 01 identificou como a relação-chave
   (posição do código ⇄ posição do preço ⇄ posição do acabamento no cabeçalho);
2. acesso ao **vetor de direção do texto** (`dir`), que nenhuma das outras três
   bibliotecas expõe de forma utilizável — crítico para o achado da seção 2.4 abaixo;
3. desempenho competitivo (mais rápida que `pdfplumber`/`camelot` para o mesmo nível de
   detalhe) e **zero dependências externas pesadas** (sem JVM, sem Ghostscript, sem
   OpenCV).

Ou seja: a estratégia vencedora não é "qual lib tem `extract_table()` melhor" — é
**reconstruir as linhas/colunas nós mesmos a partir de coordenadas brutas**
(agrupar por `y` → ordenar por `x` → casar blocos de N códigos com blocos de N preços
pela posição), usando `pymupdf` como provedor dessas coordenadas. Essa é também,
aparentemente, a abordagem que já gerou `data/prices.xlsx` — o que reforça que é o
caminho certo.

### 2.2 Quais dados foram extraídos com boa qualidade

- **Códigos/SKU** (sequências de 9–10 dígitos): extraídos de forma 100% íntegra pelas
  quatro libs — são tokens isolados, sem acentuação, sem ambiguidade de formatação.
- **Preços** (decimais com vírgula, ex. `382,75`): extraídos corretamente na grande
  maioria dos casos; exigem apenas normalização (`,` → `.`,`str` → `float`/`Decimal`).
  ⚠️ Encontramos ao menos um caso de **espaço espúrio dentro do número**
  (`"744 ,22"` na pág. 432 — texto bruto, não erro de digitação) — normalização precisa
  tolerar isso.
- **Cabeçalho de colunas / ordem dos acabamentos**: `pdfplumber.extract_tables()` e
  `pymupdf.find_tables()` reconstroem corretamente a linha de cabeçalho **inclusive a
  célula quebrada `"NOGUEIRA\nCADIZ"`** — uma confirmação independente, por uma
  ferramenta de terceiros, da hipótese "é um nome só" already levantada no doc 01 a
  partir da contagem de colunas.
- **Modelo + dimensão + tipo de componente** (quando em formato `"Reunião 1200x900
  Tampo Inteiro Simples"`): o token de dimensão `NNNNxNNNN` é regular e fácil de
  capturar via regex em qualquer uma das libs baseadas em texto.

### 2.3 Quais dados exigem revisão humana

- **Descrições consolidadas** (`descricao_comercial`): são remontadas a partir de 3–5
  linhas físicas espalhadas (nome do componente + observações soltas tipo `"Para
  Estrutura Reunião"` / `"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"`).
  Qualquer concatenação automática produz texto gramaticalmente estranho — ok para
  busca/indexação, mas precisa de revisão antes de aparecer ao cliente final.
- **Itens das páginas 432–435** (Redonda/Lounge/Componível/STAFF): a extração de
  referência já documentou **45 casos de "código sem preço"** nessas 4 páginas — nosso
  recorte da página 432 caiu exatamente numa das páginas afetadas. Esses pares
  precisam de checagem manual linha a linha contra o PDF original.
- **Linhas classificadas no grupo "híbrido" `TAMPOS / ESTRUTURAS / APOIO`** (≈ 4% da
  base, concentradas nas variantes `Bi-Partido`/`Tri-Partido`): o `component_type` não
  pôde ser determinado com confiança pela extração de referência — exige decisão humana
  de regra de classificação (ou aceite manual item a item).
- **Blocos de "Descrição Técnica"** (texto corrido no fim de cada seção de
  profundidade): não são linhas de produto; são notas de material/acabamento que
  deveriam virar metadados de seção/família, não registros de item — exige curadoria
  para decidir onde "guardar" essa informação.

### 2.4 Quais partes do PDF são frágeis para automação — **achado novo: texto vertical existe, sim**

No doc 01 eu havia classificado "texto vertical ou lateral" como risco **baixo / não
detectado**. A comparação de bibliotecas **revisa essa conclusão**: ao rodar
`pdfplumber.extract_tables()`/`camelot` na página 2, surgiram fragmentos estranhos e
"espelhados" misturados ao texto de células — por exemplo `"OCSOF"`, `"OTERP"`,
`"OCNARB"`, `"ETNAHLIRB"`, `"OIN�MULA"`. Investigando com `pymupdf.get_text("rawdict")`
(único que expõe o vetor de direção do texto), confirmei que são **rótulos verticais
legítimos do PDF, lidos de baixo para cima** (`dir = (0.0, -1.0)`):

| Texto real (vertical, `dir=(0,-1)`) | Como aparece "espelhado" nas libs baseadas em grade |
|---|---|
| `FOSCO` | `OCSOF` |
| `PRETO` | `OTERP` |
| `BRANCO` | `OCNARB` |
| `BRILHANTE` | `ETNAHLIRB` |
| `PÉ ALUMÍNIO` | `OIN�MULA` *(fragmento)* |

**Distribuição**: encontramos exatamente **5 spans verticais por página** nas páginas 2
e 44 (prováveis rótulos ilustrativos ao lado de amostras de cor/acabamento — mesmos 5
nomes nas duas páginas, sugerindo que se repetem em todo o bloco "Tampos+Estruturas").
A página 432 (`REUNIÕES` — redonda/lounge) **não apresentou nenhum span vertical** —
o que é coerente com o template visual diferente dessa seção identificado no doc 01.

**Implicação prática**: bibliotecas que reconstroem "tabelas" por agrupamento
geométrico (pdfplumber `extract_tables`, camelot, pymupdf `find_tables`) **não
respeitam a direção do texto** e podem injetar esses rótulos verticais — corrompidos —
dentro de células de dados reais (vimos isso ocorrer, ex.: `"1200x900 OCSOF"`,
`"Para Estrutura Reunião ETNAHLIRB"`). Um pipeline que dependesse dessas funções de
"tabela pronta" arriscaria poluir descrições e, em casos piores, confundir o
reconhecimento de tokens numéricos. **`pymupdf.get_text("rawdict")` é a única rota das
quatro testadas que permite filtrar esse ruído na origem** (descartando ou tratando à
parte qualquer span com `dir != (1, 0)`).

**Outras partes frágeis confirmadas pela comparação**:
- **Páginas 432–435**: layout de coluna diferente + ausência de rótulos verticais +
  maior incidência de pares código/preço não casados. Tratar como "perfil de página"
  separado, não como variação do perfil padrão.
- **Larguras grandes (`Bi-Partido`/`Tri-Partido`, ≈ 250 páginas)**: linha de
  preço aparece "nua" (sem o nome da variante ao lado), exigindo casamento por posição
  vertical relativa ao bloco de código — mais sensível a ruído (inclusive aos rótulos
  verticais, se existirem nessas páginas — não confirmamos, ficou fora da amostra de 3
  páginas e deve ser checado num spike futuro maior).
- **Acentuação**: `U+FFFD` em 100% das libs/páginas testadas (problema do PDF/fonte, não
  da biblioteca escolhida) — qualquer lib exigirá o mesmo dicionário de correção de
  termos do domínio mencionado no doc 01.

---

## 3. Proposta de JSON intermediário canônico

Arquivo de exemplo (dados **reais**, extraídos manualmente da amostra para provar o
formato): **`docs/samples/extracao-amostra.json`**.

O arquivo é uma **lista de registros por página**, cada um seguindo o formato abaixo
(idêntico ao sugerido no briefing, com pequenos acréscimos justificados a seguir):

```jsonc
{
  "source_file": "data/source.pdf",
  "price_table_version": "01-2025",
  "page_number": 2,
  "section": "TAMPOS + ESTRUTURAS REUNIÕES + ESTRUTURA APOIO",
  "page_profile": "tampo_padrao",          // <- novo: rótulo do "perfil de layout" da página
  "raw_rows": [
    { "y": 775.99, "text": "Reunião 1200x900 Tampo Inteiro Simples 3981113028 ... 3981149472" },
    { "y": 769.76, "text": "Para Estrutura Reunião" },
    { "y": 757.27, "text": "Tampos são centralizadas Caixa de Tomada Fosco 382,75 ... 493,80" }
  ],
  "normalized_items": [
    {
      "family": "Mesas de Reunião",
      "product_context": "Reunião 1200x900",
      "component_type": "tampo",
      "description": "Tampo Inteiro Simples Para Estrutura Reunião 1200x900 Caixa de Tomada Fosco",
      "dimensions": { "width_mm": 1200, "depth_mm": 900 },   // <- estrutura flexível (ver 3.2)
      "finish": "Argila",
      "sku": "3981113028",
      "price": 382.75,
      "currency": "BRL",
      "confidence": 0.95,
      "confidence_level": "alta",                            // <- novo: rótulo legível
      "source_page": 2,
      "source_text": "Reunião 1200x900 Tampo Inteiro Simples 3981113028 ... | Tampos são centralizadas Caixa de Tomada Fosco 382,75 ...",
      "extraction_notes": []                                  // <- novo: trilha de decisões/heurísticas aplicadas
    }
  ],
  "warnings": [
    "Linha 'Para Estrutura Reunião' e 'A Caixa de Tomada nos 1200x900 / Tampos são centralizadas' são observações livres intercaladas com dados — não viraram itens, mas ficam em raw_rows para auditoria."
  ]
}
```

### 3.1 Por que manter `raw_rows`

`raw_rows` é a "rede de segurança" do pipeline: guarda o texto bruto **com a coordenada
Y de origem**, na ordem em que foi lido — exatamente o padrão que a extração de
referência (`data/prices.xlsx`, aba `raw_rows`) já adotou para auditoria, e que se
provou indispensável para *nós* explicarmos, neste mesmo spike, por que um valor saiu
torto. Sem isso, qualquer divergência futura ("por que esse preço está errado?") exigiria
reabrir o PDF do zero. Recomendo manter `raw_rows` mesmo que o pipeline final não
grave esse campo no banco definitivo (pode virar um arquivo de auditoria em paralelo).

### 3.2 Por que `dimensions` como objeto (e não `width_mm`/`depth_mm` soltos)

A amostra das 3 páginas já mostra **3 formatos de dimensão diferentes**:
- retangular `LxP` → `"1200x900"` (maioria das páginas);
- circular `Diâm.` → `"900MM"` / `"Diam 1350mm"` (página 432, mesas redondas);
- tridimensional `LxPxA` → `"1500 x 600 x 740 mm"` (conectores STAFF, pág. 435).

Um par fixo `width_mm`/`depth_mm` obriga a inventar valores (`null`? `0`? duplicar o
diâmetro nos dois eixos?) para os outros dois formatos. Por isso a amostra propõe
`"dimensions": { ... }` como objeto de forma livre por tipo de produto — ex.
`{"diameter_mm": 900}` para mesas redondas e `{"width_mm": 1500, "depth_mm": 600,
"height_mm": 740}` para conectores — preservando no JSON intermediário a forma real do
dado, e deixando para a etapa de modelagem do banco (próximo documento) decidir como
normalizar/armazenar isso de forma consultável.

### 3.3 Campos acrescentados à proposta original (e por quê)

| Campo novo | Motivo |
|---|---|
| `page_profile` | A auditoria (doc 01) e este spike identificaram **pelo menos 3 perfis de layout** (tampo padrão, tampo bi/tri-partido, redonda/lounge/STAFF). Gravar o perfil detectado por página permite (a) escolher a regra de parsing certa, e (b) explicar por que a confiança variou entre páginas "normais" e "frágeis". |
| `confidence_level` | Espelha `confidence` (0–1) num rótulo `alta`/`média`/`baixa` — útil para filtros/relatórios sem repetir os limiares em todo lugar (ver seção 4). |
| `extraction_notes` | Lista curta e estruturada de heurísticas aplicadas a este item específico (ex. `"cabeçalho 'Nogueira/Cadiz' resolvido via dicionário"`, `"preço pareado por proximidade vertical, não por rótulo explícito"`). Sem isso, dois itens com a mesma `confidence` numérica podem ter passado por caminhos de decisão completamente diferentes — e quem revisar precisa saber qual. |

Os demais campos do exemplo do briefing (`family`, `product_context`, `component_type`,
`description`, `finish`, `sku`, `price`, `currency`, `confidence`, `source_page`,
`source_text`, `warnings`) foram mantidos **exatamente como sugeridos** — encaixaram
sem atrito nos dados reais da amostra.

---

## 4. Estratégia de pontuação de confiança

A confiança de cada `normalized_item` é calculada combinando estes sinais (cada item
da amostra em `extracao-amostra.json` traz `extraction_notes` explicando quais sinais
pesaram):

### Alta confiança (`>= 0.85`)
- A página tem um **perfil de layout conhecido e validado** (`page_profile`
  reconhecido nas páginas já auditadas);
- código (`sku`) e preço (`price`) foram pareados **pela mesma posição ordinal** dentro
  de blocos de tamanho esperado (9 para tampos, 3 para estruturas em aço);
- o nome do acabamento bate **exatamente** com a lista de acabamentos conhecida do
  cabeçalho daquela seção (após resolver quebras de célula conhecidas, ex.
  `"Nogueira Cádiz"`);
- os valores numéricos (`sku`, `price`) passam na validação de formato sem
  necessidade de correção heurística (ex. sem espaços internos, sem dígitos faltando).

### Média confiança (`0.5 – 0.84`)
- O pareamento código↔preço foi feito **por proximidade geométrica** (linhas
  consecutivas mais próximas em Y), e não por rótulo textual explícito que os ligue —
  válido, mas dependente de a geometria da página seguir o padrão esperado;
- a `description` foi **remontada por concatenação** de 2+ linhas de observação livre
  (ex. `"Para Estrutura Reunião"` + `"A Caixa de Tomada nos 1200x900..."`) — texto
  correto em conteúdo, mas com formatação que pode soar estranha;
- houve necessidade de **normalização não trivial** de número (ex. remover espaço
  interno em `"744 ,22"` → `744.22`) — correta com alta probabilidade, mas vale
  amostragem;
- a página pertence a um perfil "primo" de um perfil conhecido (ex. variante
  Bi-Partido de uma página que segue majoritariamente o padrão Tampo Inteiro).

### Baixa confiança (`< 0.5`)
- Código encontrado **sem** preço correspondente (ou vice-versa) — caso documentado e
  nomeado (`"código_sem_preço"`) na extração de referência, com 45 ocorrências
  conhecidas concentradas nas páginas 432–435;
- `component_type` definido por **regra de fallback genérica** (ex. grupo guarda-chuva
  `"TAMPOS / ESTRUTURAS / APOIO"`, usado pela extração de referência em ≈ 4% da base
  quando não foi possível decidir o tipo);
- a página **não corresponde a nenhum perfil de layout conhecido/validado**
  (ex. primeira vez que o pipeline encontra um padrão fora do catálogo de perfis);
- qualquer sinal de **corrupção de texto** no trecho relevante — incluindo, a partir de
  agora, fragmentos de **texto vertical mal interpretado** (ver seção 2.4: strings como
  `"OCSOF"`/`"ETNAHLIRB"` dentro de uma célula de dados são um sinalizador forte de
  ruído geométrico, não de erro de OCR).

### Quando exigir revisão humana obrigatória (independente do score)
Revisão **obrigatória**, e o item **não deve ser publicado** sem aprovação manual,
quando:
1. `price` ou `sku` vier `null`/vazio (par incompleto);
2. `confidence < 0.5` (baixa confiança, por definição);
3. o item pertencer a uma das **páginas/seções já cadastradas como frágeis**
   (432–435; variantes Bi/Tri-Partido; qualquer página cujo `page_profile` seja
   `"desconhecido"`);
4. `extraction_notes` contiver qualquer heurística marcada como **não determinística**
   (ex. "pareado por proximidade", "classificação por fallback", "texto remontado de
   N fragmentos com N > 2");
5. o `warnings` da página não estiver vazio **e** mencionar o item em questão.

Esse modelo é deliberadamente **conservador**: prefere marcar itens corretos como
"revisar" a publicar um item errado sem aviso — dado que o resultado alimenta um
orçamento comercial (custo de um erro de preço é alto).

---

## 5. Limites conhecidos da extração

1. **Acentuação/encoding**: `U+FFFD` substitui todo caractere acentuado, em 100% das
   páginas e em todas as bibliotecas testadas — é uma característica do PDF/fonte
   embutida, não da ferramenta. Mitigação viável: dicionário de correção para o
   vocabulário fechado do domínio (nomes de família, componente, acabamento, palavras
   recorrentes como "Reunião", "Estrutura", "Caixa de Tomada"); não vale tentar
   "decodificar corretamente" via mapas de Unicode genéricos.
2. **Texto vertical/rotacionado real existe** (achado novo desta etapa — revisa o doc
   01): pelo menos 5 rótulos verticais por página no perfil "Tampo padrão" (`FOSCO`,
   `PRETO`, `BRANCO`, `BRILHANTE`, `PÉ ALUMÍNIO`), ausentes no perfil "Redonda/Lounge".
   Pipelines baseados em extração de "tabela pronta" os capturam invertidos e
   misturados a células de dados — precisa filtrar por vetor de direção
   (`dir == (1, 0)`) antes de qualquer reconstrução de linha/coluna.
3. **Layouts múltiplos no mesmo arquivo**: identificamos ao menos 3 perfis de página
   (Tampo padrão / Tampo Bi-Tri-Partido / Redonda-Lounge-STAFF), cada um exigindo
   regras de parsing próprias. Um parser único e genérico tende a "funcionar bem" no
   perfil mais comum e falhar silenciosamente nos outros — daí a importância de
   detectar e rotular o perfil **antes** de extrair os itens.
4. **Pareamento código↔preço nem sempre é garantido**: a extração de referência
   documentou 45 casos de "código sem preço" — todos nas páginas 432–435 — confirmando
   que o pareamento por proximidade geométrica (a única estratégia viável neste PDF,
   já que não há rótulos textuais ligando código a preço) tem uma taxa de falha
   conhecida, ainda que pequena (45 em ~72 mil registros ≈ 0,06%) e localizada.
5. **Blocos de texto livre fora do escopo tabular** (`"DESCRIÇÃO TÉCNICA:"`, avisos de
   rodapé, índice) precisam de tratamento **separado** do pipeline de itens — não cabem
   no formato `normalized_items` e não devem ser forçados nele.
6. **Esta prova usou apenas 3 das 435 páginas**: suficiente para validar o formato do
   JSON intermediário e a viabilidade da estratégia (extração posicional via
   `pymupdf` + reconstrução manual de linha/coluna), mas **não** é representativa o
   bastante para calibrar os limiares numéricos de confiança da seção 4 — isso exigirá
   rodar o pipeline-piloto numa amostra maior (sugiro: 2 páginas de cada um dos 3
   perfis identificados, mais as 4 páginas 432–435 completas) antes de congelar os
   limiares definitivos.
