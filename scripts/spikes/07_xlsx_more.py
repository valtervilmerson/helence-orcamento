"""Spike: completar a investigacao do prices.xlsx (extracao previa) -- olhar raw_rows
(amostra de como o texto foi agrupado por coordenada Y) e os registros do grupo hibrido
'TAMPOS / ESTRUTURAS / APOIO' (indicativo de pagina/secao dificil de classificar)."""
import zipfile
import re
import xml.etree.ElementTree as ET

PATH = r"C:\projects\codex\helence\helence-orcamento\data\prices.xlsx"
z = zipfile.ZipFile(PATH)
ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def iter_rows(sheet_file):
    with z.open(sheet_file) as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag == ns + "row":
                vals = []
                for c in elem:
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
                elem.clear()

print("=" * 80)
print("ABA raw_rows -- amostra (15 primeiras linhas)")
for i, row in enumerate(iter_rows("xl/worksheets/sheet5.xml")):
    print(f"  L{i+1}: {row}")
    if i >= 15:
        break

print("\n" + "=" * 80)
print("produtos_mcp -- amostra de registros com grupo HIBRIDO 'TAMPOS / ESTRUTURAS / APOIO'")
gen = iter_rows("xl/worksheets/sheet1.xml")
header = next(gen)
idx = {col: i for i, col in enumerate(header)}
shown = 0
modelos_base_hibrido = {}
paginas_hibrido = set()
for row in gen:
    if row[idx["grupo"]] == "TAMPOS / ESTRUTURAS / APOIO":
        modelos_base_hibrido[row[idx["modelo_base"]]] = modelos_base_hibrido.get(row[idx["modelo_base"]], 0) + 1
        paginas_hibrido.add(row[idx["pagina_pdf"]])
        if shown < 6:
            print(" ", row)
            shown += 1

print(f"\nPaginas com grupo hibrido: {sorted(paginas_hibrido, key=int)[:10]} ... total {len(paginas_hibrido)} paginas")
print(f"Modelos base distintos no grupo hibrido: {modelos_base_hibrido}")
