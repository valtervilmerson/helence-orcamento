"""Spike: sheet5 (raw_rows) tem um token XML invalido (provavelmente um caractere de controle
vindo do texto cru extraido do PDF). Vamos sanitizar removendo caracteres de controle invalidos
para XML 1.0 e then conseguir ler uma amostra -- isso evidencia como o texto do PDF vem 'sujo'."""
import zipfile
import re
import xml.etree.ElementTree as ET

PATH = r"C:\projects\codex\helence\helence-orcamento\data\prices.xlsx"
z = zipfile.ZipFile(PATH)
ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

raw = z.read("xl/worksheets/sheet5.xml")
text = raw.decode("utf-8", errors="replace")

# Caracteres de controle invalidos em XML 1.0 (fora de \t \n \r e >= 0x20, exceto faixa valida)
bad_iter = list(re.finditer(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text))
print(f"Caracteres de controle invalidos encontrados: {len(bad_iter)}")
codepoints = {}
for m in bad_iter[:50]:
    cp = ord(m.group())
    codepoints[cp] = codepoints.get(cp, 0) + 1
    if len(codepoints) <= 10 and codepoints[cp] == 1:
        pos = m.start()
        print(f"  codepoint U+{cp:04X} em pos {pos}: contexto={text[max(0,pos-60):pos+10]!r}")
print("Contagem por codepoint (amostra):", codepoints)

# Sanitiza: remove os caracteres de controle invalidos
clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

def iter_rows_from_text(xml_text):
    root = ET.fromstring(xml_text)
    for row in root.iter(ns + "row"):
        vals = []
        for c in row:
            is_elem = c.find(ns + "is")
            v_elem = c.find(ns + "v")
            if is_elem is not None:
                t_elem = is_elem.find(ns + "t")
                vals.append(t_elem.text if t_elem is not None else "")
            elif v_elem is not None:
                vals.append(v_elem.text)
            else:
                vals.append(None)
        yield vals

print("\n--- Amostra de raw_rows (apos sanitizacao) ---")
for i, row in enumerate(iter_rows_from_text(clean)):
    print(f"  L{i+1}: {row}")
    if i >= 25:
        break
