# Pasta de apoio — geração do JSON de importação

> Esta pasta é **autocontida**: reúna estes arquivos para orientar um
> chat/agente de IA externo que vai ler planilhas de origem (Excel) e
> gerar o JSON de importação consumido por
> `POST /api/v1/imports/json`. Não é necessário acesso ao restante do
> repositório.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `CONTRATO.md` | O contrato formal do JSON (campos, tipos, regra de fast path). **Leitura obrigatória** — é a fonte de verdade do formato de saída. |
| `GUIA-QUALIDADE-DADOS.md` | Checklist de "o que fazer / o que evitar" — problemas reais já enfrentados (encoding, nomes de acabamento, arredondamento, etc.). **Ler antes de gerar o JSON.** |
| `catalogo-atual.json` | Snapshot do catálogo já cadastrado no sistema (famílias, tipos de componente, acabamentos com `finish_group`, produtos). Use para decidir se uma entidade já existe (e portanto usar o **nome exato** cadastrado) ou se é nova. |
| `exemplo-importacao-reunioes.json` | Exemplo pequeno (12 itens) cobrindo fast path e os 3 tipos de revisão (componente novo, acabamento novo, produto novo, confiança ausente). Bom para entender a estrutura. |
| `exemplo-importacao-solucoes-acusticas.json` | Exemplo grande (304 itens) real, gerado a partir de uma planilha com layout irregular (grades, divisores, painéis). Bom para ver como lidar com planilhas "confusas". |

## Passo a passo recomendado

1. Leia `CONTRATO.md` por completo.
2. Leia `GUIA-QUALIDADE-DADOS.md` — principalmente a seção de encoding e a
   de acabamentos (`finish`), que já causaram retrabalho em importações
   anteriores.
3. Abra `catalogo-atual.json` e anote os nomes **exatos** de
   `product_families`, `product_components` e `finishes` já cadastrados.
4. Para cada planilha/aba de origem, mapeie: família, contexto de
   produto, tipo de componente, dimensão, acabamento, SKU, preço.
   - Sempre que o valor corresponder a algo já cadastrado em
     `catalogo-atual.json`, use o nome **exatamente** como está lá
     (mesma grafia, acentuação, maiúsculas/minúsculas, espaçamento).
   - Sempre que for um valor novo, está tudo bem — mas para `finish`
     novo é **obrigatório** informar `finish_group`
     (`madeirado|metalico|pe_estrutura|outro`).
5. Gere o JSON seguindo `CONTRATO.md`. Salve em UTF-8.
6. Antes de entregar, rode o checklist final de
   `GUIA-QUALIDADE-DADOS.md` (seção "Checklist final").

## Depois de gerar o JSON

O JSON é enviado para `POST /api/v1/imports/json`. Itens "limpos" (fast
path) são publicados automaticamente; os demais caem na fila de revisão
humana. Itens com acabamento **novo** (não presente em
`catalogo-atual.json`) sempre vão para revisão, e **a publicação da
tabela de preços só funciona depois que o acabamento novo for cadastrado
em `/catalog/finishes`** — combine com o time antes de gerar muitos
itens com acabamentos novos.
