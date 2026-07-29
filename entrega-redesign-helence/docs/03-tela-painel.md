# 03 · Painel (rota `/`)

**Arquivo novo:** `frontend/src/pages/painel/PainelPage.tsx`
**DC:** `telaInicial: 'painel'`

Hoje a raiz redireciona para `/orcamentos`. O vendedor abre o sistema e vê
uma lista sem hierarquia. O Painel responde três perguntas em 5 segundos:
*o que está parado comigo, quanto tem em jogo, e o que fazer agora.*

## Layout

Área rolável, `padding: 30px 34px`.

### 1. Saudação
- `Terça, 28 de julho` — mono 11px, uppercase, `letter-spacing:.13em`, `--tinta-4`.
- `Bom dia, {primeiro nome}` — serif 30px 600 `--verde-900`.
  Regra: <12h "Bom dia", <18h "Boa tarde", senão "Boa noite".
- À direita: `Botao primario lg` **"+ Novo orçamento"** (46px, raio 12,
  sombra `--sombra-md`) → abre o modal de novo orçamento (doc 04).

### 2. Quatro cartões de métrica (`grid-template-columns: repeat(4,1fr); gap:14px`)

| Cartão | Fonte do dado | Destaque |
|---|---|---|
| Em rascunho | `listQuotes` filtrado `status==='rascunho'` | contagem + soma dos totais |
| Com o cliente | `status==='enviado'` | contagem + soma |
| Aprovados · {mês} | `status==='aprovado'` e `updated_at` no mês | número em `--verde-600` |
| Expira em 7 dias | `valid_until` entre hoje e hoje+7, status `enviado` | borda `--atencao-borda`, rótulo e número em `--atencao` |

Cartão: `--superficie`, borda 1px `--borda`, raio 14, `padding:16px 18px`,
coluna com `gap:8px`. Rótulo uppercase 12px 600 `--tinta-4`; número serif
34px 600; legenda 12.5px `--tinta-3`.

⚠ `listQuotes` hoje **não** devolve o total de cada orçamento. Duas saídas,
nesta ordem de preferência:
1. `⚠ NOVO ENDPOINT` `GET /api/v1/quotes/summary` devolvendo
   `{ por_status: {status: {count, total}}, expirando_7d: [...], pendencias: [...] }`;
2. fallback aceitável: buscar `getTotals` em paralelo para os orçamentos
   listados (limitar a 30) e somar no cliente.

### 3. "Precisa de você" (coluna esquerda, `grid: 1.35fr 1fr; gap:18px`)

Card com cabeçalho "Precisa de você" + contador mono à direita.
Cada linha é um `<button>` de largura total, `padding:13px 20px`, borda
superior `#EFEEE8`, hover `--papel-alt`:

```
● [cor]  ORC-2026-0184 · Grupo Sanders        Resolver →
         Uma linha está sem componente obrigatório — falta a estrutura.
```

Ponto 8px: `--erro` para bloqueio de envio, `--atencao` para alerta.

Regras de geração (ordem de prioridade):
1. Orçamento em rascunho com `item.missing_required_components.length > 0`
   → "Uma linha está sem componente obrigatório" → `/orcamentos/:id/itens`.
2. Orçamento com desconto acima da alçada sem justificativa → `/condicoes`.
3. Orçamento `enviado` com `valid_until` em ≤5 dias → "sem resposta há N
   dias" → `/orcamentos/:id/revisao`.
4. Item de importação bloqueando publicação (só para revisor/admin)
   → `/importacoes/:id/revisao`.

Máximo 5 linhas. Vazio: `<Vazio titulo="Nada parado com você"`
`descricao="Todos os orçamentos estão com o cliente ou finalizados."`.

### 4. "Funil do mês" (coluna direita)

Quatro barras: Rascunho, Com o cliente, Aprovado, Perdido/expirado.
Trilho 7px raio 4 `#EFEEE8`; preenchimento proporcional ao **maior** valor
do conjunto. Cores: `#C9CFC9`, `#7FA891`, `--verde-600`, `#D9B7B0`.
Rodapé com borda tracejada: "Taxa de aprovação" + valor serif 20px
(= aprovados ÷ (aprovados+recusados+expirados) no mês).

### 5. "Atividade recente"

Card com grid `148px 1fr 130px 118px 128px`: Número (mono 13px) · Cliente ·
Total (mono, direita) · Atualizado ("há 12 min", relativo) · `<Selo>`.
Máximo 3 linhas, ordenado por `updated_at`. Cabeçalho do card tem link
"Ver todos" → `/orcamentos`.

## Estados

- **Carregando:** `<Esqueleto>` nos 4 cartões e 3 linhas em cada lista.
- **Erro:** faixa `--erro-bg` no topo com "Tentar novamente".
- **Usuário sem papel de vendedor** (revisor puro): esconder cartões de
  funil e mostrar no lugar o card de fila de revisão do doc 11.

## Critérios de aceite

- [ ] `/` não redireciona mais para `/orcamentos`.
- [ ] Cada linha de "Precisa de você" navega para a tela que resolve o problema.
- [ ] Saudação muda conforme a hora.
