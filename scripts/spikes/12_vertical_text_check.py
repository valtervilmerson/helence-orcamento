"""Spike: o extract_tables() do pdfplumber/camelot trouxe fragmentos estranhos e
"espelhados" (ex.: 'OCSOF' = 'FOSCO' ao contrario, 'OTERP' = 'PRETO' ao contrario,
'ETNAHLIRB' = 'BRILHANTE' ao contrario, 'OIN�MULA' = 'ALUMINIO' ao contrario)
misturados ao texto da pagina 2. Isso sugere texto rotacionado/vertical sendo
capturado pelo motor de deteccao de tabelas. Vamos confirmar usando pymupdf
em modo 'dict' (que expõe a matriz/direcao de cada span de texto).
"""
import fitz

PDF = r"C:\projects\codex\helence\helence-orcamento\data\source.pdf"
doc = fitz.open(PDF)
page = doc[1]  # pagina 2 (indice 0-based)

raw = page.get_text("rawdict")
rotated_spans = []
normal_spans = []
for block in raw["blocks"]:
    if block.get("type") != 0:
        continue
    for line in block["lines"]:
        direction = line.get("dir", (1.0, 0.0))
        text = "".join(span.get("text", "") for span in line.get("spans", []) if "text" in span)
        if not text and "chars" in str(line):
            pass
        # Reconstroi texto a partir de 'chars' quando 'text' nao existir (rawdict)
        if not text:
            text = "".join(
                ch.get("c", "")
                for span in line.get("spans", [])
                for ch in span.get("chars", [])
            )
        text = text.strip()
        if not text:
            continue
        # direcao (1,0) = horizontal da esquerda p/ direita; qualquer outra = rotacionado
        is_horizontal = abs(direction[0] - 1.0) < 1e-3 and abs(direction[1]) < 1e-3
        entry = (round(direction[0], 2), round(direction[1], 2), text[:60])
        if is_horizontal:
            normal_spans.append(entry)
        else:
            rotated_spans.append(entry)

print(f"Total de linhas de texto HORIZONTAIS (dir=(1,0)): {len(normal_spans)}")
print(f"Total de linhas de texto ROTACIONADAS (dir != (1,0)): {len(rotated_spans)}")
print("\n--- Amostra de linhas ROTACIONADAS encontradas na pagina 2 ---")
for d in rotated_spans[:30]:
    print("  dir=", d[:2], " texto=", repr(d[2]))

print("\n--- Conferindo se sao 'espelhos' de nomes de acabamento conhecidos ---")
conhecidos = ["FOSCO", "PRETO", "BRANCO", "BRILHANTE", "ALUMINIO", "ALUM�NIO", "PAINEL", "APOIO", "DIRET", "5050"]
for d in rotated_spans[:30]:
    txt = d[2].strip()
    rev = txt[::-1]
    hit_normal = [k for k in conhecidos if k.upper() == txt.upper()]
    hit_reversed = [k for k in conhecidos if k.upper() == rev.upper()]
    if hit_normal or hit_reversed:
        print(f"   '{txt}'  -> normal={hit_normal}  invertido={hit_reversed}  (texto invertido = '{rev}')")
