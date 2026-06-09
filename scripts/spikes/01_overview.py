"""Spike descartavel: visao geral do PDF (paginas, texto bruto por pagina, tamanho)."""
import pypdf

PATH = r"C:\projects\codex\helence\helence-orcamento\data\source.pdf"

reader = pypdf.PdfReader(PATH)
print(f"Numero de paginas: {len(reader.pages)}")
print(f"Metadata: {reader.metadata}")

# Imprime o texto das primeiras 6 paginas e de algumas paginas do meio/fim
sample_pages = list(range(0, 6)) + [len(reader.pages)//2, len(reader.pages)//2 + 1, len(reader.pages) - 2, len(reader.pages) - 1]
sample_pages = sorted(set(p for p in sample_pages if 0 <= p < len(reader.pages)))

for i in sample_pages:
    text = reader.pages[i].extract_text() or ""
    print("=" * 80)
    print(f"PAGINA {i+1} (tamanho texto: {len(text)} chars)")
    print("-" * 80)
    print(text[:2500])
