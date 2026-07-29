# 10 · Catálogo · administração (`/catalogo/admin`)

**Arquivos:** `pages/catalogo/admin/*` (evolução de
`pages/catalog/CatalogLayout.tsx`, `CatalogHomePage.tsx`, `families/`,
`products/`, `componentTypes/`, `dimensions/`, `finishes/`, `variants/`)
**DC:** `telaInicial: 'admin'`

Acesso restrito a `admin`. Hoje vive em `/catalogo` com sete abas de texto
(`.catalog-tabs`) e um grid de cards de contagem.

## Mudanças estruturais

1. A rota passa a ser `/catalogo/admin` — `/catalogo` é a consulta.
2. As **sete abas somem**. Visão geral e as seis entidades passam a conviver
   em **uma única tela**: os cards de entidade no topo funcionam como
   seletor, e a tabela abaixo mostra a entidade selecionada.
   Motivo: as cinco entidades pequenas (famílias, tipos, dimensões,
   acabamentos) têm 4 a 23 registros — não justificam uma rota cada.
3. `Variações vendáveis` (303 registros) é a entidade padrão ao entrar.

## Cabeçalho

- Sobrelinha mono "Cadastro · somente admin".
- `<h1>` serif 28px "Estrutura do catálogo".
- `Botao secundario` "Ir para a consulta" → `/catalogo`.
- Parágrafo 13.5px `--tinta-3`, máx. 640px: *"Famílias, produtos-base,
  tipos de componente, dimensões e acabamentos são as peças de montagem.
  As variações vendáveis são o que o vendedor realmente coloca num
  orçamento."*

## Cards de entidade

`grid-template-columns: repeat(3,1fr); gap:12px`. Card `--superficie`,
borda `--borda`, raio 14, `padding:15px 17px`, hover borda `--verde-200`
+ fundo `#FCFDFC`. Selecionado: borda 1.5px `--verde-600`, fundo
`--verde-050`.

Conteúdo: nome 14.5px 600 à esquerda, **contagem em serif 21px `--verde-900`
à direita**, descrição 12.5px `--tinta-3` embaixo. Textos (manter os do
`CatalogHomePage` atual):

| Entidade | Descrição |
|---|---|
| Famílias de produto | Agrupamentos de alto nível: Mesas de Reunião, Plataformas, Bistrô, Soluções Acústicas. |
| Produtos-base | Produtos dentro de uma família, com uma dimensão associada. |
| Tipos de componente | Peças que compõem um produto: tampo, estrutura, painel, apoio. |
| Dimensões | Medidas reutilizadas pelos produtos: largura, profundidade, diâmetro, altura. |
| Acabamentos | Cores e materiais, agrupados por tipo (madeirado, metálico, pé/estrutura). |
| Variações vendáveis | Combinações finais com SKU e preço — é o que entra no orçamento. |

## Tabela da entidade selecionada

Card raio 16. Cabeçalho: nome da entidade 15.5px 600 + subtítulo explicando
a chave (para variações: *"produto + componente + dimensão + acabamento,
com SKU e preço"*), e `Botao primario` "+ Nova {entidade}".

Colunas para **Variações vendáveis**
(`128px 1fr 138px 116px 128px 120px 92px`):

Componente · Descritor · SKU (mono) · Dimensão (mono) · Acabamento ·
Preço (mono, direita) · botão "Editar".

Variação sem preço: célula em `--erro` com o texto "sem preço".

Rodapé: "Mostrando N de M variações" à esquerda e, à direita, a frase
**"Toda edição aqui exige justificativa e fica no histórico."**

Paginação de 25 (`PAGE_SIZE` atual de `VariantsPage`).

## Edição

O formulário inline expandido dentro da linha (comportamento atual do
`EditVariantForm`) é substituído por uma `<Gaveta>` de 560 px à direita,
com os mesmos campos e a mesma chamada `updateComponent`:

Tipo de componente* · Produto-base · Dimensão · Acabamento · Descritor ·
Descrição · SKU · Preço (BRL)

Acrescentar um campo **obrigatório** "Motivo da alteração", enviado junto
(`⚠ campo novo no PATCH`, ou registrado no log de auditoria existente).
Rodapé da gaveta: "Cancelar" · "Salvar alteração".

Excluir usa `<ConfirmDialog>` tom perigo, informando quantos orçamentos já
usam aquela variação (o congelamento os protege — dizer isso no texto:
*"Orçamentos existentes não são afetados: eles guardam o preço congelado."*).

## Critérios de aceite

- [ ] Nenhuma aba de texto (`.catalog-tabs` apagado).
- [ ] Trocar de entidade não muda a rota nem recarrega a página inteira.
- [ ] Edição de variação exige motivo.
