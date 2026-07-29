# 11 · Importações (`/importacoes`)

**Arquivo:** `pages/importacoes/ImportacoesPage.tsx`
(evolução de `pages/imports/upload/ImportsPage.tsx`)
**DC:** `telaInicial: 'import'`

## Cabeçalho

Sobrelinha mono "Catálogo & preços" + `<h1>` serif 28px "Importações".

## Bloco superior — `grid-template-columns: 1fr 1fr; gap:16px`

### Esquerda · Zona de upload
Card `--superficie` com **borda tracejada 1.5px `#C7CFC8`**, raio 16,
`padding:26px`, coluna centralizada:
- quadrado 46×46 raio 13 `--verde-050` com ícone de seta para cima
  (stroke `--verde-600`);
- **"Solte o JSON da tabela aqui"** 15px 600;
- 13px `--tinta-3`, máx. 320px: *"Gerado pelo agente de extração a partir
  das planilhas do fabricante."*;
- `Botao secundario` "Escolher arquivo" (`accept=".json"` — só JSON, o
  caminho de PDF foi descontinuado na UI).

Estado *arrastando*: borda `--verde-600`, fundo `--verde-050`.
Estado *enviando*: barra de progresso + "Processando 131 itens…".
Erro de contrato: faixa `--erro-bg` **listando os campos inválidos**, não
"JSON inválido" genérico.

### Direita · Fila de revisão (o que trava a publicação)
Card `#FFFDF7`, borda `--atencao-borda`, raio 16:
- "Fila de revisão" 15px 600 + "7 bloqueando publicação" em mono `--atencao`;
- barra de progresso 7px (`--verde-600` sobre `#F0E5CB`);
- frase: *"124 de 131 itens já revisados na importação **01-2026 · Linha
  Noar**."*;
- duas amostras dos itens mais críticos, cada uma com selo de confiança
  (`baixa` = `--erro-bg`/`--erro`; `média` = `--atencao-bg`/`--atencao`),
  descrição curta e link "Revisar";
- `Botao` fundo `--atencao` de largura total: **"Abrir fila de revisão · 7"**
  → `/importacoes/:id/revisao` (doc 12).

Este card só aparece para `importador`/`revisor`/`admin` e some quando não
há itens bloqueando (troca por um card `--verde-050`: *"Nada aguardando
revisão. A importação pode ser publicada."* + botão "Publicar importação",
habilitado só para admin).

## Histórico

Card raio 16, grid `1fr 130px 118px 150px 150px`:
Arquivo · Tabela (mono) · Itens (mono, direita) · Enviado (`28/07 · 09:12`)
· `<Selo>` de situação.

Mapeamento de `ImportListItem.status`:

| status | Selo | tom |
|---|---|---|
| `recebido` / `processando` | "Processando" | atenção |
| `concluido` com itens bloqueando | "Em revisão" | atenção |
| `concluido` publicado | "Publicada" | ok |
| `erro` | "Erro no arquivo" | erro |

Menu `⋯` por linha: *Revisar · Publicar importação (admin, só se nada
bloqueia) · Excluir (só não publicada)* — mesmas regras de hoje.

## Critérios de aceite

- [ ] O seletor de arquivo aceita apenas `.json`.
- [ ] Erro de contrato lista os campos com problema.
- [ ] O caminho para a fila de revisão é a ação mais evidente da tela.
