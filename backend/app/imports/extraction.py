"""Pipeline de extração de PDF (docs/02-spike-extracao-pdf.md, docs/07 Fase 5).

Estratégia validada no spike: usar `pymupdf` (fitz) para obter os tokens de
texto com coordenadas (`get_text("words")`) e reconstruir linhas/colunas a
partir delas — em vez de depender de "tabelas prontas" (`find_tables()`),
que embaralham o corpo da tabela em mega-células.

Layout reconhecido (perfil "tampo_padrao" / "redonda_lounge"):
- uma linha de cabeçalho com "MODELO", "DESCRIÇÃO" e 9 nomes de
  acabamento — cada nome define a posição (x) de uma das 9 colunas;
- para cada produto, um bloco de linhas onde a linha do "modelo" também
  carrega 9 códigos (SKU) alinhados às colunas do cabeçalho, e uma linha
  posterior carrega 9 preços alinhados às mesmas colunas;
- linhas que não se alinham às 9 colunas são texto livre (nome do
  modelo/dimensão, observações) e viram `description_raw`.

Esta fase **não** tenta extrair perfeitamente — itens cujo código não tem
preço pareado (ou vice-versa) são gravados com `confidence_level='baixa'` e
`price_raw=None`, e a página gera um aviso. Isso é o comportamento
**correto**, não uma falha (docs/07, Fase 5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz

# ---------------------------------------------------------------------------
# Dicionários de domínio — corrigem o `U+FFFD` que substitui acentos em 100%
# das páginas (docs/02, seção 5.1) e a falta de acentuação em maiúsculas.
# ---------------------------------------------------------------------------

_DOMAIN_TERMS = {
    "REUNI�ES": "Reuniões",
    "REUNI�O": "Reunião",
    "Reuni�o": "Reunião",
    "DESCRI��O": "Descrição",
    "s�o": "são",
    "S�O": "São",
    "P�": "Pé",
    "Pain�l": "Painel",
    "Encabe�ado": "Encabeçado",
    "Pol�do": "Polido",
    "Alum�nio": "Alumínio",
    "ALUM�NIO": "Alumínio",
    "A�O": "Aço",
    "DIRET": "Direto",
}

# Nomes de acabamento do cabeçalho de 9 colunas, em maiúsculas/sem acento
# (como aparecem no PDF) -> nome canônico do domínio.
FINISH_DICTIONARY = {
    "ARGILA": "Argila",
    "BRANCO": "Branco",
    "PRETO": "Preto",
    "GIANDUIA": "Gianduia",
    "AMENDOA": "Amêndoa",
    "CARVALHO": "Carvalho",
    "NOGUEIRA CADIZ": "Nogueira Cádiz",
    "GRAFITE": "Grafite",
    "ITAPUA": "Itapuã",
}

SKU_PATTERN = re.compile(r"^\d{8,12}$")
PRICE_TOKEN_PATTERN = re.compile(r"^[\d.,\s]+$")
PRICE_VALUE_PATTERN = re.compile(r"^\d{1,3}(\.\d{3})*,\d{2}$")
DIMENSION_PATTERN = re.compile(
    r"\d{3,4}\s*[xX]\s*\d{3,4}(?:\s*[xX]\s*\d{2,4})?(?:\s*mm)?|\d{3,4}\s*MM|Diam\.?\s*\d{3,4}\s*mm",
    re.IGNORECASE,
)

# Linhas de cabeçalho repetidas em toda página — não viram raw_rows úteis.
_PAGE_HEADER_NOISE = {"*imagens", "meramente", "ilustrativas."}


def _fix_domain_text(text: str) -> str:
    for raw, fixed in _DOMAIN_TERMS.items():
        text = text.replace(raw, fixed)
    return text


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class RawRow:
    sequence_no: int
    y: float
    text: str
    is_vertical: bool = False


@dataclass
class ExtractedItemDraft:
    family_raw: str | None
    product_context_raw: str | None
    component_type_raw: str | None
    description_raw: str | None
    dimension_raw: str | None
    finish_raw: str | None
    sku_raw: str | None
    price_raw: str | None
    currency: str
    confidence: float
    confidence_level: str
    source_text: str
    extraction_notes: list[str] = field(default_factory=list)


@dataclass
class PageExtraction:
    page_number: int
    section: str | None
    page_profile: str
    raw_rows: list[RawRow]
    items: list[ExtractedItemDraft]
    warnings: list[str]


@dataclass
class _Column:
    x0: float
    x1: float
    header_text: str
    header_merged: bool


def _is_vertical(word: tuple) -> bool:
    x0, y0, x1, y1, text = word[0], word[1], word[2], word[3], word[4]
    return (y1 - y0) > (x1 - x0) and len(text.strip()) >= 2


def _extract_words(page: fitz.Page) -> tuple[list[Word], list[Word]]:
    """Retorna (palavras horizontais, palavras verticais/rotacionadas).

    `get_text("words")` inclui rótulos verticais (ex. 'FOSCO' lido de baixo
    para cima — docs/02, seção 2.4) com caixas "em pé" (altura > largura).
    Eles são separados aqui para não poluir a reconstrução de linhas/colunas.
    """
    horizontal: list[Word] = []
    vertical: list[Word] = []
    for w in page.get_text("words"):
        word = Word(x0=w[0], y0=w[1], x1=w[2], y1=w[3], text=w[4])
        if _is_vertical(w):
            vertical.append(word)
        else:
            horizontal.append(word)
    return horizontal, vertical


def _group_rows(words: list[Word], tolerance: float = 2.0) -> list[list[Word]]:
    """Agrupa palavras em linhas por proximidade de `y0` (docs/02, seção 2.1)."""
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w.y0, w.x0)):
        if rows and abs(word.y0 - rows[-1][0].y0) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w.x0)
    return rows


def _row_text(row: list[Word]) -> str:
    return "  ".join(_fix_domain_text(w.text) for w in row)


def _detect_columns(rows: list[list[Word]]) -> tuple[int, list[_Column], set[int]] | None:
    """Localiza a linha de cabeçalho ('MODELO'/'DESCRIÇÃO' + 9 acabamentos).

    Também retorna os índices de linhas extras totalmente "consumidas" pelo
    cabeçalho (ex. a linha física que só contém 'CADIZ', a 2a parte de um
    cabeçalho de acabamento quebrado em duas linhas) — para que o loop
    principal não as trate como texto livre de descrição.
    """
    for row_index, row in enumerate(rows):
        texts = [w.text.upper() for w in row]
        if "MODELO" not in texts:
            continue
        descricao = next((w for w in row if w.text.upper().startswith("DESCRI")), None)
        if descricao is None:
            continue

        header_words = [w for w in row if w.x0 > descricao.x1]
        header_y = descricao.y0
        # Cabeçalhos quebrados em 2 linhas (ex. "NOGUEIRA"/"CADIZ") ficam a
        # poucos pontos de distância em y, mas alinhados em x.
        consumed_rows: set[int] = set()
        for other_row_index, other_row in enumerate(rows):
            if other_row is row:
                continue
            extra = [w for w in other_row if w.x0 > descricao.x1 and abs(w.y0 - header_y) <= 8]
            if extra and len(extra) == len(other_row):
                consumed_rows.add(other_row_index)
            header_words.extend(extra)

        header_words.sort(key=lambda w: w.x0)
        columns: list[_Column] = []
        for w in header_words:
            if columns and w.x0 <= columns[-1].x1 + 5:
                columns[-1].x1 = max(columns[-1].x1, w.x1)
                columns[-1].header_text += " " + w.text.upper()
                columns[-1].header_merged = True
            else:
                columns.append(
                    _Column(x0=w.x0, x1=w.x1, header_text=w.text.upper(), header_merged=False)
                )

        if len(columns) == 9:
            return row_index, columns, consumed_rows

    return None


def _column_index(word: Word, columns: list[_Column], tolerance: float = 12.0) -> int | None:
    for i, col in enumerate(columns):
        col_center = (col.x0 + col.x1) / 2
        if abs(word.x_center - col_center) <= tolerance:
            return i
    return None


def _normalize_price(raw_text: str) -> tuple[str | None, list[str]]:
    notes: list[str] = []
    cleaned = raw_text.replace(" ", "")
    if cleaned != raw_text:
        notes.append(
            f"preço extraído com espaço espúrio no texto bruto ({raw_text!r}); "
            "normalizado removendo espaços internos (docs/02, seção 2.2)"
        )
    if not PRICE_VALUE_PATTERN.match(cleaned):
        return None, notes
    normalized = cleaned.replace(".", "").replace(",", ".")
    return normalized, notes


def _resolve_finish(column: _Column) -> tuple[str, list[str]]:
    notes: list[str] = []
    canonical = FINISH_DICTIONARY.get(column.header_text)
    if canonical is None:
        canonical = column.header_text.title()
        notes.append(
            f"acabamento {column.header_text!r} não encontrado no dicionário do domínio; "
            "mantido em title-case sem correção de acentuação"
        )
    elif column.header_merged:
        notes.append(
            f"cabeçalho de acabamento veio quebrado em mais de uma linha física "
            f"({column.header_text!r}); resolvido como um nome único "
            f"({canonical!r}) via dicionário do domínio"
        )
    return canonical, notes


def _strip_leading_section_titles(lines: list[str]) -> list[str]:
    """Remove linhas iniciais "TUDO EM MAIÚSCULAS" (subtítulos de seção,
    ex. 'REUNIÃO TAMPO INTEIRO 1 CAIXA DE TOMADA') que precedem a linha do
    modelo/dimensão de um bloco de produto, mantendo ao menos uma linha.
    """
    result = list(lines)
    while len(result) > 1 and result[0] == result[0].upper() and result[0] != result[0].lower():
        result.pop(0)
    return result


def _section_title(rows: list[list[Word]]) -> str | None:
    for row in rows:
        texts = [w.text for w in row if w.text not in _PAGE_HEADER_NOISE]
        if texts:
            return _fix_domain_text(" ".join(texts))
    return None


def _detect_dimension(text: str) -> str | None:
    match = DIMENSION_PATTERN.search(text)
    return match.group(0) if match else None


def _profile_for_dimension(dimension: str | None) -> str:
    if dimension is None:
        return "desconhecido"
    if "x" in dimension.lower() and "mm" not in dimension.lower():
        return "tampo_padrao"
    return "redonda_lounge"


def extract_page(page: fitz.Page, page_number: int) -> PageExtraction:
    horizontal, vertical = _extract_words(page)
    return extract_page_from_words(horizontal, vertical, page_number)


def extract_page_from_words(
    horizontal: list[Word], vertical: list[Word], page_number: int
) -> PageExtraction:
    rows = _group_rows(horizontal)

    raw_rows: list[RawRow] = []
    seq = 0
    for row in rows:
        raw_rows.append(RawRow(sequence_no=seq, y=row[0].y0, text=_row_text(row)))
        seq += 1
    for word in sorted(vertical, key=lambda w: (w.y0, w.x0)):
        raw_rows.append(
            RawRow(sequence_no=seq, y=word.y0, text=_fix_domain_text(word.text), is_vertical=True)
        )
        seq += 1

    section = _section_title(rows)
    header = _detect_columns(rows)

    if header is None:
        page_profile = "indice" if page_number == 1 else "desconhecido"
        warnings = []
        if page_profile == "desconhecido":
            warnings.append(
                "Página não corresponde a nenhum perfil de layout conhecido "
                "(cabeçalho de 9 colunas de acabamento não encontrado)."
            )
        else:
            warnings.append(
                "Página de índice/texto livre — não contém linhas de produto/preço; "
                "'normalized_items' é intencionalmente vazio (docs/02, seção 3)."
            )
        return PageExtraction(
            page_number=page_number,
            section=section,
            page_profile=page_profile,
            raw_rows=raw_rows,
            items=[],
            warnings=warnings,
        )

    header_row_index, columns, consumed_rows = header

    finish_labels: list[str] = []
    finish_notes: list[str] = []
    for column in columns:
        label, notes = _resolve_finish(column)
        finish_labels.append(label)
        finish_notes.extend(notes)

    items: list[ExtractedItemDraft] = []
    warnings: list[str] = []
    if vertical:
        warnings.append(
            f"Confirmados {len(vertical)} span(s) de texto vertical (rótulos laterais) "
            "nesta página; isolados via filtro geométrico e mantidos em raw_rows "
            "apenas para registro — não compõem normalized_items (docs/02, seção 2.4)."
        )

    description_lines: list[str] = []
    pending_skus: dict[int, str] | None = None
    pending_dimension: str | None = None
    pending_description_lines: list[str] = []
    pending_source_lines: list[str] = []

    def _resolve_pending_dimension() -> None:
        nonlocal pending_dimension, family_raw
        if pending_dimension is not None:
            return
        dimension = _detect_dimension(" ".join(pending_description_lines))
        if dimension is None:
            return
        pending_dimension = dimension
        if family_raw is None:
            family_raw = (
                "Mesas de Reunião"
                if _profile_for_dimension(dimension) == "tampo_padrao"
                else "Mesas Redondas / Lounge"
            )

    def _flush_unmatched_block() -> None:
        if pending_skus is None:
            return
        _resolve_pending_dimension()
        description_lines_clean = _strip_leading_section_titles(pending_description_lines)
        for column_index, sku in pending_skus.items():
            finish_label = finish_labels[column_index]
            notes = list(finish_notes) + [
                "CASO 'código sem preço': nenhuma linha de preço foi localizada para "
                "este bloco de código (docs/02, seção 4 — caso documentado, "
                "concentrado nas páginas 432-435)",
                "price=null propositalmente; item NÃO deve ser publicado sem checagem "
                "manual contra o PDF original",
            ]
            items.append(
                ExtractedItemDraft(
                    family_raw=family_raw,
                    product_context_raw=description_lines_clean[0]
                    if description_lines_clean
                    else None,
                    component_type_raw=description_lines_clean[1]
                    if len(description_lines_clean) > 1
                    else None,
                    description_raw=" ".join(description_lines_clean) or None,
                    dimension_raw=pending_dimension,
                    finish_raw=finish_label,
                    sku_raw=sku,
                    price_raw=None,
                    currency="BRL",
                    confidence=0.2,
                    confidence_level="baixa",
                    source_text=" | ".join(pending_source_lines),
                    extraction_notes=notes,
                )
            )
        warnings.append(
            f"Detectado 'código sem preço' nesta página: {len(pending_skus)} código(s) "
            "sem linha de preço pareada na faixa de Y esperada."
        )

    family_raw: str | None = None

    for row_index, row in enumerate(rows):
        if row_index <= header_row_index or row_index in consumed_rows:
            continue

        column_words: dict[int, list[Word]] = {}
        other_words: list[Word] = []
        for word in row:
            col_idx = _column_index(word, columns)
            if col_idx is not None:
                column_words.setdefault(col_idx, []).append(word)
            else:
                other_words.append(word)

        other_text = _fix_domain_text(" ".join(w.text for w in other_words)).strip()

        if len(column_words) >= 7 and all(
            SKU_PATTERN.match("".join(w.text for w in ws)) for ws in column_words.values()
        ):
            _flush_unmatched_block()

            pending_skus = {
                idx: "".join(w.text for w in ws) for idx, ws in column_words.items()
            }
            pending_description_lines = description_lines + ([other_text] if other_text else [])
            description_lines = []
            pending_source_lines = [_row_text(row)]
            continue

        if (
            pending_skus is not None
            and len(column_words) >= 7
            and all(
                PRICE_TOKEN_PATTERN.match("".join(w.text for w in ws))
                for ws in column_words.values()
            )
        ):
            price_raws: dict[int, str] = {}
            block_notes: list[str] = []
            valid = True
            for idx, ws in column_words.items():
                raw_text = "".join(w.text for w in ws)
                normalized, notes = _normalize_price(raw_text)
                block_notes.extend(notes)
                if normalized is None:
                    valid = False
                    break
                price_raws[idx] = normalized

            if valid:
                if other_text:
                    pending_description_lines.append(other_text)
                pending_source_lines.append(_row_text(row))
                _resolve_pending_dimension()
                description_lines_clean = _strip_leading_section_titles(pending_description_lines)

                page_profile = _profile_for_dimension(pending_dimension)
                base_confidence = 0.95 if page_profile == "tampo_padrao" else 0.8
                if any("espaço espúrio" in n for n in block_notes):
                    base_confidence -= 0.1

                for column_index, sku in pending_skus.items():
                    finish_label = finish_labels[column_index]
                    item_notes = list(finish_notes) + list(block_notes)
                    confidence = base_confidence
                    if columns[column_index].header_merged:
                        confidence = min(confidence, 0.85)
                    if page_profile != "tampo_padrao":
                        item_notes.append(
                            "page_profile difere de 'tampo_padrao' (cabeçalho/posições "
                            "deslocados); pareamento sku/preço feito por proximidade "
                            "geométrica, não por rótulo explícito que os ligue"
                        )

                    confidence_level = (
                        "alta" if confidence >= 0.85 else "media" if confidence >= 0.5 else "baixa"
                    )
                    items.append(
                        ExtractedItemDraft(
                            family_raw=family_raw,
                            product_context_raw=description_lines_clean[0]
                            if description_lines_clean
                            else None,
                            component_type_raw=description_lines_clean[1]
                            if len(description_lines_clean) > 1
                            else None,
                            description_raw=" ".join(description_lines_clean) or None,
                            dimension_raw=pending_dimension,
                            finish_raw=finish_label,
                            sku_raw=sku,
                            price_raw=price_raws.get(column_index),
                            currency="BRL",
                            confidence=round(confidence, 2),
                            confidence_level=confidence_level,
                            source_text=" | ".join(pending_source_lines),
                            extraction_notes=item_notes,
                        )
                    )

                pending_skus = None
                pending_dimension = None
                pending_description_lines = []
                pending_source_lines = []
                continue
            # Linha não era realmente uma linha de preços válida — cai para texto livre.

        if other_text:
            if pending_skus is not None:
                pending_description_lines.append(other_text)
                pending_source_lines.append(_row_text(row))
            else:
                description_lines.append(other_text)

    _flush_unmatched_block()

    page_profile = "desconhecido"
    if items:
        page_profile = (
            "tampo_padrao"
            if any(_profile_for_dimension(i.dimension_raw) == "tampo_padrao" for i in items)
            else "redonda_lounge"
        )
    elif pending_skus or description_lines:
        warnings.append(
            "Página com cabeçalho de 9 colunas reconhecido, mas nenhum item completo "
            "foi extraído — possível layout fora do padrão."
        )

    return PageExtraction(
        page_number=page_number,
        section=section,
        page_profile=page_profile,
        raw_rows=raw_rows,
        items=items,
        warnings=warnings,
    )
