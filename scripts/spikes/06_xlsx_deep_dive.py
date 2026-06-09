"""Spike: o prices.xlsx parece ser um RESULTADO DE EXTRACAO PREVIA do mesmo PDF (schema com
record_id, categoria, grupo, modelo_base, dimensao, acabamento, codigo_produto, preco_tabela,
confianca_extracao, observacoes_mcp...). Vamos extrair, sem carregar tudo na memoria/contexto:
 - conteudo das abas pequenas (schema_mcp, meta, issues_extracao)
 - contagem de linhas e amostra da aba grande (produtos_mcp)
 - quais sheetN.xml correspondem a quais nomes de aba (e qual da erro de XML)
usando parsing incremental (iterparse) para nao estourar memoria/contexto.
"""
import zipfile
import re
import xml.etree.ElementTree as ET

PATH = r"C:\projects\codex\helence\helence-orcamento\data\prices.xlsx"
z = zipfile.ZipFile(PATH)

ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Mapear rId -> sheetN.xml e nome da aba, via workbook.xml + rels
wb_xml = z.read("xl/workbook.xml").decode("utf-8")
rels_xml = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
sheets = re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wb_xml)
rid_to_target = dict(re.findall(r'<Relationship Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml))
print("Mapa aba -> arquivo:")
name_to_file = {}
for name, rid in sheets:
    target = rid_to_target.get(rid, "?")
    name_to_file[name] = f"xl/{target}"
    print(f"  {name:20s} -> {target}")

def iter_rows(sheet_file, max_rows=None):
    """Itera linhas (lista de valores de celula em ordem de coluna) usando parsing incremental."""
    with z.open(sheet_file) as f:
        row_vals = []
        count = 0
        for event, elem in ET.iterparse(f, events=("end",)):
            tag = elem.tag
            if tag == ns + "row":
                vals = []
                for c in elem:
                    t = c.get("t")
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
                count += 1
                elem.clear()
                if max_rows and count >= max_rows:
                    return

# 1) Abas pequenas: meta, schema_mcp, issues_extracao -- imprime tudo
for small in ["meta", "schema_mcp", "issues_extracao"]:
    if small not in name_to_file:
        continue
    print("\n" + "=" * 80)
    print(f"ABA: {small}")
    print("-" * 80)
    for i, row in enumerate(iter_rows(name_to_file[small])):
        print(f"  L{i+1}: {row}")

# 2) Aba grande produtos_mcp: cabecalho + total de linhas + amostra + valores unicos de colunas-chave
print("\n" + "=" * 80)
print("ABA: produtos_mcp (grande) -- cabecalho + amostra + estatisticas")
print("-" * 80)
gen = iter_rows(name_to_file["produtos_mcp"])
header = next(gen)
print("Cabecalho:", header)
idx = {col: i for i, col in enumerate(header)}

sample = []
total = 0
categorias = {}
grupos = {}
acabamentos = {}
confiancas = {}
moedas = {}
tabelas = {}
sem_preco = 0
sem_codigo = 0
for row in gen:
    total += 1
    if total <= 8:
        sample.append(row)
    def bump(d, key):
        d[key] = d.get(key, 0) + 1
    if idx.get("categoria") is not None and len(row) > idx["categoria"]:
        bump(categorias, row[idx["categoria"]])
    if idx.get("grupo") is not None and len(row) > idx["grupo"]:
        bump(grupos, row[idx["grupo"]])
    if idx.get("acabamento") is not None and len(row) > idx["acabamento"]:
        bump(acabamentos, row[idx["acabamento"]])
    if idx.get("confianca_extracao") is not None and len(row) > idx["confianca_extracao"]:
        bump(confiancas, row[idx["confianca_extracao"]])
    if idx.get("moeda") is not None and len(row) > idx["moeda"]:
        bump(moedas, row[idx["moeda"]])
    if idx.get("tabela_preco") is not None and len(row) > idx["tabela_preco"]:
        bump(tabelas, row[idx["tabela_preco"]])
    preco = row[idx["preco_tabela"]] if idx.get("preco_tabela") is not None and len(row) > idx["preco_tabela"] else None
    codigo = row[idx["codigo_produto"]] if idx.get("codigo_produto") is not None and len(row) > idx["codigo_produto"] else None
    if not preco:
        sem_preco += 1
    if not codigo:
        sem_codigo += 1

print(f"\nTotal de linhas de dados: {total}")
print("\nAmostra (8 primeiras linhas):")
for r in sample:
    print(" ", r)

print(f"\nLinhas sem preco: {sem_preco} | Linhas sem codigo: {sem_codigo}")
print(f"\nCategorias ({len(categorias)}): {categorias}")
print(f"\nGrupos ({len(grupos)}): {grupos}")
print(f"\nMoedas: {moedas}")
print(f"\nTabelas de preco: {tabelas}")
print(f"\nNiveis de confianca de extracao: {confiancas}")
print(f"\nAcabamentos distintos ({len(acabamentos)}):")
for k, v in sorted(acabamentos.items(), key=lambda kv: -kv[1])[:40]:
    print(f"   {k!r}: {v}")
