# 09b · Correção — filtro de dimensão do Catálogo

> Complemento obrigatório de [09-catalogo-consulta.md](09-catalogo-consulta.md).

Os rótulos reais de dimensão, como `1800x1000x740`, não cabem como chips
atômicos no painel de filtros de 234 px. Com dezenas de medidas, a coluna
ficava com mais de uma tela de altura e empurrava os resultados para fora da
viewport de tablet.

## Implementação aplicada

- O filtro usa dois níveis: primeiro a **largura (mm)** e depois a medida
  completa daquela largura.
- A escolha da largura reduz somente a lista visível; o filtro enviado à API
  continua sendo o `raw_label` completo selecionado no segundo nível.
- Trocar a largura limpa a medida completa anterior.
- Os grupos de filtro usam `<details>`; Linha abre inicialmente e os grupos
  com filtro ativo permanecem abertos, mostrando o valor resumido no cabeçalho.
- O painel de filtros é `sticky`, tem `height:100vh` e rolagem própria em
  paisagem; abaixo de 850 px ele volta a ser uma faixa normal no topo.
- A coluna de dimensão usa o formato compacto `1800 × 1000` com altura como
  sufixo, preservando o valor completo em `title`.

## Critérios de aceite

- Em 1194 × 834, abrir os filtros não deve rolar a página inteira.
- O primeiro nível não deve renderizar mais que os chips de largura distintos.
- Cada chip de filtro mede pelo menos 34 px de altura.
- A medida completa é a única dimensão enviada à busca.
- Em tablet retrato, a barra deixa de ser sticky e rola junto com a página.

O suporte de API para `width_mm`, `depth_mm` e `height_mm` é opcional; não é
necessário para esta correção.
