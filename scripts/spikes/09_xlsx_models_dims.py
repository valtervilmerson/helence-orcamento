"""Spike: contar modelo_base / dimensao / paginas distintas na extracao previa, para
dimensionar o catalogo (familia, produto base, dimensoes, paginas por grupo)."""
import zipfile
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

gen = iter_rows("xl/worksheets/sheet1.xml")
header = next(gen)
idx = {col: i for i, col in enumerate(header)}

modelos = {}
dimensoes = {}
paginas = set()
codigos = set()
descricoes_unicas = set()
for row in gen:
    modelos[row[idx["modelo_base"]]] = modelos.get(row[idx["modelo_base"]], 0) + 1
    dimensoes[row[idx["dimensao"]]] = dimensoes.get(row[idx["dimensao"]], 0) + 1
    paginas.add(int(row[idx["pagina_pdf"]]))
    codigos.add(row[idx["codigo_produto"]])
    descricoes_unicas.add(row[idx["descricao_comercial"]])

print(f"Modelos base distintos: {len(modelos)}")
for k, v in sorted(modelos.items(), key=lambda kv: -kv[1])[:15]:
    print(f"   {k!r}: {v} linhas")
print(f"... (mostrando so os 15 mais frequentes de {len(modelos)})")

print(f"\nDimensoes distintas: {len(dimensoes)}")
for k, v in sorted(dimensoes.items(), key=lambda kv: -kv[1])[:15]:
    print(f"   {k!r}: {v} linhas")

print(f"\nPaginas cobertas: {len(paginas)} (min={min(paginas)}, max={max(paginas)})")
print(f"Codigos de produto distintos: {len(codigos)}")
print(f"Descricoes comerciais distintas: {len(descricoes_unicas)}")

# Verifica se ha codigos duplicados (mesmo codigo em linhas diferentes)
import collections
gen2 = iter_rows("xl/worksheets/sheet1.xml")
next(gen2)
codigo_count = collections.Counter()
for row in gen2:
    codigo_count[row[idx["codigo_produto"]]] += 1
dups = {k: v for k, v in codigo_count.items() if v > 1}
print(f"\nCodigos que aparecem mais de uma vez: {len(dups)}")
for k, v in list(dups.items())[:5]:
    print(f"   {k}: {v}x")
