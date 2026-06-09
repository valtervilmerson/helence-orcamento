"""Spike: olhar paginas especiais (fim de secao com 'descricao tecnica', secao redonda/componivel,
e tentar destrancar o mojibake comparando com o prices.xlsx que acompanha o PDF)."""
import pypdf

PATH = r"C:\projects\codex\helence\helence-orcamento\data\source.pdf"
reader = pypdf.PdfReader(PATH)

def show(page_num, limit=6000):
    text = reader.pages[page_num - 1].extract_text() or ""
    print("=" * 80)
    print(f"PAGINA {page_num} -- {len(text)} chars")
    print("-" * 80)
    print(text[:limit])

# Pagina de fim-de-secao (tem 'DESCRICAO TECNICA')
show(44)
# Paginas da secao redonda/lounge/componivel (estrutura de colunas pode variar)
show(432)
show(433)
