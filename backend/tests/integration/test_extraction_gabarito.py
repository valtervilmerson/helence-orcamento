"""Teste lento: compara a extração do PDF real contra o gabarito de
referência (docs/samples/extracao-amostra.json, docs/02, docs/07 Fase 5).

Os SKUs do gabarito são ilustrativos (docs/02) — o real `data/source.pdf`
tem códigos diferentes para as mesmas posições. Por isso este teste verifica
**estrutura, perfis de página, preços e níveis de confiança** (que batem
exatamente com o PDF real), não os valores de SKU.
"""

from pathlib import Path

import fitz
import pytest

from app.imports.extraction import extract_page

SOURCE_PDF = Path(__file__).resolve().parents[3] / "data" / "source.pdf"

pytestmark = pytest.mark.skipif(not SOURCE_PDF.exists(), reason="data/source.pdf não disponível")


@pytest.fixture(scope="module")
def document():
    doc = fitz.open(SOURCE_PDF)
    yield doc
    doc.close()


@pytest.mark.slow
def test_page_1_is_indice_with_no_items(document) -> None:
    extraction = extract_page(document.load_page(0), page_number=1)

    assert extraction.page_profile == "indice"
    assert extraction.items == []
    assert extraction.raw_rows
    assert any("índice" in w.lower() for w in extraction.warnings)


@pytest.mark.slow
def test_page_2_matches_gabarito_first_item(document) -> None:
    extraction = extract_page(document.load_page(1), page_number=2)

    assert extraction.page_profile == "tampo_padrao"

    argila = extraction.items[0]
    assert argila.finish_raw == "Argila"
    assert argila.price_raw == "382.75"
    assert argila.dimension_raw == "1200x900"
    assert argila.confidence == 0.95
    assert argila.confidence_level == "alta"
    assert "Reunião 1200x900" in argila.product_context_raw

    finishes = [item.finish_raw for item in extraction.items[:9]]
    assert finishes == [
        "Argila",
        "Branco",
        "Preto",
        "Gianduia",
        "Amêndoa",
        "Carvalho",
        "Nogueira Cádiz",
        "Grafite",
        "Itapuã",
    ]

    nogueira_cadiz = extraction.items[6]
    assert nogueira_cadiz.confidence == 0.85
    assert nogueira_cadiz.confidence_level == "alta"

    prices = [item.price_raw for item in extraction.items[:9]]
    assert prices == [
        "382.75",
        "374.45",
        "493.80",
        "472.85",
        "493.80",
        "493.80",
        "493.80",
        "472.85",
        "493.80",
    ]


@pytest.mark.slow
def test_page_432_is_redonda_lounge_with_codigo_sem_preco(document) -> None:
    extraction = extract_page(document.load_page(431), page_number=432)

    assert extraction.page_profile == "redonda_lounge"

    argila = extraction.items[0]
    assert argila.finish_raw == "Argila"
    assert argila.dimension_raw == "900MM"
    assert argila.price_raw == "534.16"
    assert argila.confidence == 0.8
    assert argila.confidence_level == "media"

    sem_preco = [item for item in extraction.items if item.price_raw is None]
    assert len(sem_preco) > 0
    for item in sem_preco:
        assert item.confidence == 0.2
        assert item.confidence_level == "baixa"
        assert any("código sem preço" in note for note in item.extraction_notes)

    assert any("código sem preço" in w for w in extraction.warnings)
