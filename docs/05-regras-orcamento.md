# Regras de negócio — montagem de orçamento

> Documento de regras (não de implementação) que define **como um
> orçamento deve ser montado** a partir do catálogo normalizado
> proveniente da tabela de preços. Construído sobre:
> `docs/01-auditoria-pdf-dominio.md` (entidades e riscos do domínio),
> `docs/02-spike-extracao-pdf.md` + `docs/samples/extracao-amostra.json`
> (dados reais verificados), `docs/03-modelagem-sqlite.md` (modelo de
> dados/tabelas referenciadas) e `docs/04-ux-operacional.md` (telas onde
> cada regra se manifesta).
>
> Convenção: cada regra é identificada como **RN-NN** (Regra de
> Negócio). Onde a regra depende de uma decisão comercial ainda não
> confirmada, isso é dito explicitamente — e revisitado na seção final
> "Perguntas de validação pendentes".

---

## 1. Os componentes de um item de orçamento

Um "item final" de orçamento (ex. "Mesa de Reunião 1200×900 —
Carvalho/Prata") é, na prática, uma **composição** de componentes
vendáveis independentes — cada um com seu próprio SKU e preço (ver
auditoria, seção 5, pergunta 1). Os tipos identificados até aqui:

| Componente | Papel típico | Observação de modelagem |
|---|---|---|
| **Tampo** | Estrutural — a superfície da mesa | 9 acabamentos "madeirados"; descritor (`Simples`/`Encabeçado`/`Bi-Partido`/`Tri-Partido`) varia por largura |
| **Estrutura** | Estrutural — sustenta o tampo | 3 acabamentos "metálicos"; descritor deve **casar** com o do tampo (RN-04) |
| **Apoio/Credenza** | Complementar — aparador lateral | Vendido com código/preço próprios, acompanhando a largura da mesa principal |
| **Pé** | Ambíguo — ver nota abaixo | Em mesas redondas, parece ser o componente de sustentação (`"Pé Painel"`, `"Pé Disco"`); em mesas retangulares, aparece como **atributo do descritor da Estrutura** (`"Alum Atto Fosco"`, `"Painel Diret"`) |
| **Acessório/Conector** | Opcional — combina módulos | Ex. "Conexão STAFF Componível Mod. Angular/Retangular/Trapezoidal"; dimensão em 3 eixos (LxPxA) |
| **Caixa de Tomada** | Possível *feature* do Tampo | Aparece apenas como **observação textual** no PDF (`"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"`) — não há evidência de SKU/preço próprios na amostra auditada |
| **Conjunto Completo** | Item fechado (mesas redondas/lounge) | Não é composto — é vendido como uma única unidade com um único SKU/preço |
| **Outros** | Categoria de extensão | Reservada para tipos que a tabela revelar fora da amostra auditada (ex. extensões, complementos específicos de outras famílias) |

> ⚠ **"Pé" e "Caixa de Tomada" têm status ambíguo na fonte** — as
> regras abaixo assumem o tratamento mais conservador para cada um (ver
> RN-04, RN-07 e RN-11) e marcam explicitamente onde uma decisão
> comercial é necessária antes de codificar o comportamento definitivo.

---

## 2. Regras de seleção e compatibilidade

### RN-01 — Seleção de família/linha
A montagem de um item começa pela escolha da **família/linha**
(`product_families` — ex. "Mesas de Reunião", "Mesas Redondas/Lounge").
Essa escolha é o primeiro filtro e **determina o que aparece depois**:
- Em "Mesas de Reunião", o fluxo segue o modo de **composição**
  (Tampo + Estrutura [+ Apoio/Acessórios]).
- Em "Mesas Redondas/Lounge", o catálogo indica que os itens são
  vendidos como **conjunto fechado** — o fluxo de composição não se
  aplica (ou se aplica de forma muito mais restrita — ver RN-07).

Um único orçamento pode conter linhas de **famílias diferentes** (ex.
uma mesa de reunião retangular + uma mesa redonda de apoio); cada
*linha* (`quote_item`), porém, pertence a exatamly uma família/produto.

### RN-02 — Seleção de dimensão
A dimensão é escolhida no nível do **produto-base** (`products` — ex.
"Reunião 1200×900") e propaga-se como padrão para todos os componentes
da composição:
- Famílias retangulares: largura × profundidade (ex. `1200×900`).
- Famílias redondas/lounge: diâmetro (ex. `900MM`).
- Acessórios/conectores: podem ter dimensão própria em 3 eixos
  (LxPxA), independente da dimensão do produto-base ao qual se associam.

**Regra dura**: só são **selecionáveis** dimensões que de fato existem
no catálogo publicado — isto é, que têm ao menos uma
`component_variant` com preço vigente associada. O sistema nunca expõe
uma combinação "teórica" de medidas; a lista de opções é sempre
derivada do que a tabela de preços realmente contém (evita o usuário
escolher "1100×950" só porque parece um valor plausível).

### RN-03 — Compatibilidade entre profundidade, largura e componente
Nem todo tipo de componente está disponível para toda combinação de
medidas. A auditoria confirmou, por exemplo, que os descritores
`Bi-Partido`/`Tri-Partido` de tampo concentram-se nas **larguras
maiores** (faixa de ~250 páginas do bloco "larguras grandes"), o que
sugere que essas variantes simplesmente **não existem** para mesas
estreitas.

**Regra**: a lista de componentes/descritores oferecida ao usuário para
uma dada dimensão é **sempre filtrada pela existência real** de
`component_variant` + preço para aquela combinação — nunca uma lista
fixa e universal. Isso transforma "compatibilidade entre dimensão e
componente" de uma regra a *codificar manualmente* em uma simples
*consulta ao catálogo já publicado* (ver `docs/03-…`, consulta 6.1) —
o que é, ao mesmo tempo, mais simples de manter e impossível de ficar
desatualizado em relação à tabela vigente.

> A **largura mínima** a partir da qual `Bi-Partido`/`Tri-Partido`
> passam a existir não está documentada de forma explícita no PDF —
> emerge apenas da observação de quais combinações têm preço. A regra
> acima já lida corretamente com isso sem precisar conhecer o limiar
> exato (ver pergunta de validação 1).

### RN-04 — Compatibilidade entre tampo e estrutura
Esta é a regra **central** da composição — e a que mais depende de uma
convenção que o PDF sugere, mas não declara explicitamente.

**Regra proposta** (a partir da nomenclatura observada — ex. uma
observação real na amostra diz *"Para Estrutura Reunião"* logo após o
nome de um tampo, e a auditoria identificou tanto `"Estrutura Reunião
Tampo Inteiro"` quanto `"Estrutura Reunião Tampo Tri-Partido"` como
itens distintos): **o descritor do Tampo determina qual descritor de
Estrutura é compatível** — ex. `Tampo Inteiro` requer `Estrutura
Reunião Tampo Inteiro`; `Tampo Tri-Partido` requer `Estrutura Reunião
Tampo Tri-Partido`. Ao escolher o tampo, o sistema:
1. **Pré-seleciona** a estrutura compatível (reduz erro/esforço); e
2. **Bloqueia** (ou, no mínimo, exige confirmação textual explícita
   com aviso de risco) combinações fora dessa correspondência — ex.
   tentar combinar `Tampo Bi-Partido` com `Estrutura ... Tampo Inteiro`.

Como o PDF **não declara** essa correspondência de forma estruturada
(ela é inferida da convenção de nomes), recomenda-se que o cadastro
dessa relação vire um **dado de configuração explícito** — não uma
heurística de *string matching* em produção — para que a área comercial
possa revisá-la e ajustá-la sem depender de uma releitura do PDF (ver
pergunta de validação 1).

### RN-05 — Compatibilidade entre acabamento selecionado e SKU disponível
A auditoria confirmou **dois universos de acabamento disjuntos** + um
terceiro específico de "pé":
- **Tampo**: 9 acabamentos "madeirados" (`Argila, Branco, Preto,
  Gianduia, Amêndoa, Carvalho, Nogueira Cádiz, Grafite, Itapuã`).
- **Estrutura**: 3 acabamentos "metálicos" (`Prata, Preto, Branco`).
- **Pé** (quando aplicável): conjunto próprio e mais variado (`Aço
  5050, Painel, Alum Atto Fosco/Polido/Preto/Branco/Brilhante, Painel
  Diret`).

**Regra (em duas camadas, ambas obrigatórias — uma sozinha não basta)**:
1. **Filtro por grupo**: o seletor de acabamento mostra apenas opções
   cujo `finish_group` é compatível com o `component_id` selecionado —
   nunca oferecer "Carvalho" para uma Estrutura nem "Prata" para um
   Tampo. Essa é uma restrição **física** (o fabricante não produz a
   combinação), não apenas comercial.
2. **Verificação de existência real**: mesmo dentro do grupo correto, o
   sistema confirma que existe de fato uma `component_variant` com
   `prices` para a combinação exata (componente + dimensão + descritor
   + acabamento) na tabela vigente — porque o **nome** de um acabamento
   pode existir no catálogo geral de `finishes` sem que exista uma
   variação vendável específica para a dimensão escolhida. Falhar nessa
   checagem aciona o tratamento de "item sem preço" (RN-12), nunca uma
   adição silenciosa com dado incompleto.

### RN-06 — Preço por acabamento
**Regra**: o preço **não** é uma propriedade do componente em geral —
é uma propriedade da combinação **completa** componente + dimensão +
descritor + acabamento + versão de tabela (a entidade `prices`,
amarrada a `component_variants`). A amostra real confirma isso
concretamente: o mesmo "Tampo Inteiro Simples 1200×900" custa
`R$ 382,75` em "Argila", `R$ 374,45` em "Branco" e `R$ 493,80` em
"Preto"/"Carvalho"/"Nogueira Cádiz" — diferenças de **até ~24%** dentro
do mesmo produto, dependendo só do acabamento.

Consequência prática: **trocar o acabamento de um componente já
selecionado é, na prática, trocar de variação inteira** — o sistema
deve reconsultar o preço do zero (não "ajustar" o valor anterior por
algum fator), e — se o componente já estiver num orçamento — tratar
isso como um evento de recongelamento explícito (RN-16, e tela 8 de
`docs/04-…`).

### RN-07 — Componente obrigatório versus opcional
**Regra proposta** (composição mínima vendável — ainda pendente de
confirmação comercial, ver pergunta de validação 4):

| Componente | Em "Mesas de Reunião" (composição) | Em "Mesas Redondas/Lounge" (conjunto fechado) |
|---|---|---|
| Tampo | **Obrigatório** | *(não se aplica — embutido no conjunto)* |
| Estrutura | **Obrigatório** | *(não se aplica — embutido no conjunto)* |
| Apoio/Credenza | Opcional | Opcional |
| Pé | *(embutido no descritor da Estrutura)* | **Obrigatório** — é o componente de sustentação do conjunto |
| Acessório/Conector | Opcional (usado para unir módulos) | Opcional |
| Caixa de Tomada | *(feature embutida — sem evidência de seleção própria)* | *(idem)* |

**Regra de finalização**: uma linha de orçamento só pode ser
considerada "completa" quando todos os componentes marcados como
obrigatórios para aquele modo de composição estiverem presentes — o
sistema impede o avanço para a tela de revisão final (RN-18) enquanto
houver linha incompleta, e aponta exatamente o que falta ("Esta linha
está sem Estrutura selecionada").

### RN-08 — Quantidade
**Regra de propagação**: a quantidade é definida primariamente no nível
da **linha lógica** (`quote_item` — "quero 2 destas mesas"), e
**multiplica** a quantidade de cada componente que a compõe (2 mesas →
2 tampos + 2 estruturas + 2 apoios, automaticamente).

**Exceção controlada**: alguns componentes são vendidos com lógica de
quantidade **independente** da contagem de "mesas" — o caso mais claro
é o **Acessório/Conector**: o número de conectores necessários depende
de quantos módulos estão sendo unidos, não de quantas mesas existem na
linha. Para esses casos, o sistema permite **sobrescrever** a
quantidade propagada — de forma explícita e visível (não "escondida"
dentro do componente), para que o vendedor sempre saiba que está diante
de uma exceção à regra padrão.

**Validação**: quantidade é sempre um inteiro positivo (mínimo 1);
reduzir a zero é tratado como remoção (com confirmação), nunca como
"linha com quantidade zero".

### RN-09 — Desconto
> O PDF de origem **não contém** nenhuma informação de desconto — esta
> é, por definição, uma regra **comercial**, não uma regra derivada do
> catálogo. O texto abaixo é uma **proposta inicial de estrutura**,
> pendente de confirmação da área comercial (pergunta de validação 5).

**Regra proposta**:
1. Desconto pode ser aplicado em **dois níveis independentes**: por
   **linha** (`quote_item` — ex. "10% nesta mesa específica, por
   promoção") e/ou no **orçamento como um todo** (`quotes`/
   `quote_totals` — ex. "5% para pedidos acima de R$ 10.000").
2. Em cada nível, o desconto é expresso como **percentual OU valor
   fixo — nunca os dois ao mesmo tempo** (evita ambiguidade sobre a
   ordem de aplicação e sobre "desconto sobre desconto").
3. Todo desconto aplicado **exige uma justificativa registrada**
   (campo obrigatório) — não por burocracia, mas porque desconto afeta
   diretamente a margem (RN-10) e é exatamente o tipo de decisão que
   pode ser questionada depois ("por que este cliente recebeu 15% e
   aquele não?").
4. Faixas de aprovação (ex. "descontos acima de 10% exigem aprovação de
   um gestor") **podem existir**, mas não há evidência de regra
   formal — fica como pergunta de validação 5/10.

### RN-10 — Margem comercial (se aplicável)
> Assim como desconto, **margem não aparece no PDF** — ela depende de
> **custo**, um dado que não existe em nenhuma camada deste sistema
> (nem na fonte, nem no modelo de catálogo). Esta seção é
> deliberadamente uma **constatação de lacuna**, não uma regra pronta.

**Regra proposta** (condicional): **se** a área comercial decidir que o
sistema de orçamento deve calcular/exibir margem, isso exigiria (a)
incorporar um dado de **custo por variação** vindo de **outra fonte**
(o PDF é uma tabela de *venda*, não de custo) e (b) decidir se essa
informação é **visível ao vendedor** (para orientar até onde pode
descontar) ou **estritamente interna/gerencial**. Até essa decisão ser
tomada, a recomendação é **não modelar margem neste sistema** — tratá-
la, se necessário, num sistema financeiro/ERP separado que consulte os
preços de venda aqui publicados (pergunta de validação 6).

### RN-11 — Observações comerciais
Existem **duas origens** de observação, e a regra central é
**não misturá-las**:

1. **Observações do catálogo** (vindas da tabela de preço — ex.
   *"A Caixa de Tomada nos 1200x900 Tampos são centralizadas"*, blocos
   de *"DESCRIÇÃO TÉCNICA"*): são fatos declarados pelo fabricante,
   modelados como `business_rules` associadas a produto/componente/
   dimensão. **Regra**: quando o usuário seleciona uma combinação à
   qual essas observações se aplicam, elas **aparecem automaticamente**
   na linha do orçamento, em destaque visual de "informação do
   fabricante" — somente leitura, não editáveis pelo vendedor.
2. **Observações comerciais do vendedor** (texto livre — ex. "cliente
   pediu prazo de entrega estendido"): são específicas daquele
   atendimento/orçamento, inseridas manualmente, podendo existir tanto
   no nível da linha quanto do orçamento inteiro.

**Regra de apresentação**: no documento final exportado (tela 9 de
`docs/04-…`), as duas origens devem ser **visualmente distinguíveis**
("Observação do fabricante" vs. "Observação do vendedor") — confundir
as duas poderia, por exemplo, fazer parecer que o fabricante prometeu
algo que foi, na verdade, uma promessa pontual do vendedor (ou
vice-versa), com risco comercial real.

### RN-12 — Item sem preço
Caso **real e documentado**: a extração de referência encontrou
**45 ocorrências de "código sem preço"**, concentradas nas páginas
432–435 (seção de mesas redondas/lounge/conectores) — exatamente o
padrão reproduzido no exemplo 3 (seção 4) com o SKU `398101456`.

**Regra dura, sem exceção**: um componente **sem preço associado na
tabela vigente** não pode ser adicionado a um orçamento — em hipótese
alguma. A checagem ocorre **antes** da adição (não depois, como uma
falha de salvamento) e a mensagem ao vendedor é **específica e
acionável**: explica que se trata de uma lacuna conhecida do catálogo
(não um erro do sistema), e oferece alternativas (escolher outra
variação ou contatar o time responsável pelo catálogo).

**Regra de origem (camada de importação)**: itens com `price = NULL`
**não deveriam**, a rigor, ser publicados no catálogo com
`review_status = aprovado` — esse é, na verdade, um problema a ser
resolvido **antes** da publicação (telas 4/5 de `docs/04-…`). Se a área
de catálogo decidir publicá-los mesmo assim como "lacunas conhecidas
aguardando o fabricante", o sistema deve registrar esse *status*
explicitamente, para que a regra acima possa exibir uma explicação
precisa em vez de um genérico "sem preço disponível".

### RN-13 — Item sem SKU
O caso **espelhado** de RN-12: existe preço, mas não há código de
fabricação associado. A amostra auditada **não documentou nenhuma
ocorrência real** desse padrão específico (os 45 casos conhecidos são
todos do tipo "código sem preço", não o inverso) — mas a robustez do
sistema exige tratá-lo de forma simétrica, porque a consequência prática
é igualmente grave: **sem código, o item não pode ser fabricado/
encomendado**, mesmo que o preço esteja correto.

**Regra**: idêntica, em espírito, à RN-12 — bloqueio total na adição ao
orçamento, com mensagem específica para esta causa ("Este componente
tem preço cadastrado, mas não tem código de fabricação associado — não
pode ser incluído até que isso seja resolvido").

> Ambas as regras (RN-12/RN-13) derivam de uma **regra de integridade
> única e mais fundamental**: *"um componente só é cotável quando tem,
> simultaneamente, SKU válido E preço válido na tabela vigente"* — a
> distinção entre as duas é apenas qual metade está faltando, para que
> a mensagem ao usuário aponte exatamente a causa.

### RN-14 — Item importado mas ainda não revisado
**Regra estrutural** (garantida pelo desenho do pipeline em
`docs/03-…`/`docs/04-…`, não apenas por uma checagem em tempo de
montagem): um item permanece **invisível** para quem monta orçamentos
até que passe por todo o ciclo — extração → revisão/correção → **
aprovação e publicação no catálogo**. Não existe, na arquitetura
proposta, nenhum caminho pelo qual um `extracted_item` com
`review_status` diferente de `aprovado` chegue a virar uma
`component_variant`/`prices` consultável na tela de orçamento — a
publicação (tela 5) é o único portão de entrada para o catálogo.

Isso significa que esta regra, na prática, **não precisa ser
"verificada" no momento de montar o orçamento** — ela já foi garantida
estruturalmente antes. O único cenário em que ela precisaria de uma
decisão explícita é o seguinte:

> **E se um vendedor precisar urgentemente cotar algo de uma tabela
> ainda em revisão** (ex. cliente pede um preço de um produto que só
> existe na próxima versão, ainda não publicada)? A recomendação é:
> **não permitir por padrão**. Se a área comercial identificar uma
> necessidade real para isso, deveria ser um processo **excepcional,
> explícito e registrado** (ex. "cotação preliminar — sujeita a
> confirmação"), e não um modo paralelo de acesso ao catálogo em
> revisão (pergunta de validação 7).

### RN-15 — Uso de tabela de preço vigente
**Regra padrão**: todo novo orçamento é automaticamente ancorado à
versão de tabela marcada como **vigente** (`price_tables.status =
'vigente'`) no momento de sua criação — `quotes.price_table_id` é
preenchido pelo sistema, não escolhido pelo vendedor.

**Regra de exceção**: usar uma tabela **não-vigente** (arquivada) é uma
ação **deliberada e visível** — exige confirmação explícita e produz
uma nota permanente e visível no documento final ("Este orçamento foi
montado com base na tabela 01-2025, que não é mais a vigente"). Isso
evita que um orçamento pareça "atual" quando na verdade reflete preços
defasados.

**Regra do "orçamento de versão mista"** (cenário real e provável — ver
exemplo 4): como o congelamento (RN-16) ocorre **no momento em que cada
componente é adicionado**, é perfeitamente possível que um orçamento em
rascunho acumule itens adicionados **antes** e **depois** da troca da
tabela vigente — cada um congelado ao preço que valia no instante da
adição. O sistema deve **detectar e exibir esse cenário de forma
explícita** ("Este orçamento contém itens precificados em duas versões
de tabela diferentes: 01-2025 e 02-2025 — ver detalhes"), nunca deixar
isso "invisível" dentro de uma soma.

### RN-16 — Congelamento do preço no orçamento
Esta é, em conjunto com RN-12/13, a regra **mais sensível** do ponto de
vista de negócio — é o que garante ao cliente que o valor cotado **não
muda debaixo dele**.

**Regra**: no instante em que um componente é adicionado a uma linha de
orçamento, seu preço (`prices.amount`/`currency` da tabela vigente
naquele momento) é **copiado** — não referenciado — para
`quote_item_components.frozen_unit_price`/`frozen_currency`. Esse valor
copiado é, a partir desse instante, **o valor contratual do
orçamento**, e permanece estável mesmo que:
- a tabela de preço seja atualizada (nova versão publicada);
- o preço de catálogo daquela variação específica mude;
- o registro de catálogo de origem seja arquivado/removido.

**Regra de recongelamento controlado**: a única forma legítima de mudar
o valor de um componente já incluído é **trocar o que ele é**
(variação/acabamento/SKU — ver tela 8 de `docs/04-…`) — e isso sempre
**recongela** o valor a partir do preço de catálogo *atual*, mostrando
ao vendedor, lado a lado, o valor anterior e o novo, **antes** de
confirmar a troca.

**Regra do total**: `quote_totals` segue o mesmo princípio em nível
agregado — é um *snapshot* calculado e armazenado (não uma soma "ao
vivo"), gravado no momento em que o orçamento atinge um marco definido
(tipicamente, ao ser finalizado/enviado). Pode-se **recalcular** a
qualquer momento para fins de conferência — e, se o recálculo divergir
do snapshot, o snapshot **prevalece** (é o valor que já foi, ou está
prestes a ser, comunicado ao cliente).

### RN-17 — Duplicação de orçamento
**Decisão central a esclarecer ao usuário no próprio ato de duplicar**:
duplicar **copia a estrutura, mas repreça contra a tabela vigente
atual** — não é uma cópia fiel dos valores congelados.

**Justificativa da regra proposta**: duplicar um orçamento serve,
tipicamente, para começar uma **proposta nova e semelhante** (mesmo
cliente ou um parecido, configuração parecida) — não para reemitir
exatamente o mesmo documento (para isso já existem "reenviar"/
"exportar novamente" na tela 9). Se a duplicação simplesmesmente
copiasse os valores antigos, um orçamento duplicado meses depois
poderia exibir preços completamente defasados sem nenhum aviso.

**Regra de transparência obrigatória**: no momento de duplicar, o
sistema **avisa explicitamente** — "Este orçamento será duplicado com
os preços da tabela vigente (02-2025); os valores podem ser diferentes
do orçamento original (01-2025)" — e, se algum componente do orçamento
original **não existir mais** (ou não tiver preço) na tabela vigente,
trata isso exatamente como RN-12/13: sinaliza a linha como pendência a
resolver, em vez de omiti-la silenciosamente ou copiar um valor
inválido.

**Regra de rastreabilidade**: todo orçamento duplicado nasce como
`rascunho`, recebe um número novo e mantém uma referência ao orçamento
de origem — útil tanto para o vendedor ("de onde veio esta proposta?")
quanto para auditoria.

### RN-18 — Revisão manual antes de fechar orçamento
**Regra de portão de saída**: antes de um orçamento poder sair do
estado `rascunho` (ser enviado/finalizado), o sistema executa uma
checagem final e apresenta um **checklist explícito** — nunca um
simples botão "Finalizar" sem retaguarda. Itens verificados:

1. Toda linha tem **todos** os componentes obrigatórios para seu modo
   de composição (RN-07) — nenhuma "mesa sem estrutura".
2. Nenhum componente está com SKU ou preço ausente (RN-12/13) — estado
   estruturalmente impossível se RN-12/13 forem aplicadas
   corretamente, mas vale conferir antes do fechamento como rede de
   segurança final.
3. Cliente está definido; ao menos um item existe.
4. Eventuais descontos têm justificativa registrada (RN-09) e, se
   aplicável, aprovação (pergunta de validação 5/10).
5. Caso o orçamento misture versões de tabela (RN-15) ou utilize uma
   tabela não-vigente, o vendedor **reconheceu** esse fato
   explicitamente (não basta o aviso ter aparecido — precisa ter sido
   confirmado).

**Regra de bloqueio explicativo**: cada pendência aparece **nomeada e
acionável** ("Linha 2 está sem Estrutura selecionada — adicionar
agora") — nunca um agregado genérico do tipo "existem erros, corrija-os
e tente novamente".

---

## 3. Exemplos realistas

> Valores marcados como **(real, da amostra verificada)** vêm de
> `docs/samples/extracao-amostra.json`; valores marcados como
> **(ilustrativo)** são inventados apenas para completar o exemplo —
> não foram extraídos do PDF e não devem ser tratados como referência.

### Exemplo 1 — Orçamento simples: Tampo + Estrutura
**Cenário**: cliente "Studio Almeida Arquitetura" pede 2 mesas de
reunião retangulares de 1200×900, acabamento de tampo Carvalho e
estrutura Prata.

```
Orçamento #00231 — Studio Almeida Arquitetura — tabela-base: 01-2025

Linha 1 — "Reunião 1200x900 — Carvalho/Prata"           qtd. da linha: 2
  • Tampo Inteiro Simples — Carvalho
      SKU 3981144789 — R$ 493,80  (real, congelado)
  • Estrutura Reunião Tampo Inteiro — Prata
      SKU 398250071 (ilustrativo) — R$ 612,40 (ilustrativo, congelado)

  Subtotal da linha = (493,80 + 612,40) × 2 = R$ 2.212,40
```
**Regras demonstradas**: RN-01/02 (família "Mesas de Reunião",
dimensão 1200×900); RN-04 (descritor "Tampo Inteiro" casado com
"Estrutura Reunião Tampo Inteiro"); RN-06 (preço específico da
combinação componente+acabamento); RN-07 (composição mínima completa:
tampo + estrutura, ambos obrigatórios); RN-08 (quantidade da linha
propagada para os dois componentes); RN-16 (cada componente congelado
no momento da adição).

### Exemplo 2 — Orçamento com Apoio e Acessório
**Cenário**: o mesmo cliente decide adicionar um aparador lateral à
mesa principal e, em outra linha, um conjunto de mesas modulares que
precisam de conectores.

```
Linha 1 (continuação do exemplo 1) — adiciona componente opcional:
  • Apoio Credenza 5050 — Prata
      SKU 398250115 (ilustrativo) — R$ 318,90 (ilustrativo, congelado)
  Nova subtotal da linha = (493,80 + 612,40 + 318,90) × 2 = R$ 2.850,20

Linha 2 — "Conexão STAFF Componível Mod. Angular — Branco"   qtd.: 3
  • Acessório/Conector
      SKU 398435020 (ilustrativo) — R$ 187,50 (ilustrativo, congelado)
  Subtotal da linha = 187,50 × 3 = R$ 562,50

  ℹ Observação do fabricante (origem: catálogo, página 435):
    "Conectores STAFF — verifique a quantidade necessária conforme
    o número de módulos a unir."
```
**Regras demonstradas**: RN-07 (Apoio é opcional — adicionado por
escolha, não exigido para completar a linha); RN-08, exceção
controlada (quantidade do conector definida de forma independente —
"3", não "2× algo"); RN-11 (observação do catálogo exibida
automaticamente e marcada como vinda do fabricante, distinta de uma
nota do vendedor).

### Exemplo 3 — Item bloqueado por ausência de preço
**Cenário**: o vendedor tenta adicionar uma "Reunião Redonda 1100MM —
Pé Disco — Argila" a um orçamento — exatamente o caso real registrado
na amostra de extração da página 432 (`docs/samples/extracao-amostra.json`,
item de baixa confiança, `sku = "398101456"`, `price = null`).

```
[ Buscar no catálogo: "Reunião Redonda 1100MM" ]
  → Reunião Redonda 1100MM — Pé Disco — Argila
    SKU 398101456 · preço: — (indisponível na tabela 01-2025)
    [+ Adicionar]  ← desabilitado

  ⚠ Este item não pode ser adicionado: não há preço cadastrado para
    esta combinação na tabela vigente (01-2025). Esta é uma lacuna
    conhecida do catálogo (identificada durante a importação — caso
    "código sem preço", concentrado nas págs. 432–435), não um erro
    pontual. Selecione outra variação ou contate o time de catálogo.

  [Ver variações semelhantes disponíveis]   [Auditar este SKU →]
```
**Regras demonstradas**: RN-12 (bloqueio total e explicado, antes da
tentativa de adicionar — não depois); rastreabilidade ponta a ponta
(o mesmo SKU aparece, com o mesmo problema, desde o spike de extração
até a tela de orçamento — prova de que o "alerta de baixa confiança" da
importação se traduz, corretamente, num bloqueio comercial real).

### Exemplo 4 — Item com preço de versão antiga da tabela
**Cenário**: um orçamento foi iniciado em 20/05/2026, quando a tabela
**01-2025** ainda era a vigente. Um Tampo foi adicionado e congelado
naquele momento. Em 01/06/2026, a tabela **02-2025** é publicada e
passa a ser a vigente — com um novo preço para essa mesma variação. O
vendedor, em 03/06/2026, ainda com o orçamento em rascunho, adiciona um
**novo** componente.

```
Orçamento #00245 — ainda em rascunho

Linha 1 — adicionada em 20/05/2026 (tabela vigente then: 01-2025)
  • Tampo Inteiro Simples 1200x900 — Argila
      SKU 3981113028 — R$ 382,75  (real, congelado em 20/05/2026)
      preço atual no catálogo (tabela 02-2025, vigente desde 01/06): 
      R$ 412,90 (ilustrativo) — DIFERENTE do valor congelado acima

Linha 2 — adicionada em 03/06/2026 (tabela vigente then: 02-2025)
  • Apoio Credenza 5050 — Prata
      SKU 398250115 (ilustrativo) — R$ 341,20 (ilustrativo, já
      congelado pela tabela 02-2025 — preço "atual" no momento da adição)

  ⚠ Este orçamento contém itens precificados em DUAS versões de
    tabela diferentes — 01-2025 (linha 1) e 02-2025 (linha 2).
    Os valores de cada item permanecem os congelados no momento
    da adição e NÃO serão recalculados automaticamente. [ver detalhes]
```
**Regras demonstradas**: RN-15 (cada adição usa a tabela vigente *no
momento em que ocorre* — não há "uma tabela única" fixa para o
orçamento inteiro); RN-16 (o valor congelado da Linha 1 não muda
mesmo após a publicação da nova tabela — é exatamente o comportamento
contratual desejado); detecção e aviso explícito de "orçamento de
versão mista" (em vez de uma soma silenciosamente heterogênea).

---

## 4. Perguntas de validação pendentes

Estas perguntas **bloqueiam decisões de implementação** específicas —
cada uma referencia a(s) regra(s) que depende(m) dela:

1. **(RN-03, RN-04)** Existe, em alguma ficha técnica do fabricante,
   uma tabela explícita de "qual Estrutura serve para qual Tampo" e
   "a partir de qual largura existem variantes Bi-/Tri-Partido"? Ou
   essas correspondências devem ser **levantadas manualmente** (e
   formalizadas como dado de configuração) a partir da nomenclatura e
   da existência de preços?
2. **(RN-01, RN-07)** "Pé" é um **componente vendável independente**
   (equivalente, em mesas redondas, ao papel que a Estrutura tem nas
   retangulares) ou **sempre** um atributo/variante embutido no
   descritor da Estrutura? A resposta muda fundamentalmente o desenho
   da composição para a família "Mesas Redondas/Lounge".
3. **(RN-07, RN-11)** "Caixa de Tomada" tem **código e preço próprios**
   (é um item selecionável/opcional) ou é uma **característica
   embutida** no Tampo (sempre presente quando aplicável, sem custo
   adicional, e o texto do PDF é apenas uma instrução de montagem)?
   A amostra auditada só encontrou evidência do segundo cenário — mas
   isso precisa de confirmação comercial antes de travar a regra.
4. **(RN-07)** A composição mínima vendável é mesmo **Tampo +
   Estrutura** (com Apoio sempre opcional), ou existe alguma
   combinação em que um desses dois é dispensável (ex. cliente que já
   possui a estrutura e só quer comprar o tampo de reposição)?
5. **(RN-09, RN-18)** Existe uma **política formal de desconto**
   (faixas percentuais, valor máximo sem aprovação, quem aprova,
   se é por linha/orçamento/ambos)? Sem essa resposta, RN-09 permanece
   uma proposta de estrutura, não uma regra confirmada.
6. **(RN-10)** A área comercial espera que **este sistema** calcule ou
   exiba margem (o que exigiria importar/cadastrar dados de **custo**,
   inexistentes na fonte atual), ou margem é — e deve continuar sendo —
   tratada **fora** deste sistema (ex. ERP/financeiro)?
7. **(RN-14)** Existe necessidade real de **cotar a partir de uma
   tabela ainda em revisão** (não publicada) para atender pedidos
   urgentes? Se sim, que processo de exceção (aprovação, marcação
   explícita de "preço preliminar") deveria existir?
8. **(RN-17)** Ao duplicar um orçamento, a expectativa do usuário é
   "nova proposta semelhante, com preços atualizados" (proposta deste
   documento) ou "cópia fiel para reenvio" (o que mudaria
   completamente o comportamento de repreciação na duplicação)?
9. **(RN-13)** "Item sem SKU" já ocorreu **na prática** em alguma
   versão da tabela, ou é apenas uma simetria teórica de "item sem
   preço"? Vale levantar com a área técnica/comercial se esse padrão
   tem precedente real — isso ajuda a calibrar o quão "rara" essa
   trava deve ser tratada operacionalmente.
10. **(RN-09, RN-18)** Existe (ou deveria existir) um **segundo nível
    de aprovação interna** para orçamentos que apresentem
    características de risco — valor total elevado, desconto acima de
    um limiar, uso de tabela não-vigente, ou presença de itens
    corrigidos manualmente durante a importação? Se sim, quem aprova,
    e em que momento do fluxo (antes de enviar ao cliente, ou antes de
    confirmar o pedido)?
