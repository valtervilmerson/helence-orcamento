"""Spike: comparar pypdf, pdfplumber, pymupdf (fitz) e camelot numa amostra de 3 paginas:
 - pagina 1  = indice (texto livre, layout fora do padrao tabular)
 - pagina 2  = tabela "simples" (Tampo Inteiro, layout regular, 9 colunas de acabamento)
 - pagina 432 = tabela "complexa" (Reuniao Redonda, layout diferente, 1 codigo+preco por linha,
                presenca de issues conhecidas tipo 'codigo sem preco')

Objetivo: decidir qual lib e mais adequada para o MVP e documentar qualidade por tipo de dado.
"""
import time

PDF = r"C:\projects\codex\helence\helence-orcamento\data\source.pdf"
PAGES = {"indice": 1, "simples": 2, "complexa": 432}

print("#" * 90)
print("1) pypdf -- extract_text()")
print("#" * 90)
import pypdf
t0 = time.time()
reader = pypdf.PdfReader(PDF)
for label, pno in PAGES.items():
    text = reader.pages[pno - 1].extract_text() or ""
    print(f"\n--- pypdf | {label} (pag {pno}) | {len(text)} chars | tempo acumulado {time.time()-t0:.2f}s ---")
    print(text[:600])

print("\n" + "#" * 90)
print("2) pdfplumber -- extract_text() + extract_table()/extract_tables()")
print("#" * 90)
import pdfplumber
t0 = time.time()
with pdfplumber.open(PDF) as pdf:
    for label, pno in PAGES.items():
        page = pdf.pages[pno - 1]
        text = page.extract_text() or ""
        print(f"\n--- pdfplumber TEXT | {label} (pag {pno}) | {len(text)} chars ---")
        print(text[:500])
        tables = page.extract_tables()
        print(f"--- pdfplumber TABLES | {label}: {len(tables)} tabela(s) detectada(s) ---")
        for ti, tb in enumerate(tables[:1]):
            print(f"   tabela {ti}: {len(tb)} linhas x {len(tb[0]) if tb else 0} colunas. Primeiras 4 linhas:")
            for row in tb[:4]:
                print("     ", row)
print(f"tempo pdfplumber: {time.time()-t0:.2f}s")

print("\n" + "#" * 90)
print("3) pymupdf (fitz) -- get_text() variants + find_tables()")
print("#" * 90)
import fitz
t0 = time.time()
doc = fitz.open(PDF)
for label, pno in PAGES.items():
    page = doc[pno - 1]
    text_plain = page.get_text("text")
    text_words = page.get_text("words")  # lista (x0,y0,x1,y1,"word",block,line,word_no)
    print(f"\n--- pymupdf TEXT | {label} (pag {pno}) | {len(text_plain)} chars | {len(text_words)} 'words' com coordenadas ---")
    print(text_plain[:500])
    print("   amostra de 'words' com coordenadas (5 primeiras):")
    for w in text_words[:5]:
        print("     ", [round(v, 1) if isinstance(v, float) else v for v in w])
    try:
        tabs = page.find_tables()
        print(f"   find_tables(): {len(tabs.tables)} tabela(s) detectada(s)")
        if tabs.tables:
            tb = tabs.tables[0]
            data = tb.extract()
            print(f"      tabela 0: {len(data)} linhas x {len(data[0]) if data else 0} colunas. Primeiras 3 linhas:")
            for row in data[:3]:
                print("       ", row)
    except Exception as e:
        print("   find_tables() falhou:", type(e).__name__, e)
print(f"tempo pymupdf: {time.time()-t0:.2f}s")

print("\n" + "#" * 90)
print("4) camelot -- read_pdf(flavor='stream') e flavor='lattice'")
print("#" * 90)
import camelot
for label, pno in PAGES.items():
    print(f"\n--- camelot | {label} (pag {pno}) ---")
    for flavor in ("stream", "lattice"):
        try:
            t0 = time.time()
            tables = camelot.read_pdf(PDF, pages=str(pno), flavor=flavor)
            dt = time.time() - t0
            print(f"   flavor={flavor}: {len(tables)} tabela(s) em {dt:.2f}s")
            if len(tables):
                df = tables[0].df
                print(f"      shape={df.shape}, accuracy={tables[0].parsing_report.get('accuracy')}, whitespace={tables[0].parsing_report.get('whitespace')}")
                print(df.head(3).to_string())
        except Exception as e:
            print(f"   flavor={flavor}: ERRO {type(e).__name__}: {e}")
