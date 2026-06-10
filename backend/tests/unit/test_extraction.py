"""Testes unitários do parser de extração (docs/02, docs/07 Fase 5).

Usam listas sintéticas de `Word` com as mesmas coordenadas/relações
geométricas observadas no PDF real (docs/samples/extracao-amostra.json),
sem depender do arquivo `data/source.pdf` (esse é o teste `slow`).
"""

from app.imports.extraction import (
    Word,
    _normalize_price,
    extract_page_from_words,
)

# Centros das 9 colunas de acabamento, replicando o cabeçalho de 9 colunas
# observado no PDF (Argila..Itapuã, com "Nogueira"/"Cádiz" quebrado em 2 linhas).
_COLUMN_CENTERS = [254.5, 287.5, 319.0, 353.0, 389.5, 427.0, 481.35, 519.0, 559.0]


def _word(text: str, center: float, y0: float, width: float = 25.0) -> Word:
    half = width / 2
    return Word(x0=center - half, y0=y0, x1=center + half, y1=y0 + 6.5, text=text)


def _header_row(y0: float = 30.0) -> list[Word]:
    words = [
        _word("MODELO", 63.0, y0, width=24),
        _word("DESCRI��O", 184.0, y0, width=52),
    ]
    finishes = [
        "ARGILA",
        "BRANCO",
        "PRETO",
        "GIANDUIA",
        "AMENDOA",
        "CARVALHO",
        "NOGUEIRA",
        "GRAFITE",
        "ITAPUA",
    ]
    for center, text in zip(_COLUMN_CENTERS, finishes, strict=True):
        words.append(_word(text, center, y0))
    # "CADIZ" fica em uma 2a linha física, sobreposto em x ao "NOGUEIRA".
    words.append(_word("CADIZ", _COLUMN_CENTERS[6], y0 + 7.0))
    return words


def _column_row(values: list[str], y0: float) -> list[Word]:
    return [_word(v, center, y0) for center, v in zip(_COLUMN_CENTERS, values, strict=True)]


SKUS = [
    "3981113028",
    "3981121234",
    "3981130567",
    "3981138901",
    "3981142345",
    "3981144789",
    "3981146012",
    "3981148256",
    "3981149472",
]
PRICES = [
    "382,75",
    "374,45",
    "493,80",
    "472,85",
    "493,80",
    "493,80",
    "493,80",
    "472,85",
    "493,80",
]


def _other_word(text: str, x0: float, y0: float, width: float) -> Word:
    return Word(x0=x0, y0=y0, x1=x0 + width, y1=y0 + 6.5, text=text)


def test_tampo_padrao_page_produces_nine_items_matching_gabarito() -> None:
    rows: list[Word] = []
    rows += _header_row(y0=30.0)

    model_row = [
        _other_word("Reuni�o", 51.0, 50.0, 28.0),
        _other_word("1200x900", 81.0, 50.0, 36.0),
        _other_word("Tampo", 158.0, 50.0, 22.0),
        _other_word("Inteiro", 182.0, 50.0, 28.0),
        _other_word("Simples", 212.0, 50.0, 28.0),
    ]
    model_row += _column_row(SKUS, y0=50.0)
    rows += model_row

    rows += [_other_word("Para Estrutura Reuni�o", 30.0, 58.0, 90.0)]
    rows += [
        _other_word(
            "A Caixa de Tomada nos 1200x900 Tampos s�o centralizadas", 30.0, 66.0, 220.0
        )
    ]

    rows += _column_row(PRICES, y0=74.0)

    page = extract_page_from_words(rows, [], page_number=2)

    assert page.page_profile == "tampo_padrao"
    assert len(page.items) == 9

    argila = page.items[0]
    assert argila.finish_raw == "Argila"
    assert argila.sku_raw == "3981113028"
    assert argila.price_raw == "382.75"
    assert argila.confidence == 0.95
    assert argila.confidence_level == "alta"
    assert argila.dimension_raw == "1200x900"
    assert argila.product_context_raw == "Reunião 1200x900 Tampo Inteiro Simples"
    assert "Para Estrutura Reunião" in argila.description_raw
    assert "centralizadas" in argila.description_raw

    nogueira_cadiz = page.items[6]
    assert nogueira_cadiz.finish_raw == "Nogueira Cádiz"
    assert nogueira_cadiz.confidence == 0.85
    assert nogueira_cadiz.confidence_level == "alta"
    assert any("quebrado em mais de uma linha" in note for note in nogueira_cadiz.extraction_notes)


def test_vertical_text_is_isolated_into_raw_rows_only() -> None:
    rows: list[Word] = []
    rows += _header_row(y0=30.0)
    rows += [
        _other_word("Reuni�o", 51.0, 50.0, 28.0),
        _other_word("1200x900", 81.0, 50.0, 36.0),
    ]
    rows += _column_row(SKUS, y0=50.0)
    rows += _column_row(PRICES, y0=74.0)

    vertical = [
        Word(x0=125.1, y0=76.2, x1=131.4, y1=95.5, text="FOSCO"),
        Word(x0=125.1, y0=126.5, x1=131.4, y1=145.2, text="BRILHANTE"),
    ]

    page = extract_page_from_words(rows, vertical, page_number=2)

    assert any(r.is_vertical and r.text == "FOSCO" for r in page.raw_rows)
    assert any(r.is_vertical and r.text == "BRILHANTE" for r in page.raw_rows)
    assert any("texto vertical" in w for w in page.warnings)
    for item in page.items:
        assert "FOSCO" not in (item.description_raw or "")
        assert "BRILHANTE" not in (item.description_raw or "")


def test_redonda_lounge_pairs_sku_and_price_with_lower_confidence() -> None:
    rows: list[Word] = []
    rows += _header_row(y0=30.0)
    rows += [
        _other_word("Reuni�o Redonda 900MM", 51.0, 50.0, 90.0),
        _other_word("P� Painel", 158.0, 50.0, 40.0),
    ]
    rows += _column_row(SKUS[:1] + ["398091185"] + SKUS[2:], y0=50.0)
    rows += _column_row(PRICES, y0=74.0)

    page = extract_page_from_words(rows, [], page_number=432)

    assert page.page_profile == "redonda_lounge"
    assert len(page.items) == 9
    argila = page.items[0]
    assert argila.dimension_raw == "900MM"
    assert argila.confidence == 0.8
    assert argila.confidence_level == "media"
    assert any("page_profile" in note for note in argila.extraction_notes)


def test_codigo_sem_preco_is_recorded_with_low_confidence() -> None:
    rows: list[Word] = []
    rows += _header_row(y0=30.0)
    rows += [
        _other_word("Reuni�o Redonda 1100MM", 51.0, 50.0, 90.0),
        _other_word("P� Disco", 158.0, 50.0, 40.0),
    ]
    rows += _column_row(SKUS, y0=50.0)
    # Sem linha de preços depois do bloco de SKU.

    page = extract_page_from_words(rows, [], page_number=432)

    assert len(page.items) == 9
    item = page.items[0]
    assert item.sku_raw == "3981113028"
    assert item.price_raw is None
    assert item.confidence == 0.2
    assert item.confidence_level == "baixa"
    assert any("código sem preço" in note for note in item.extraction_notes)
    assert any("código sem preço" in w for w in page.warnings)


def test_indice_page_has_no_items() -> None:
    rows = [_other_word("�NDICE", 250.0, 92.4, 60.0)]
    rows += [
        _other_word(
            "MESAS DE REUNI�O ............................................. 2",
            250.0,
            140.1,
            300.0,
        )
    ]

    page = extract_page_from_words(rows, [], page_number=1)

    assert page.page_profile == "indice"
    assert page.items == []
    assert any("índice" in w.lower() for w in page.warnings)


def test_normalize_price_strips_internal_whitespace() -> None:
    normalized, notes = _normalize_price("744 ,22")

    assert normalized == "744.22"
    assert any("espaço espúrio" in n for n in notes)


def test_normalize_price_rejects_unparseable_value() -> None:
    normalized, notes = _normalize_price("abc")

    assert normalized is None
