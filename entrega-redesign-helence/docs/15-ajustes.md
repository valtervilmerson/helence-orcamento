# 15 · Ajustes (`/ajustes`)

**Arquivo:** `pages/ajustes/AjustesPage.tsx` (evolução de
`pages/settings/SettingsPage.tsx`)
**DC:** `telaInicial: 'ajustes'`

Acesso: `admin`. Duas colunas (`grid: 1fr 1fr; gap:16px`, máx. 900px).

## Card "Política comercial"

Lista de linhas com divisória `--linha`, rótulo 13.5px `--tinta-3` à
esquerda e valor em mono 14px à direita (clicável para editar inline):

| Rótulo | Campo | Observação |
|---|---|---|
| Margem padrão | `global_markup_percent` | usado pelo doc 07 |
| Alçada de desconto do vendedor | ⚠ **NOVO** `discount_limit_percent` | usado pelos docs 03, 07, 08 |
| Validade padrão da proposta | ⚠ **NOVO** `default_validity_days` | usado pelo doc 04 |

⚠ Os dois campos novos são pré-requisito para as regras de alçada e de
validade padrão. Se o backend não os tiver, criar em `settings` com os
padrões 8% e 30 dias. Enquanto não existirem, usar constantes no frontend
e marcar com `// TODO: mover para settings`.

## Card "Equipe"

Uma linha por usuário: avatar circular 34px com iniciais, nome 14px 600,
e-mail 12.5px `--tinta-4`, e `<Selo>` de papel à direita —
**Admin** usa fundo `--verde-900` com texto `--ouro-500` (o único selo
escuro do sistema, para marcar privilégio); os demais usam os tons padrão.

## Critérios de aceite

- [ ] Alterar a margem padrão reflete imediatamente no doc 07.
- [ ] Alçada e validade padrão existem como configuração, não como número
      escrito no código.
