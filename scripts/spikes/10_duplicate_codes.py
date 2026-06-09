"""Spike: investigar codigos de produto duplicados na extracao previa -- sao o mesmo
componente reaproveitado em varias paginas (esperado) ou artefato de extracao?"""
import zipfile
import xml.etree.ElementTree as ET
import collections

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

gen = iter_rows("xl/worksheets/sheet1.xml")
header = next(gen)
idx = {col: i for i, col in enumerate(header)}

rows_by_code = collections.defaultdict(list)
for row in gen:
    rows_by_code[row[idx["codigo_produto"]]].append(row)

target = "3982528494"
print(f"Linhas para o codigo {target}:")
for r in rows_by_code[target]:
    print(" ", {k: r[idx[k]] for k in ["modelo_base", "dimensao", "descricao_comercial", "acabamento", "preco_tabela", "pagina_pdf"]})

# Verifica se duplicados tem sempre o mesmo preco/descricao (= mesmo componente, pagina diferente)
mismatches = 0
checked = 0
for code, rows in rows_by_code.items():
    if len(rows) > 1:
        checked += 1
        precos = set(r[idx["preco_tabela"]] for r in rows)
        descricoes = set(r[idx["descricao_comercial"]] for r in rows)
        if len(precos) > 1 or len(descricoes) > 1:
            mismatches += 1
            if mismatches <= 3:
                print(f"\nDIVERGENCIA no codigo {code}:")
                for r in rows:
                    print("   ", {k: r[idx[k]] for k in ["modelo_base", "dimensao", "preco_tabela", "pagina_pdf"]})

print(f"\nCodigos duplicados verificados: {checked}")
print(f"Casos com preco/descricao DIFERENTES entre duplicatas: {mismatches}")
