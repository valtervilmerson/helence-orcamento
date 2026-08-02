# 09b · Correção — filtro de dimensão do Catálogo (transbordo em tablet)

> **Complemento ao [09-catalogo-consulta.md](09-catalogo-consulta.md).**
> Aplicar **depois** que a tela 09 estiver implementada. Se a 09 ainda não
> existe no código, implemente-a primeiro — este documento corrige o filtro
> de dimensão dela, não substitui a tela.
>
> **Arquivos entregues junto com este documento:**
> `arquivos/ConsultaPage.tsx` (substituição integral) e as substituições de
> CSS descritas na seção 3.

## 1 · O defeito

Os `raw_label` reais do catálogo são três eixos concatenados —
`1370x700x740`, `1800x1000x740`, `2000x1200x740`. Em IBM Plex Mono 12px isso
dá ~95px de texto; com `padding:5px 7px` e borda, cada chip mede **~110px**.

A barra de filtros tem `width:234px` menos `padding:24px 18px` = **198px
úteis**. Dois chips (110 + 6 + 110 = 226px) não cabem, então
`.dimension-chips` colapsa para **uma coluna**. Só a Linha Noar tem mais de
50 combinações distintas de dimensão: **cerca de 1.500px de chips
empilhados**, numa tela de 834px de altura.

Agrava o quadro que `.catalog-filters` não tem altura contida nem
`overflow-y`: a coluna estica a página inteira, o cabeçalho "Catálogo" e a
tabela de resultados saem da viewport, e o usuário precisa rolar 1.500px de
filtro para voltar ao conteúdo.

## 2 · A correção

**Dimensão não é um valor atômico, são três eixos** — e a tabela `dimensions`
já os guarda separados (`width_mm`, `depth_mm`, `diameter_mm`, `height_mm`).
O vendedor procura "uma mesa de 1800 de largura", nunca "1800x1000x740".

O grupo único vira um **seletor de dois níveis**:

```
DIMENSÃO                                    1800 × 1000
  1 · Largura (mm)
  [600] [1000] [1200] [1370]
  [1400] [1600] [1800] [2000]
  [2200] [2400] [3000] [3700]

  2 · Medida completa
  [1800 × 800  h 740]
  [1800 × 900  h 740]
  [1800 × 1000 h 740]
```

O chip de eixo mede ~46px — cabem 4 por linha. Enquanto nenhuma largura for
escolhida, o passo 2 não é renderizado (só uma frase de orientação).

Somam-se três medidas de contenção:

- barra de filtros `position:sticky` + `height:100vh` + `overflow-y:auto`;
- cada grupo vira um `<details>`, aberto apenas se for "Linha" ou se tiver
  filtro ativo, com o valor ativo resumido no cabeçalho do grupo;
- alvo de toque dos chips sobe de 24px para 34px.

### Limite conhecido

O chip de largura é um **redutor da lista**, não um filtro enviado à API:
`searchComponents` só aceita `dimension` como `raw_label` completo. O
usuário escolhe a largura para encontrar a medida, e é a medida que filtra.

⚠ **NOVO PARÂMETRO (opcional, melhora o fluxo):** aceitar `width_mm`,
`depth_mm` e `height_mm` em `GET /catalog/components`. Com isso, "todas as
peças com 1800 de largura" passa a ser um filtro real: basta enviar
`widthPick` na consulta e o passo 2 vira opcional. Não é bloqueante — a
correção acima funciona inteira sem tocar no backend.

## 3 · Como aplicar

### 3.1 · Substituir a página

Copiar `arquivos/ConsultaPage.tsx` sobre
`frontend/src/pages/catalog/consulta/ConsultaPage.tsx`.

O arquivo é a versão completa da tela 09 já com a correção. Mudanças em
relação à versão anterior:

| O quê | Detalhe |
|---|---|
| `listDimensions()` tipado como `Dimension[]` | passa a usar `width_mm`, não só `raw_label` |
| estado `widthPick` | passo 1 do seletor; não é enviado à API |
| `splitMeasure()` | quebra `1800x1000x740` em `1800 × 1000` + altura `740` |
| `FilterGroup` | virou `<details>` com `<summary>`, prop `ativo` e prop `aberto` |
| `FilterButton` | ganhou `type="button"` e `aria-pressed` |
| cabeçalho da barra | novo bloco `.catalog-filters__head` com botão "Limpar" |
| coluna Dimensão da tabela | usa `.catalog-measure` com a altura como sufixo |
| `clear()` | também zera `widthPick` |

### 3.2 · Seis substituições em `frontend/src/index.css`

Todas no bloco `.catalog-page` (linha 1088 na versão de referência).
Nenhuma outra linha do arquivo muda.

**(a) Conter a barra de filtros na altura da tela**

Procurar:
```css
.catalog-filters{width:234px;flex:0 0 234px;padding:24px 18px;border-right:1px solid var(--borda);background:var(--superficie)}
```
Substituir por:
```css
.catalog-filters{position:sticky;top:0;align-self:flex-start;width:234px;flex:0 0 234px;height:100vh;overflow-y:auto;overscroll-behavior:contain;padding:20px 18px 28px;border-right:1px solid var(--borda);background:var(--superficie)}.catalog-filters__head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}.catalog-filters__clear{border:0;background:transparent;color:var(--verde-600);font:600 12px var(--fonte-ui);cursor:pointer;padding:2px}
```

**(b) Grupos colapsáveis**

Procurar:
```css
.filter-group{display:grid;gap:8px;margin-top:20px}
```
Substituir por:
```css
.filter-group{display:grid;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--linha)}.filter-group>summary{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:34px;list-style:none;cursor:pointer}.filter-group>summary::-webkit-details-marker{display:none}.filter-group>summary::after{content:"⌃";color:var(--tinta-4);font-size:12px;transform:rotate(180deg);transition:transform .15s ease}.filter-group[open]>summary::after{transform:rotate(0deg)}.filter-group>summary em{overflow:hidden;max-width:104px;color:var(--verde-600);font:600 11px var(--fonte-ui);font-style:normal;text-align:right;text-overflow:ellipsis;white-space:nowrap}
```

**(c) O rótulo do grupo passou para dentro do `<summary>`**

O seletor antigo deixa de casar. Procurar:
```css
.filter-group>b{font-size:12px;text-transform:uppercase;color:var(--tinta-4)}
```
Substituir por:
```css
.filter-group summary b{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--tinta-4)}
```

**(d) Seletor de dimensão em dois níveis**

Procurar:
```css
.dimension-chips button{padding:5px 7px;border:1px solid var(--borda-forte);border-radius:8px;font:12px var(--fonte-mono)}
```
Substituir por:
```css
.dimension-step{display:grid;gap:7px;margin-top:4px}.dimension-step>small{color:var(--tinta-4);font:600 11px var(--fonte-ui)}.dimension-axis{display:flex;flex-wrap:wrap;gap:5px}.dimension-axis button{min-width:46px;min-height:34px;padding:0 8px;border:1px solid var(--borda-forte);border-radius:8px;text-align:center!important;font:12px var(--fonte-mono)}.dimension-chips button{display:flex;align-items:center;gap:5px;min-height:34px;padding:0 9px;border:1px solid var(--borda-forte);border-radius:8px;font:12px var(--fonte-mono)}.dimension-chips button i{color:var(--tinta-4);font:10px var(--fonte-mono);font-style:normal}.dimension-axis button.is-active,.dimension-chips button.is-active{border-color:var(--verde-600);background:var(--verde-100)}.dimension-hint{margin:2px 0 0;color:var(--tinta-4);font-size:11px;line-height:1.45}
```

**(e) Coluna "Dimensão" da tabela**

`1800x1000x740` em mono 12,5px ocupa ~98px numa coluna de 116px, sem folga.
A coluna vai a 132px (tirando 18px do SKU). Procurar:
```css
grid-template-columns:1fr 168px 116px 132px 122px
```
Substituir por:
```css
grid-template-columns:minmax(0,1fr) 150px 132px 128px 122px
```

E acrescentar logo depois de `.catalog-no-price{color:var(--erro)}`:
```css
.catalog-measure{display:flex;align-items:baseline;gap:5px}.catalog-measure small{color:var(--tinta-4);font:10px var(--fonte-mono)}
```

**(f) Desfazer a contenção abaixo de 850px**

Em retrato a barra vira uma faixa no topo e não deve continuar sticky.
Procurar:
```css
.catalog-filters{width:auto;border-right:0;border-bottom:1px solid var(--borda)}
```
Substituir por:
```css
.catalog-filters{position:static;width:auto;height:auto;overflow:visible;border-right:0;border-bottom:1px solid var(--borda)}
```

## 4 · Resultado esperado

| | antes | depois |
|---|---|---|
| Chips de dimensão visíveis de uma vez | ~50, em 1 coluna | 13 larguras em ~4 linhas |
| Altura do grupo "Dimensão" | ~1.500px | ~190px |
| Altura da barra de filtros | estica a página inteira | contida em 100vh, rolagem própria |
| Grupos abertos ao entrar | 4 | 1, mais os que tiverem filtro ativo |
| Alvo de toque dos chips | 24px | 34px |

## 5 · Critérios de aceite

- [ ] Em 1194 × 834, a barra de filtros inteira cabe na tela sem rolar a página.
- [ ] O cabeçalho "Catálogo" e a primeira linha de resultados ficam visíveis
      com qualquer combinação de filtros aberta.
- [ ] O grupo "Dimensão" nunca mostra mais de ~15 chips de largura de uma vez.
- [ ] Escolher uma largura revela apenas as medidas daquela largura; trocar
      de largura limpa a medida escolhida antes.
- [ ] Cada grupo fechado mostra no cabeçalho o filtro ativo dentro dele.
- [ ] Nenhum chip de filtro tem menos de 34px de altura.
- [ ] Abaixo de 850px de largura a barra vira faixa no topo e volta a rolar
      junto com a página.
