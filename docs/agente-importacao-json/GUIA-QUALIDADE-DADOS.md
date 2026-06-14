# Guia de qualidade de dados para geração do JSON de importação

Este guia reúne problemas **reais** já encontrados ao gerar e importar
JSONs para o Helence Orçamento, e como evitá-los. Leia junto com
`CONTRATO.md` (formato) e `catalogo-atual.json` (o que já existe
cadastrado).

---

## 1. Encoding — nunca propague "versões corrompidas" de palavras

**O que pode dar errado**: planilhas antigas, PDFs convertidos ou
copy/paste entre programas podem introduzir caracteres de substituição
(`�`, código `U+FFFD`) no lugar de letras acentuadas. Isso já aconteceu
no histórico do projeto (extração de PDF) e gerou nomes de acabamento
como `Am�ndoa` em vez de `Amêndoa`/`Amendoa`.

Um item com `finish` corrompido **não dá erro na importação** — ele só
falha **na hora de publicar**, com `ACABAMENTO_NAO_CADASTRADO`, porque o
nome corrompido nunca vai casar com nada no catálogo. Isso é difícil de
depurar depois, então é melhor prevenir na geração do JSON.

**O que fazer**:
- Gere o JSON sempre em **UTF-8** (sem BOM).
- Antes de entregar, verifique se NENHUMA string do JSON contém o
  caractere `U+FFFD` (`�`). Em Python:
  ```python
  import json
  data = json.load(open("import.json", encoding="utf-8"))
  def check(obj, path=""):
      if isinstance(obj, str):
          if "�" in obj:
              print("CORROMPIDO:", path, repr(obj))
      elif isinstance(obj, dict):
          for k, v in obj.items():
              check(v, f"{path}.{k}")
      elif isinstance(obj, list):
          for i, v in enumerate(obj):
              check(v, f"{path}[{i}]")
  check(data)
  ```
- Se a planilha de origem já tiver texto com `�`, **não invente** a
  grafia correta sem confirmar — prefira:
  - usar o nome de uma entidade equivalente já existente em
    `catalogo-atual.json` (ex.: "Amendoa" sem acento, se for esse o
    padrão já cadastrado), ou
  - deixar o item em `notes` explicando a ambiguidade, para revisão
    humana, em vez de gerar um nome novo possivelmente errado.

**Atenção ao "falso positivo" do terminal**: ao inspecionar strings no
terminal do Windows, caracteres acentuados corretos (á, ã, ç, õ, ú etc.)
podem **aparecer** como `�` por causa da code page do console (cp1252),
mesmo estando corretos em UTF-8. Não conclua que há corrupção só pela
aparência no terminal — confirme com o código Python acima (`�`
real) ou inspecionando os code points (`ord(c)`).

---

## 2. `finish` — o nome precisa casar EXATAMENTE com o catálogo

**Regra**: o backend procura o acabamento por **igualdade de string
exata** (`finishes.name = ?`). Isso é sensível a:
- acentuação (`Itapuã` ≠ `Itapua`)
- maiúsculas/minúsculas (`Branco` ≠ `branco`)
- espaços extras no início/fim ou duplicados no meio

**O que fazer**:
- Antes de escrever o `finish` de um item, procure o valor em
  `catalogo-atual.json` → `finishes[].name`. Se existir um nome
  equivalente, **copie-o exatamente como está lá** — não "normalize"
  para outra grafia.
- Se o acabamento realmente não existe ainda:
  - use um nome novo claro e sem acentos problemáticos/ambíguos,
  - informe `finish_group` (obrigatório), com um dos valores:
    `madeirado`, `metalico`, `pe_estrutura`, `outro`,
  - isso fará o item cair em revisão (não fast path) — é esperado.
    A tabela só poderá ser **publicada** depois que alguém cadastrar
    esse acabamento em `/catalog/finishes` com o `finish_group`
    informado.
- **Caso "sem acabamento aplicável"**: alguns componentes (placas
  acústicas, mosaicos etc.) não têm acabamento. Use o valor padrão já
  adotado no projeto: `"Sem acabamento aplicável"` (com `finish_group:
  "outro"`), exatamente nessa grafia, se já existir em
  `catalogo-atual.json`. Não crie variações (`"Sem acabamento"`, `"N/A"`,
  `"-"`) para o mesmo conceito.

---

## 3. Fast path — quando o item é publicado automaticamente

Um item só entra no "fast path" (aprovado e publicado direto, sem
revisão humana) se **todas** as condições forem verdadeiras:
- `confidence >= 0.9`
- `notes` é `null`
- `family`, `product_context`, `component_type` e `finish` já existem
  **exatamente** em `catalogo-atual.json`

Se qualquer um desses itens for novo ou a confiança for baixa, o item
vai para a fila de revisão — **isso não é um erro**, é o comportamento
esperado para dados que precisam de validação humana.

**O que fazer**:
- Não force `confidence: 1.0` em itens onde você não tem certeza só
  para "passar direto". Itens ambíguos devem ir para revisão.
- Se você sabe que uma família/produto/componente/acabamento é novo,
  não tente "disfarçar" usando um nome existente parecido — isso geraria
  dados errados no catálogo. Deixe o item ir para revisão com o nome
  correto e novo.

---

## 4. Preços — arredonde para 2 casas decimais

Cálculos feitos a partir de planilhas Excel frequentemente produzem
artefatos de ponto flutuante (`199.99000000000001`, `89.90000000000001`).

**O que fazer**:
- Sempre arredonde o `price` para **2 casas decimais** antes de colocar
  no JSON (`round(valor, 2)` em Python).
- Use `.` como separador decimal (formato JSON padrão), nunca `,`.
- `currency` deve ser `"BRL"` salvo indicação em contrário.

---

## 5. Não invente SKU, preço ou dimensão

Se a planilha não tiver um valor para um campo obrigatório, ou se o
valor for ambíguo (ex.: célula mesclada, texto livre que parece não ser
preço, SKU ilegível):
- **não** preencha com um valor "chute" só para completar o JSON;
- **não** copie o valor de uma linha vizinha sem confirmação;
- registre a ambiguidade em `notes` (string curta, em português, que
  explique o que está incerto) e deixe `confidence` baixo (ex.: `0.5`),
  para o item cair em revisão humana.

---

## 6. Leitura dinâmica de cabeçalhos e colunas

Planilhas reais raramente têm a mesma estrutura de coluna em todas as
abas — números de colunas, ordem, e presença de colunas "de apoio"
(comentários internos, custos, margens) variam.

**O que fazer**:
- Não assuma posições fixas de coluna (`coluna C = preço`); **leia o
  cabeçalho** de cada aba e identifique as colunas pelo nome/conteúdo.
- Ignore colunas de apoio que não fazem parte do contrato (custo
  interno, margem, observações de uso interno) — elas não devem virar
  campos do JSON nem ir para `notes` salvo se relevantes para a revisão
  do preço/acabamento.
- Trate variações de nome de coluna (ex. "Acabamento" vs "Cor/Acabamento"
  vs "Acab.") como o mesmo campo lógico.

---

## 7. `ref` — identificadores únicos e rastreáveis

Cada item deve ter um `ref` único dentro do JSON, que permita rastrear
de qual aba/linha da planilha ele veio (ex.:
`"solucoes-acusticas-painel-ripado-l1-amendoa"`). Isso facilita muito a
revisão humana e a depuração de problemas depois. Evite `ref` genéricos
tipo `"item-1"`, `"item-2"`, ... sem nenhuma relação com o conteúdo.

---

## 8. Checklist final antes de entregar o JSON

- [ ] JSON é válido (`json.load` não levanta erro).
- [ ] `contract_version` é `"1.0"`.
- [ ] Todos os campos obrigatórios de `source` e de cada item (ver
      `CONTRATO.md`) estão presentes.
- [ ] Nenhuma string contém `U+FFFD` (`�`) — rodar o script da seção 1.
- [ ] Todo `price` está arredondado para 2 casas decimais.
- [ ] Todo `finish` que corresponde a um acabamento já cadastrado usa a
      grafia **exata** de `catalogo-atual.json`.
- [ ] Todo `finish` novo tem `finish_group` válido
      (`madeirado|metalico|pe_estrutura|outro`).
- [ ] Itens com dados ambíguos têm `notes` preenchido e `confidence`
      reduzido — nenhum dado foi "inventado" para preencher lacunas.
- [ ] Cada item tem `ref` único e rastreável até a origem (aba/linha).
- [ ] Se houver muitos itens com acabamento/família/componente **novo**,
      isso foi comunicado ao time — a publicação da tabela vai exigir o
      cadastro prévio dessas entidades em `/catalog/...`.
