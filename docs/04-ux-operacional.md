# UX operacional — importação, revisão e orçamento

> Desenho de experiência para os usuários **internos** que (a) importam
> novas versões da tabela de preços a partir do PDF do fabricante e
> (b) montam orçamentos a partir do catálogo resultante. Baseado no
> domínio mapeado em `docs/01-auditoria-pdf-dominio.md`, no formato de
> extração provado em `docs/02-spike-extracao-pdf.md` /
> `docs/samples/extracao-amostra.json` e no modelo de dados em
> `docs/03-modelagem-sqlite.md`.
>
> Este documento contém **wireframes textuais e especificação
> funcional** — sem UI visual, sem código de aplicação. Cada tela é
> descrita por: objetivo, componentes, campos, ações, validações,
> estados (vazio/erro/carregamento) e permissões.

---

## 0. Premissas de design para este sistema interno

1. **Confiança é o produto.** Este não é um sistema de "preencher
   formulário" — é um sistema que decide se um número que vai para um
   orçamento de cliente está certo. Toda tela que exibe um dado vindo
   de extração automática deve deixar claro **o quão confiável** ele é
   e **de onde** ele veio. Isso não é um adendo "para auditoria" — é o
   centro da experiência de revisão.
2. **Prevenir erro custa menos que tratá-lo.** Sempre que possível,
   restringir a entrada (combos com vocabulário fechado, máscaras de
   formato, validação no momento da digitação) em vez de aceitar
   qualquer coisa e mostrar erro depois — especialmente em campos que
   alimentam preço de orçamento.
3. **Lote com rede de segurança, não lote cego.** Correções em massa
   são essenciais (a mesma falha de extração se repete centenas de
   vezes), mas **toda ação em lote mostra uma pré-visualização** do que
   vai mudar, permite restringir o escopo e nunca sobrescreve uma
   decisão humana já tomada sem aviso.
4. **Estados vazios e de carregamento orientam, não decoram.** Em um
   fluxo operacional longo (importar → revisar → aprovar → publicar →
   orçar), o usuário precisa sempre saber "o que falta" e "o que fazer
   agora" — os estados vazios são oportunidades de apontar o próximo
   passo, não apenas avisos de "nada aqui".
5. **Nada que vira orçamento de cliente é editado "no escuro".**
   Qualquer edição de SKU, preço, acabamento ou dimensão exige
   justificativa e fica registrada (consistente com
   `import_review_decisions` no modelo de dados) — não existe "edição
   silenciosa" em dado de catálogo.

### Papéis (permissões transversais)

| Papel | O que faz | Onde aparece |
|---|---|---|
| **Importador** | Sobe novos PDFs e acompanha o processamento | Telas 1–2 |
| **Revisor** | Compara, corrige e aprova/rejeita itens extraídos | Telas 3–4 |
| **Aprovador/Admin** | Publica a versão revisada como nova tabela vigente; acesso total | Telas 5, 10 + tudo do Revisor |
| **Vendedor** | Consulta catálogo e monta/edita/exporta orçamentos | Telas 6–9 |
| **Auditor** | Investiga a origem de qualquer preço (pode ser o próprio Admin) | Tela 10 |

### Padrões transversais de estado

Para não repetir em cada tela, os três estados abaixo seguem o mesmo
vocabulário visual em todo o sistema — cada seção de tela só descreve o
que **difere** desse padrão:

- **Carregamento**: listas/tabelas usam *skeleton rows* (linhas cinza
  pulsantes no formato final do conteúdo); operações pontuais (salvar,
  buscar) usam *spinner* inline no botão/campo afetado; processos
  longos (processar PDF, publicar tabela, gerar PDF de orçamento) usam
  *barra de progresso* com texto de etapa atual e tempo estimado.
- **Vazio**: sempre com (a) ícone/ilustração neutra, (b) frase
  explicando *por que* está vazio (filtro? ainda não há dados? tudo
  concluído?) e (c) uma ação primária que resolve o "vazio" quando
  fizer sentido (ex.: "Importar primeira tabela", "Limpar filtros").
- **Erro**: erros de **campo** ficam inline, abaixo do campo, em
  vermelho, com texto específico (não "valor inválido" genérico);
  erros de **ação** (salvar, publicar, exportar) aparecem em um banner
  no topo da área afetada, com botão **Tentar novamente** e, quando
  aplicável, **Ver detalhes técnicos** (para o time de suporte); erros
  de **carregamento de página inteira** mostram uma tela de fallback
  com **Recarregar** e link para suporte.

---

## 1. Upload de PDF

**Objetivo**: permitir que um Importador inicie a importação de uma
nova versão da tabela de preços a partir de um arquivo PDF.

```
┌────────────────────────────────────────────────────────────────────┐
│  Importar nova tabela de preços                                     │
├────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────┐   Código da versão               │
│  │                               │   [ 02-2025                   ]  │
│  │     Arraste o PDF aqui        │   Vigência a partir de           │
│  │   ou  [ Selecionar arquivo ]  │   [ 01/07/2026                ]  │
│  │                               │   Observações (opcional)         │
│  │   pdf-precos-julho.pdf  2,1MB │   [______________________________]│
│  └───────────────────────────────┘                                  │
│                                                                      │
│                                   [Cancelar]   [Iniciar importação] │
├────────────────────────────────────────────────────────────────────┤
│  Importações recentes                                               │
│   01-2025.pdf     ✓ processado   08/05/2026   [ver detalhes]        │
│   teste-abr.pdf   ✗ erro         02/04/2026   [ver detalhes]        │
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: área de arrastar-e-soltar com seletor de
arquivo alternativo; cartão de arquivo selecionado (nome, tamanho,
miniatura/ícone, botão remover); formulário de metadados; lista/tabela
de importações recentes com status e link para detalhe.

**Campos**:
- Arquivo PDF (obrigatório)
- Código da versão da tabela — ex. `02-2025` (obrigatório, mapeia para
  `price_tables.code`)
- Vigência a partir de — data (opcional no upload; pode ser definida
  na publicação, tela 5)
- Observações (texto livre, opcional)

**Ações**: selecionar/arrastar arquivo; remover arquivo selecionado;
preencher metadados; **Iniciar importação** (envia o arquivo e navega
para a tela de processamento); **Cancelar**; abrir detalhe de uma
importação anterior.

**Validações**:
- Tipo de arquivo: somente `.pdf` — rejeitar outros formatos
  imediatamente, antes do upload, com mensagem clara ("Este sistema
  aceita apenas arquivos PDF").
- Tamanho máximo do arquivo (definir limite operacional, ex. 100 MB) —
  bloquear e explicar antes de subir.
- Código da versão: obrigatório, formato esperado (`NN-AAAA`) validado
  no campo; **checagem de duplicidade** assíncrona contra
  `price_tables.code` — se já existir, bloquear com link para a versão
  existente ("Já existe uma versão '02-2025'. Ver detalhes ↗").
- **Detecção de arquivo repetido**: comparar hash do arquivo
  (`imported_files.file_hash`) com importações anteriores; se idêntico,
  alertar antes de prosseguir ("Este arquivo já foi importado em
  08/05/2026. Importar mesmo assim?") — evita reprocessar o mesmo PDF
  por engano.

**Estados vazios**: nenhuma importação anterior — mensagem "Esta será a
primeira tabela importada" sem a seção de histórico.

**Estados de erro**: falha de upload (rede/timeout) com **Tentar
novamente** preservando o arquivo já selecionado; arquivo corrompido
detectado no servidor ("Não foi possível abrir este PDF — verifique se
o arquivo não está corrompido"); código de versão duplicado (tratado
como validação, acima).

**Estados de carregamento**: barra de progresso de upload (%, tamanho
enviado/total); botão "Iniciar importação" em estado de carregamento
("Enviando…") até a confirmação do servidor de que o processamento
começou.

**Permissões**: Importador e Admin. Vendedores e Revisores não têm
acesso a esta tela (ela não aparece na navegação para esses papéis).

---

## 2. Processamento do PDF

**Objetivo**: dar visibilidade ao andamento da extração automática —
sem exigir nenhuma ação além de aguardar ou cancelar.

```
┌────────────────────────────────────────────────────────────────────┐
│  Processando: pdf-precos-julho.pdf  →  versão 02-2025               │
├────────────────────────────────────────────────────────────────────┤
│  Extraindo conteúdo das páginas                                      │
│  ████████████████████░░░░░░░░░░░░░░  287 / 435 páginas  (≈ 4 min)   │
│                                                                      │
│  Encontrados até agora                                               │
│   1.842 itens   • confiança alta:  1.690   • média: 118  • baixa: 34│
│   12 avisos                                                          │
│                                                                      │
│  Atividade recente                                                   │
│   pág. 287  •  perfil "tampo_padrao"  •  9 itens  •  0 avisos       │
│   pág. 286  •  perfil "tampo_padrao"  •  9 itens  •  0 avisos       │
│   pág. 245  ⚠ perfil desconhecido — marcado para revisão prioritária│
│                                                                      │
│                                              [Cancelar processamento]│
└────────────────────────────────────────────────────────────────────┘
```
*(ao concluir, o botão de cancelar é substituído por* **Ir para
revisão →** *)*

**Componentes de interface**: cabeçalho com nome do arquivo e versão
de destino; barra de progresso com contagem de páginas e tempo
estimado; cartões de contagem (itens por nível de confiança, total de
avisos); feed de atividade recente (últimas páginas processadas, com
destaque para páginas que geraram avisos).

**Campos**: nenhum (tela somente leitura/acompanhamento).

**Ações**: **Cancelar processamento** (com confirmação — explica que o
progresso parcial será descartado); ao concluir, **Ir para revisão**
(navega para a tela 3 já filtrada pela importação atual); abrir o
detalhe de uma página específica do feed.

**Validações**: não aplicável (tela de status).

**Estados vazios**: não aplicável — a tela só existe quando há um
processamento em curso ou recém-concluído.

**Estados de erro**:
- **Falha total** (PDF ilegível, sem texto extraível): tela de erro
  dedicada explicando a causa provável e oferecendo **Tentar
  novamente** ou **Cancelar e reportar**.
- **Falha parcial** (algumas páginas não puderam ser processadas): o
  processamento continua, e as páginas afetadas aparecem destacadas no
  feed com ⚠ e contador "X páginas com falha — serão marcadas para
  revisão manual"; ao final, essas páginas chegam à fila de revisão com
  `confidence_level = baixa` e um aviso explícito.

**Estados de carregamento**: a tela inteira É o estado de carregamento
— atualização em tempo real (polling ou *push*) da barra de progresso e
do feed, sem necessidade de recarregar a página.

**Permissões**: visível para quem iniciou a importação (Importador) e
para Admin/Revisor (para acompanhar sem precisar esperar).

---

## 3. Revisão de extração (fila de triagem)

**Objetivo**: dar ao Revisor uma visão geral de **tudo que precisa de
atenção** numa importação — filtrar, priorizar e selecionar itens para
correção em lote ou individual.

```
┌────────────────────────────────────────────────────────────────────┐
│  Revisão — versão 02-2025                    1.842 itens extraídos  │
├────────────────────────────────────────────────────────────────────┤
│  [🔍 Buscar por SKU, descrição, página...]                          │
│  Confiança: [ Todas ▾ ]  Status: [ Pendentes ▾ ]  Página: [__-__]   │
│  Seção: [ Todas ▾ ]               12 avisos abertos  [ver avisos]   │
├────────────────────────────────────────────────────────────────────┤
│  ☐  Conf.   Pág.  Componente          Descrição          SKU   Preço│
│  ☐  ⚠baixa   432  Reunião Redonda     Pé Disco 1100MM   39810… —    │
│  ☐  média    432  Reunião Redonda     Pé Painel 900MM   39809… 534,16│
│  ☐  alta       2  Tampo Inteiro       Simples 1200x900  39811… 382,75│
│  ...                                                                 │
├────────────────────────────────────────────────────────────────────┤
│  3 selecionados   [Aprovar selecionados] [Rejeitar selecionados]    │
│                                          [Abrir em lote →]           │
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: barra de busca textual; filtros
combináveis (nível de confiança, status de revisão, intervalo de
página, seção/perfil de página); indicador de avisos abertos com atalho;
tabela paginada/virtualizada com seleção múltipla; barra de ações em
lote fixa no rodapé quando há seleção; badge de confiança colorido por
linha (vermelho/amarelo/verde).

**Campos** (filtros): texto de busca; nível de confiança
(`alta`/`média`/`baixa`/todas); status (`pendente`/`revisado`/
`aprovado`/`rejeitado`/`corrigido`/todos); intervalo de páginas; seção
ou perfil de página.

**Ações**: aplicar/limpar filtros; ordenar colunas (por padrão,
confiança crescente — prioriza o que precisa de mais atenção); abrir um
item (navega para a tela 4); selecionar itens (checkbox individual ou
"selecionar todos os filtrados"); aprovar/rejeitar em lote a seleção
direta (para casos óbvios, sem precisar editar); abrir o fluxo de
correção em lote (tela 4, modal de lote).

**Validações**:
- Ações em lote exigem seleção não vazia; "rejeitar em lote" exige uma
  justificativa única aplicada a todos os itens selecionados.
- Combinações de filtro sem resultado mostram contagem zerada antes de
  renderizar a tabela vazia (evita "pulo" de layout).

**Estados vazios**:
- **Sem itens para os filtros aplicados**: "Nenhum item encontrado com
  esses filtros" + botão **Limpar filtros**.
- **Fila zerada** (tudo revisado): estado de celebração — "Tudo
  revisado! 1.842 de 1.842 itens com decisão registrada." + botão
  **Ir para aprovação para catálogo →** (tela 5). Esse é o estado que
  sinaliza ao Revisor que o próximo passo é do Aprovador.

**Estados de erro**: falha ao carregar a lista (banner "Não foi
possível carregar os itens — Tentar novamente"); falha ao aplicar ação
em lote (mensagem específica: "X de Y itens não puderam ser
atualizados" com lista dos que falharam e por quê — nunca "tudo ou
nada" silencioso).

**Estados de carregamento**: *skeleton rows* na tabela ao carregar/
filtrar; spinner inline nos botões de ação em lote durante o
processamento; contador "Aplicando a 47 itens… 12 concluídos".

**Permissões**: Revisor e Admin. "Aprovar"/"Rejeitar" em lote ficam
visíveis para ambos; ações que **promovem ao catálogo** (tela 5) ficam
reservadas ao Admin/Aprovador (o Revisor vê o botão, mas ele leva a uma
tela cujo botão final de publicação está desabilitado para o seu papel,
com explicação "Publicação requer um Aprovador").

---

## 4. Correção de dados extraídos — **a tela de revisão de importação**

> Esta é a tela com **atenção especial** pedida no briefing — reúne
> comparação, edição campo a campo, decisão (aprovar/rejeitar) e
> correção em lote num único fluxo de trabalho contínuo, para que o
> Revisor não precise "trocar de tela" a cada item.

**Objetivo**: permitir que o Revisor compare o trecho original do PDF
com o item normalizado, **corrija com segurança** os campos que a
extração não capturou bem, e registre uma decisão — item a item ou em
lote — sem perder o contexto de origem.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Fila de revisão        Item 47 de 312 filtrados — pág. 2, Tampo 1200x900    │
├────────────────────────────────────┬─────────────────────────────────────────┤
│ ORIGEM (página 2 do PDF)            │ COMPARAÇÃO: linha bruta × item           │
│ ┌─────────────────────────────────┐ │ normalizado                              │
│ │                                 │ │                                          │
│ │  [render da página com a        │ │ Linha de origem (raw_row #6 · y=750,1)   │
│ │   linha em destaque + realce    │ │ ┌─────────────────────────────────────┐ │
│ │   do trecho deste item]         │ │ │ "...382,75  374,45  493,80 472,85.."│ │
│ │                                 │ │ └─────────────────────────────────────┘ │
│ │      [−]  zoom  [+]             │ │ ☑ ver também as 2 linhas de contexto    │
│ └─────────────────────────────────┘ │   ("Para Estrutura Reunião" / "Caixa…") │
│ [Ir para página: ___]               │                                          │
│                                      │ Item normalizado (3º de 9 nesta linha)  │
│                                      │ ⚠ Confiança: ALTA (0,95)                │
│                                      │ ──────────────────────────────────────  │
│                                      │ SKU          [3981130567        ] ✎     │
│                                      │ Preço        [R$ 493,80         ] ✎     │
│                                      │ Acabamento   [Preto          ▾  ] ✎     │
│                                      │ Dimensão     L [1200] × P [900] mm  ✎   │
│                                      │ Componente   [Tampo          ▾  ] ✎     │
│                                      │ Descrição (somente leitura)              │
│                                      │  "Tampo Inteiro Simples Para Estrutura…" │
│                                      │                                          │
│                                      │ Notas de extração:                       │
│                                      │  • SKU/preço pareados pela 3ª posição    │
│                                      │    do bloco de 9 (perfil validado)       │
│                                      │                                          │
│                                      │ Justificativa (obrigatória ao editar     │
│                                      │ ou rejeitar)                             │
│                                      │ [_____________________________________] │
│                                      │                                          │
│                                      │ [Aplicar correção em lote…]              │
│                                      │            [Rejeitar]   [✓ Aprovar]      │
│                                      │      [◀ Item anterior]   [Próximo ▶]     │
└──────────────────────────────────────┴─────────────────────────────────────────┘
```

### Capacidades específicas desta tela (mapeadas do briefing)

1. **Visualizar página original ou trecho original** — painel esquerdo
   com o *render* da página do PDF; a linha correspondente ao item
   atual vem **realçada automaticamente** (usa as coordenadas
   `y_coordinate` registradas em `extracted_rows`); controles de zoom
   e um campo "Ir para página" para navegação livre quando o revisor
   quiser conferir o contexto maior (ex.: o bloco de "Descrição
   Técnica" da seção).
2. **Comparar linha extraída com item normalizado** — painel direito
   dividido em duas partes: (a) o **texto bruto** da linha de origem,
   exatamente como extraído (inclusive ruídos, ex. `"744 ,22"` com
   espaço espúrio), com um toggle para revelar linhas de contexto
   vizinhas (ex. observações livres concatenadas na descrição); (b) o
   **item normalizado**, campo a campo, editável. A justaposição lado a
   lado é deliberada — o Revisor decide "o sistema interpretou certo?"
   olhando os dois ao mesmo tempo, sem alternar de tela.
3. **Editar SKU** — campo de texto com máscara numérica; valida
   comprimento esperado (9–10 dígitos) e formato; se o valor editado já
   existe no catálogo associado a **outra** variação, exibe aviso
   informativo (não bloqueante — é o comportamento esperado para peças
   físicas compartilhadas, conforme já confirmado na auditoria) com
   link "ver outras associações deste código".
4. **Editar preço** — campo monetário com máscara BRL
   (`R$ 0.000,00`), aceita o separador decimal por vírgula; normaliza
   automaticamente ruídos de espaçamento (`"744 ,22"` → `744,22`)
   mostrando o valor já limpo para confirmação; valida valor positivo;
   alerta (não bloqueia) se o novo valor estiver **muito distante** da
   média de preços de itens com o mesmo componente/dimensão na mesma
   tabela ("Este valor está 40% acima da média de itens semelhantes —
   confirme antes de aprovar").
5. **Editar acabamento** — campo do tipo combo/autocomplete restrito ao
   **vocabulário fechado** de `finishes` (evita criar grafias
   divergentes do mesmo acabamento — ex. "Nogueira Cádiz" vs "Nogueira
   Cadiz"); opção explícita **"Não está na lista — cadastrar novo
   acabamento"**, que abre um sub-formulário curto (nome + grupo:
   madeirado/metálico/pé) e fica registrada como uma decisão que requer
   atenção do Aprovador na tela 5.
6. **Editar dimensão** — campos numéricos contextuais: o formulário
   **se adapta ao tipo de produto** (largura×profundidade para tampos;
   diâmetro para mesas redondas; largura×profundidade×altura para
   conectores) em vez de forçar sempre os mesmos dois campos — espelha
   a estrutura flexível de `dimensions` no modelo de dados. O texto
   bruto original (`raw_label`, ex. `"900MM"`) permanece visível ao
   lado como referência de conferência.
7. **Marcar item como aprovado** — botão **Aprovar**; grava
   `review_status = aprovado` e uma entrada em
   `import_review_decisions`; avança automaticamente para o próximo
   item da fila filtrada (mantém o ritmo de revisão sem cliques
   extras). Itens aprovados **com edição prévia** ficam, na verdade,
   com `decision = corrigido` (a edição é registrada como correção; a
   aprovação é a decisão final sobre o valor já corrigido).
8. **Marcar item como rejeitado** — botão **Rejeitar**; **exige
   justificativa** (campo obrigatório ao acionar); grava
   `review_status = rejeitado` — o item **não** seguirá para o
   catálogo nesta versão; fica disponível para consulta futura
   ("por que rejeitamos este código na v.02-2025?").
9. **Ver alertas de baixa confiança** — badge de confiança sempre
   visível no topo do painel de comparação, com cor e rótulo
   (vermelho/"BAIXA", amarelo/"MÉDIA", verde/"ALTA"); ao passar o
   cursor (ou tocar, em telas sensíveis ao toque), expande para mostrar
   **por que** a confiança é essa — lista as `extraction_notes`
   relevantes (ex. "código sem preço pareado na faixa esperada — typo
   conhecido nas págs. 432–435") e qualquer `import_warning` associado
   ao item. Itens de confiança baixa também são **destacados na fila**
   (tela 3) e priorizados na ordenação padrão.
10. **Aplicar correção em lote quando várias linhas seguirem o mesmo
    padrão** — botão **Aplicar correção em lote…**, disponível
    imediatamente após o Revisor editar um campo. Abre o fluxo descrito
    a seguir.

### Fluxo de correção em lote (modal)

```
┌──────────────────────────────────────────────────────────────────┐
│ Aplicar correção em lote                                     [×] │
├──────────────────────────────────────────────────────────────────┤
│ Você alterou o campo "Acabamento" de "Am�ndoa" para "Amêndoa"     │
│ no item #4128. Encontramos outros itens com o MESMO valor bruto   │
│ ("Am�ndoa") neste campo:                                          │
│                                                                    │
│  Aplicar a:                                                        │
│   ( ) Apenas itens desta página (2)               — 9 itens       │
│   (•) Itens do mesmo perfil de página "tampo_padrao" — 37 itens   │
│   ( ) Todos os itens desta importação              — 41 itens     │
│                                                                    │
│  Pré-visualização (3 de 37 — ver lista completa)                  │
│   pág.   2  •  conf. alta   •  "Am�ndoa" → "Amêndoa"              │
│   pág.  45  •  conf. alta   •  "Am�ndoa" → "Amêndoa"              │
│   pág.  88  •  conf. média  •  "Am�ndoa" → "Amêndoa"              │
│                                                                    │
│  ⚠ 2 destes itens já têm decisão humana registrada — serão        │
│     PRESERVADOS (não sobrescritos). Ver quais ↗                   │
│                                                                    │
│                              [Cancelar]   [Aplicar a 35 itens]    │
└──────────────────────────────────────────────────────────────────┘
```

- **Critério de agrupamento**: o sistema propõe candidatos comparando o
  **valor bruto original** do campo editado (`*_raw`) — não o valor já
  corrigido — dentro de um escopo que o Revisor pode restringir
  (página atual / perfil de página / importação inteira). Isso evita
  generalizar uma correção válida para "Amêndoa" para outro problema
  que por coincidência produza texto parecido.
- **Pré-visualização obrigatória**: nenhuma alteração em lote é
  aplicada sem que o usuário veja, página a página, o que vai mudar —
  com paginação/lista completa sob demanda ("ver lista completa").
- **Rede de segurança para decisões humanas prévias**: itens que já
  possuem uma entrada em `import_review_decisions` (já revisados,
  aprovados, rejeitados ou corrigidos manualmente) são **excluídos
  automaticamente** do lote e contabilizados à parte — o sistema nunca
  sobrescreve silenciosamente uma decisão humana anterior com uma ação
  em massa.
- **Resultado auditável**: cada correção aplicada em lote gera sua
  própria entrada em `import_review_decisions` (`decision = corrigido`,
  com nota indicando que a origem foi uma "correção em lote a partir do
  item #4128") — para fins de auditoria, é indistinguível de uma
  correção manual individual, exceto pela anotação de origem.

### Demais especificações da tela 4

**Componentes de interface**: layout em duas colunas (visualizador de
PDF | comparação e formulário); barra de navegação superior com posição
na fila ("Item 47 de 312") e botão de retorno à fila; modal de correção
em lote; tooltip/popover de detalhe de confiança.

**Campos**: SKU, preço, acabamento (combo de vocabulário fechado +
opção de cadastro), dimensão (1–3 grandezas conforme tipo de produto),
tipo de componente (combo), justificativa (texto, obrigatório ao
editar/rejeitar).

**Ações**: editar campo (entra em modo de edição inline); desfazer
edição de um campo (volta ao valor extraído); salvar correção;
aprovar; rejeitar; abrir correção em lote; navegar item anterior/
próximo; voltar à fila; alternar exibição de linhas de contexto;
ajustar zoom/navegar página do visualizador.

**Validações**: todas as listadas nos itens 3–6 acima, mais: campo de
justificativa obrigatório sempre que **qualquer** valor for alterado ou
o item for rejeitado; o sistema impede salvar uma correção que deixe o
item em estado inconsistente (ex. SKU presente sem preço, sem que isso
seja explicitamente confirmado — "Este item ficará com preço em
branco — confirma?").

**Estados vazios**: ao chegar ao fim da fila filtrada — "Você revisou
todos os itens deste filtro." com **Voltar à fila** e **Ver próximo
filtro sugerido** (ex. "34 itens de confiança baixa ainda pendentes em
outra seção").

**Estados de erro**: falha ao carregar o *render* da página original
("Não foi possível carregar a página 2 do PDF — Tentar novamente |
Continuar sem visualização"); conflito de edição concorrente — "Este
item foi revisado por outra pessoa (Maria, há 2 minutos) — recarregar
para ver a decisão atual?"; falha ao salvar (preserva os valores
digitados no formulário, nunca os descarta).

**Estados de carregamento**: *skeleton* no visualizador de página
enquanto o render carrega; spinner inline no botão Aprovar/Rejeitar/
Salvar durante a gravação; barra de progresso "Aplicando correção a
35 itens… 18 concluídos" no modal de lote.

**Permissões**: Revisor e Admin podem editar/aprovar/rejeitar
individualmente e aplicar lotes restritos à própria importação. Ações
que afetam **muitos** itens de uma vez (ex. lote "toda a importação")
podem exigir confirmação adicional ou ficar reservadas ao Admin —
parametrizável conforme política interna.

---

## 5. Aprovação para catálogo

**Objetivo**: permitir que um Aprovador revise o conjunto de itens já
aprovados na triagem e **publique** uma nova versão da tabela de preços
no catálogo normalizado — o ponto de não-retorno do fluxo de
importação.

```
┌────────────────────────────────────────────────────────────────────┐
│  Publicar versão 02-2025 no catálogo                                │
├────────────────────────────────────────────────────────────────────┤
│  Resumo da revisão                                                   │
│   ✓ 1.798 itens aprovados        ✗ 12 rejeitados                    │
│   ⚠ 32 itens ainda pendentes — não serão incluídos nesta publicação │
│                                                                      │
│  O que vai mudar no catálogo                                         │
│   • 14 novos acabamentos a cadastrar (revisar lista ↗)              │
│   • 3 SKUs já existentes terão preço atualizado (ver diferenças ↗)  │
│   • 1.781 preços novos serão criados para a versão 02-2025          │
│                                                                      │
│  ⚠ Conflitos a resolver antes de publicar (2)                       │
│   • SKU 3981234567 — valor 40% maior que na versão anterior         │
│     [Revisar item] [Marcar como esperado e continuar]               │
│                                                                      │
│  Dados da versão                                                     │
│   Vigência a partir de  [ 01/07/2026 ]   ☑ Tornar esta a vigente    │
│                                                                      │
│                       [Cancelar]   [Publicar 1.798 itens no catálogo]│
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: painel-resumo com contagens (aprovados/
rejeitados/pendentes); seção "diff" mostrando o que será criado/
atualizado no catálogo (novos acabamentos, novas variações, mudanças de
preço em SKUs já existentes); lista de conflitos bloqueantes com ação
de resolução por item; formulário de dados da versão; botão de
publicação com contagem dinâmica.

**Campos**: vigência (`valid_from`/`valid_to`), marcar como versão
vigente (define `price_tables.status = vigente`, o que implicitamente
torna a anterior `substituida`).

**Ações**: revisar item de conflito (abre a tela 4 em contexto);
marcar conflito como esperado (libera a publicação sem alterar o
valor); ver lista completa de novos acabamentos / mudanças de preço;
**Publicar no catálogo** (ação irreversível — exige confirmação
explícita em diálogo separado, com resumo final); **Cancelar** (volta à
fila de revisão sem publicar).

**Validações**:
- Publicação **bloqueada** enquanto houver conflitos não resolvidos
  (cada conflito precisa de "revisar" ou "marcar como esperado").
- Itens com `review_status = pendente` **nunca** entram na publicação —
  o resumo deixa isso textualmente explícito ("32 itens pendentes não
  serão incluídos") para que ninguém publique pensando que tudo foi
  considerado.
- Confirmação de duas etapas para a ação final (resumo → "Sim, publicar
  1.798 itens como tabela 02-2025").

**Estados vazios**: nenhum item aprovado ainda — a tela não oferece o
botão de publicar; mostra "Nenhum item aprovado para publicação. Volte
à fila de revisão." com atalho.

**Estados de erro**: falha durante a publicação (parcial) — o sistema
**não deixa o catálogo em estado intermediário**: a publicação é
tratada como uma operação atômica (tudo ou nada) e, em caso de falha,
exibe "A publicação não pôde ser concluída — nenhuma alteração foi
aplicada. Tentar novamente | Ver detalhes técnicos".

**Estados de carregamento**: barra de progresso "Publicando… criando
variações (340/1.798)" — operação potencialmente longa, com texto de
etapa (criar produtos → criar variações → criar SKUs → gravar preços).

**Permissões**: **exclusivo de Aprovador/Admin**. Revisores acessam a
tela em modo somente-leitura (veem o resumo, não o botão de publicar) —
útil para conferirem se seu trabalho está pronto para ser publicado.

---

## 6. Consulta do catálogo

**Objetivo**: permitir que qualquer usuário interno (especialmente
Vendedores, na preparação de um orçamento) busque e explore o catálogo
normalizado — produtos, variações, acabamentos, SKUs e preços — de
forma rápida e confiável.

```
┌────────────────────────────────────────────────────────────────────┐
│  Catálogo                                  Tabela vigente: 01-2025 ▾│
├────────────────────────────────────────────────────────────────────┤
│  [🔍 Buscar por produto, SKU, descrição...]                         │
│  Família:[Mesas Reunião▾] Componente:[Tampo▾] Acabamento:[Todos▾]   │
│  Dimensão:  L[____] × P[____]  ou  Diâmetro [____]                   │
├──────────────────────────┬─────────────────────────────────────────┤
│ Resultados (134)         │  Reunião 1200x900 — Tampo Inteiro Simples│
│ ▸ Reunião 1200x900       │  — Carvalho                              │
│   Tampo Inteiro Simples  │ ─────────────────────────────────────── │
│    • Argila    382,75    │  SKU         3981144789                  │
│    • Carvalho  493,80 ◂  │  Preço (01-2025)   R$ 493,80             │
│    • ...                 │  Dimensão    1200 × 900 mm               │
│ ▸ Reunião 1200x900       │  Componente  Tampo                       │
│   Estrutura Tampo Inteiro│  Descrição   "Tampo Inteiro Simples..."  │
│ ▸ Reunião 1350x1350      │                                          │
│   ...                    │  Histórico de preço                      │
│                          │   01-2025: R$ 493,80   (vigente)         │
│                          │   —  sem versões anteriores cadastradas  │
│                          │                                          │
│                          │            [+ Adicionar a um orçamento]  │
└──────────────────────────┴─────────────────────────────────────────┘
```

**Componentes de interface**: seletor de versão de tabela (padrão: a
vigente); busca textual; filtros facetados (família, tipo de
componente, acabamento, dimensão — com campos que se adaptam ao tipo de
produto, igual à tela 4); lista de resultados agrupada por
produto/variação; painel de detalhe com ficha completa da variação
selecionada e histórico de preço entre versões de tabela.

**Campos** (filtros): texto de busca; família; tipo de componente;
acabamento; dimensão (largura×profundidade **ou** diâmetro, conforme o
tipo selecionado).

**Ações**: buscar/filtrar; selecionar item da lista (abre o detalhe);
trocar a versão de tabela exibida (consulta histórica); **Adicionar a
um orçamento** (atalho que leva à tela 7 com este item pré-selecionado);
copiar SKU; ver "auditar origem deste preço" (atalho para a tela 10).

**Validações**: campos de dimensão aceitam apenas números inteiros
positivos; combinações de filtro sem correspondência mostram contagem
zerada antes da lista vazia.

**Estados vazios**:
- **Catálogo ainda sem nenhuma versão publicada**: "O catálogo ainda
  não tem nenhuma tabela publicada." + atalho para a fila de revisão
  (se houver uma importação em andamento) ou para iniciar uma
  importação (conforme o papel do usuário).
- **Busca sem resultado**: "Nenhum item encontrado para esses
  critérios" + sugestão de relaxar filtros.

**Estados de erro**: falha ao carregar resultados (banner com **Tentar
novamente**); falha ao carregar o histórico de preço de um item
(mensagem específica nessa seção do painel, sem comprometer o restante
do detalhe).

**Estados de carregamento**: *skeleton* na lista de resultados durante
a busca; spinner no painel de detalhe ao trocar de item; indicador de
carregamento ao trocar a versão de tabela exibida.

**Permissões**: leitura para todos os papéis autenticados (Vendedor,
Revisor, Admin). Nenhuma ação de escrita nesta tela.

---

## 7. Montagem de orçamento

**Objetivo**: permitir que um Vendedor monte um orçamento para um
cliente, combinando componentes do catálogo (com filtros de
compatibilidade) em uma ou mais "linhas" de produto.

```
┌────────────────────────────────────────────────────────────────────┐
│  Novo orçamento                          Tabela-base: 01-2025 (vig.)│
├────────────────────────────────────────────────────────────────────┤
│  Cliente   [ Buscar ou cadastrar cliente...           ▾]            │
│  Validade  [ 30 dias ▾ ]                                            │
├────────────────────────────────────────────────────────────────────┤
│  Itens do orçamento                            [+ Adicionar item]   │
│                                                                      │
│  1. Reunião 1200x900 — composição                          qtd [2]  │
│      • Tampo Inteiro Simples — Carvalho      R$ 493,80    [editar]  │
│      • Estrutura Reunião — Prata             R$ 612,40    [editar]  │
│      • Apoio Credenza 5050 — Prata           R$ 318,90  [remover]   │
│                                                          [+ componente]│
│      Subtotal da linha: R$ 2.850,20                       [remover] │
│                                                                      │
│  2. Reunião Redonda 900MM — Pé Painel — Argila              qtd [1] │
│      Subtotal da linha: R$ 534,16                  [editar][remover]│
├────────────────────────────────────────────────────────────────────┤
│  Subtotal: R$ 3.384,36                                               │
│  [Salvar rascunho]                          [Revisar e finalizar →] │
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: seletor/cadastro rápido de cliente;
seletor de validade; lista de "linhas" do orçamento (cada uma podendo
agregar 1+ componentes); buscador de catálogo embutido (reaproveita os
filtros da tela 6) acionado por **+ Adicionar item**; resumo de
subtotal fixo no rodapé.

**Campos**: cliente (busca/seleção/criação rápida); validade do
orçamento; por linha — produto/variações selecionadas, acabamento por
componente, quantidade; observações por linha (opcional).

**Ações**: buscar e adicionar item/componente ao orçamento; ajustar
quantidade; remover componente ou linha inteira; salvar como rascunho;
avançar para revisão final (tela 9, em modo de pré-visualização).

**Validações**:
- **Acabamento filtrado por tipo de componente**: ao escolher o
  acabamento de um Tampo, somente os 9 acabamentos "madeirados"
  aparecem; ao escolher o de uma Estrutura, somente os 3 metálicos —
  refletindo a regra física confirmada na auditoria (não é possível
  pedir "Estrutura Carvalho"). Isso é validação **por restrição de
  opções**, não por mensagem de erro depois do fato.
- Quantidade: inteiro positivo (mínimo 1).
- Cliente obrigatório para **finalizar** (não para salvar rascunho).
- Ao adicionar um componente cujo preço não existe na tabela-base
  selecionada (caso real de "código sem preço" documentado nas págs.
  432–435): o sistema **impede a adição** e explica — "Este item não
  tem preço cadastrado na tabela 01-2025. Selecione outra variação ou
  contate o time de catálogo." — nunca deixa um item sem preço entrar
  silenciosamente num orçamento.

**Estados vazios**: orçamento recém-criado — "Seu orçamento está vazio.
Use *Adicionar item* para buscar no catálogo." com o buscador já em
foco.

**Estados de erro**: falha ao buscar no catálogo (mensagem inline no
buscador, com **Tentar novamente**); falha ao salvar rascunho
(mantém o estado local e tenta novamente em segundo plano, avisando
"Não foi possível salvar — suas alterações estão preservadas neste
dispositivo").

**Estados de carregamento**: spinner no buscador de catálogo durante a
busca; spinner no botão "Salvar rascunho"/"Revisar e finalizar"
durante a gravação.

**Permissões**: Vendedor (cria e edita os próprios orçamentos) e Admin
(qualquer orçamento). A tabela de preço usada como base é, por padrão,
a **vigente** — trocar para uma versão arquivada exige uma ação
explícita e gera um aviso visível no orçamento final ("Este orçamento
usa a tabela 01-2025, que não é mais a vigente").

---

## 8. Edição de item do orçamento

**Objetivo**: permitir ajustar uma linha já adicionada ao orçamento —
trocar acabamento/variação, alterar quantidade, adicionar ou remover
componentes — antes (ou, de forma controlada, depois) da finalização.

```
┌────────────────────────────────────────────────────────────────────┐
│  Editar item — Reunião 1200x900 (composição)                  [×]  │
├────────────────────────────────────────────────────────────────────┤
│  Quantidade da linha   [ 2 ]                                         │
│                                                                      │
│  Componentes                                                         │
│   Tampo Inteiro Simples                                              │
│     Acabamento  [ Carvalho ▾ ]     Preço atual: R$ 493,80           │
│   Estrutura Reunião Tampo Inteiro                                    │
│     Acabamento  [ Prata    ▾ ]     Preço atual: R$ 612,40           │
│   Apoio Credenza 5050                                                │
│     Acabamento  [ Prata    ▾ ]     Preço atual: R$ 318,90  [remover]│
│                                                          [+ componente]│
│                                                                      │
│  ⚠ Você alterou o acabamento da Estrutura de "Preto" para "Prata".  │
│    O preço será atualizado de R$ 598,00 (congelado) para R$ 612,40  │
│    (tabela 01-2025) ao salvar.                                       │
│                                                                      │
│                                        [Cancelar]   [Salvar alterações]│
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: painel/modal de edição da linha;
controle de quantidade; lista de componentes com seletor de
variação/acabamento por item; aviso inline de recongelamento de preço
quando a troca implica mudança de valor; botão de adicionar/remover
componente.

**Campos**: quantidade da linha; por componente — variação/acabamento
selecionado, quantidade própria (quando aplicável a componentes
vendidos por unidade própria).

**Ações**: alterar quantidade; trocar a variação/acabamento de um
componente (recalcula o preço a partir da tabela-base do orçamento);
adicionar novo componente à composição; remover um componente; salvar
alterações; cancelar (descarta mudanças não salvas, com confirmação se
houver alterações pendentes).

**Validações**:
- Mesmas restrições de compatibilidade de acabamento por tipo de
  componente da tela 7.
- **Aviso explícito de recongelamento**: qualquer troca que implique um
  preço diferente do atualmente congelado mostra, antes de salvar, o
  valor antigo *vs.* o novo (lado a lado) — o usuário precisa ver a
  diferença, não descobri-la só no total final.
- Se a variação/SKU escolhida não tiver preço na tabela-base do
  orçamento, mesmo bloqueio explicativo da tela 7.
- Quantidade mínima 1; remover o último componente de uma linha remove
  a linha inteira (com confirmação).

**Estados vazios**: não se aplica (tela de edição de algo existente).

**Estados de erro**: variação anteriormente selecionada foi
descontinuada/removida do catálogo na tabela-base atual — a tela
sinaliza isso explicitamente ("Esta variação não está mais disponível
na tabela 01-2025") e oferece escolher uma substituta, sem travar a
edição do restante da linha; falha ao salvar preserva as edições no
formulário.

**Estados de carregamento**: spinner ao recalcular preço após troca de
variação; spinner no botão "Salvar alterações".

**Permissões**: Vendedor pode editar os próprios orçamentos enquanto o
status for `rascunho`; orçamentos com status `enviado`/`aprovado`
exigem **reabertura explícita** (ação separada, registrada, talvez
restrita a Admin) antes de permitir edição — evita alterar
silenciosamente algo que o cliente já recebeu.

---

## 9. Exportação ou visualização do orçamento

**Objetivo**: apresentar o orçamento em formato final, pronto para
envio ao cliente — exportar como PDF, compartilhar e acompanhar status.

```
┌────────────────────────────────────────────────────────────────────┐
│  Orçamento #00231 — Studio Almeida Arquitetura      Status: Rascunho│
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  [pré-visualização formatada — cabeçalho com dados do cliente,│  │
│  │   tabela de itens com descrição/quantidade/preço unitário e   │  │
│  │   total, condições de validade e pagamento]                   │  │
│  │                                                                │  │
│  │   1. Reunião 1200x900 — Carvalho/Prata     2 un.  R$ 5.700,40 │  │
│  │   2. Reunião Redonda 900MM — Argila        1 un.  R$   534,16 │  │
│  │   ────────────────────────────────────────────────────────── │  │
│  │   Subtotal                                       R$ 6.234,56  │  │
│  │   Desconto (5%)                                 − R$  311,73  │  │
│  │   Total                                          R$ 5.922,83  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  [Editar]  [Duplicar]  [Exportar PDF]  [Copiar link]  [Marcar como  │
│                                                          enviado]    │
│  Histórico:  criado em 03/06 por Ana · editado em 05/06 por Ana     │
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: pré-visualização fiel ao documento final
(cabeçalho com identidade da empresa e dados do cliente, tabela de
itens, totais, condições); barra de ações; trilha de status/histórico
(quem criou, quem editou, quando foi enviado).

**Campos**: nenhum a preencher diretamente aqui — opções de exportação
(ex. "incluir observações internas: sim/não") ficam num menu de
exportação separado, claramente marcado como configuração de saída
(não altera o orçamento).

**Ações**: **Exportar PDF**; **Copiar link** (para compartilhamento
controlado); **Marcar como enviado** (muda o status e trava edição
direta — ver tela 8); **Duplicar** (cria um novo rascunho a partir
deste, útil para propostas semelhantes); **Editar** (volta à tela 7/8,
quando o status permitir); imprimir.

**Validações**: exportação/envio bloqueados se o orçamento não tiver
ao menos um item ou não tiver cliente associado — mensagem explica
exatamente o que falta ("Adicione um cliente antes de exportar").

**Estados vazios**: não se aplica — a tela só existe para orçamentos
com ao menos um item salvo.

**Estados de erro**: falha ao gerar o PDF (banner "Não foi possível
gerar o PDF agora — Tentar novamente | Ver detalhes técnicos", sem
perder o estado do orçamento); link de compartilhamento expirado/
inválido (mensagem ao destinatário, não ao vendedor).

**Estados de carregamento**: "Gerando PDF…" com spinner/barra,
substituído pelo botão de download ao concluir; spinner ao trocar de
status ("Marcando como enviado…").

**Permissões**: Vendedor (próprios orçamentos) e Admin (qualquer um).
Campos e dados **internos** (ex. nível de confiança da extração, notas
de revisão, código SKU interno se a política comercial assim definir)
nunca aparecem na pré-visualização voltada ao cliente — ficam
reservados às telas 6 e 10.

---

## 10. Auditoria da origem de um preço

**Objetivo**: permitir que um Auditor/Admin — a partir de qualquer
preço exibido no catálogo ou usado em um orçamento — reconstrua a
cadeia completa até o arquivo, página e linha originais do PDF, e veja
o histórico de decisões humanas sobre aquele dado.

```
┌────────────────────────────────────────────────────────────────────┐
│  Auditoria de origem                                                 │
│  [🔍 Buscar por SKU, nº de orçamento, ID de preço...]                │
├────────────────────────────────────────────────────────────────────┤
│  SKU 3981130567 — Tampo Inteiro Simples 1200x900 — Preto            │
│                                                                      │
│  Linha do tempo                                                      │
│   ① Extraído do arquivo "pdf-precos-jan.pdf", pág. 2                │
│       linha bruta (y=750,1): "...382,75 374,45 493,80 472,85..."    │
│       confiança: ALTA (0,95)             [ver página original ↗]    │
│   ② Revisado por Ana Souza em 09/05/2026 — decisão: aprovado        │
│       (sem alterações de valor)                                     │
│   ③ Publicado na tabela 01-2025 em 10/05/2026 por Carlos Lima       │
│       valor gravado no catálogo: R$ 493,80                          │
│   ④ Usado no orçamento #00231 em 03/06/2026 por Ana Souza           │
│       valor CONGELADO no orçamento: R$ 493,80 (idêntico ao catálogo)│
│                                                                      │
│  [Ver todas as versões de tabela em que este SKU aparece]           │
└────────────────────────────────────────────────────────────────────┘
```

**Componentes de interface**: busca universal (aceita SKU, número de
orçamento, ID interno de preço); linha do tempo vertical com eventos
ordenados cronologicamente (extração → revisão → publicação → uso em
orçamento), cada um expansível para detalhe; visualizador de página
original embutido (reaproveita o componente da tela 4); lista de
versões de tabela em que o mesmo SKU/variação aparece, com comparação
de valores lado a lado.

**Campos**: campo de busca único (com detecção automática do tipo de
identificador informado).

**Ações**: buscar; expandir/recolher cada evento da linha do tempo;
abrir a página original em destaque; comparar valores entre versões de
tabela; exportar a trilha como relatório (para responder a uma
contestação de cliente ou auditoria externa, por exemplo).

**Validações**: busca exige ao menos um critério; identifica
automaticamente se o termo buscado é um SKU, um número de orçamento ou
um ID de preço (evita exigir que o usuário "saiba" qual campo usar).

**Estados vazios**:
- **Nenhum resultado**: "Não encontramos nada com esse termo. Verifique
  o código ou tente buscar pelo número do orçamento."
- **Preço sem origem em PDF** (ex. lançamento manual futuro, fora do
  escopo desta extração): a linha do tempo começa diretamente em
  "Cadastrado manualmente por [usuário] em [data]" — sem o evento ①,
  e com uma indicação clara de que não há um documento de origem
  associado (em vez de simplesmente omitir a etapa, o que pareceria um
  erro do sistema).

**Estados de erro**: arquivo de origem não está mais disponível para
visualização (ex. removido do armazenamento) — o evento ① permanece
na linha do tempo com seus metadados (página, confiança, texto bruto
arquivado no banco), mas o link "ver página original" mostra "Arquivo
de origem indisponível — os metadados extraídos continuam preservados
abaixo" em vez de simplesmente falhar.

**Estados de carregamento**: *skeleton* na linha do tempo enquanto a
cadeia é montada; spinner ao carregar o visualizador de página
original.

**Permissões**: Admin/Auditor. Pode-se liberar uma versão **resumida**
(sem o visualizador de página original e sem notas internas de revisão)
para Revisores consultarem o histórico dos próprios itens revisados —
parametrizável conforme necessidade operacional.

---

## Resumo de rastreabilidade entre telas

A sequência abaixo amarra os dez fluxos num único caminho operacional —
do upload do PDF até a entrega ao cliente, com a auditoria disponível a
qualquer momento como uma "saída lateral":

```
 1 Upload ──> 2 Processamento ──> 3 Fila de revisão ──┬──> 4 Correção/decisão item a item
                                                        │         (compara, edita, aprova,
                                                        │          rejeita, lote)
                                                        └──> 5 Aprovação para catálogo
                                                                     │
                                                                     ▼
                                          6 Consulta do catálogo ──> 7 Montagem de orçamento
                                                                     │
                                                                     ▼
                                                       8 Edição de item ──> 9 Exportação/visualização
                                                                                       │
        10 Auditoria de origem  <───────────────  acessível a partir de QUALQUER preço exibido
                                                   (catálogo, orçamento ou linha do tempo)
```
