# Como adicionar este patch ao pacote `entrega-redesign-helence`

Este pacote contém **um documento novo** e **um arquivo de código** que se
encaixam no pacote de redesign já existente. Não substitui nada do que já
está lá.

## Passo 1 — copiar os arquivos

Copie o conteúdo de `docs/` deste pacote para dentro de
`entrega-redesign-helence/docs/`, preservando a subpasta:

```
entrega-redesign-helence/
└── docs/
    ├── 09-catalogo-consulta.md              (já existe, não mexer)
    ├── 09b-correcao-filtro-dimensao.md      ← NOVO
    └── arquivos/
        └── ConsultaPage.tsx                 ← NOVO
```

## Passo 2 — registrar no índice

Em `entrega-redesign-helence/docs/README.md`, na tabela "Ordem de
implementação recomendada", inserir uma linha logo abaixo da linha 09:

```markdown
| 09b | [Correção: filtro de dimensão do Catálogo](09b-correcao-filtro-dimensao.md) | 09 |
```

## Passo 3 — apontar o complemento na tela 09

No topo de `entrega-redesign-helence/docs/09-catalogo-consulta.md`, logo
abaixo do cabeçalho, acrescentar:

```markdown
> ⚠ Esta tela tem um complemento obrigatório:
> [09b — Correção do filtro de dimensão](09b-correcao-filtro-dimensao.md).
> O filtro de dimensão descrito aqui transborda a tela do tablet com os
> dados reais do catálogo; implemente a 09 e aplique a 09b em seguida.
```

## Passo 4 — remover este arquivo

`COMO-INTEGRAR.md` é instrução de montagem do pacote, não de implementação.
Depois de integrar, apague-o — o agente que for aplicar o redesign não
precisa dele.

---

## Resumo para quem for aplicar

O documento 09b corrige um transbordo real: o filtro de dimensão do catálogo
renderiza ~50 chips de `1800x1000x740` numa coluna de 198px, gerando ~1.500px
de altura numa tela de 834px, e a barra de filtros não tem contenção — ela
estica a página e empurra a tabela de resultados para fora da viewport.

A correção troca o filtro por um seletor de dois níveis (largura → medida),
torna os grupos colapsáveis e contém a barra em `100vh`. É toda em frontend;
o único item de backend citado é opcional e está marcado como tal.
