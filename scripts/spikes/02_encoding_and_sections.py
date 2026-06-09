"""Spike: investigar encoding (mojibake) e variedade de secoes/cabecalhos no PDF."""
import re
import pypdf

PATH = r"C:\projects\codex\helence\helence-orcamento\data\source.pdf"
reader = pypdf.PdfReader(PATH)
n = len(reader.pages)
print(f"Total paginas: {n}")

# 1) Tentar destrancar o mojibake: o extrator devolve '�' (replacement char)
#    Vamos ver se cp1252 / latin1 / outras rotas resolvem reapresentando bytes.
sample = reader.pages[1].extract_text() or ""
trecho = "REUNI" + "�" + "O"
print("\n--- Teste de mojibake na palavra REUNIAO ---")
print("Repr do trecho problematico:", repr(sample[:60]))
for ch in sample:
    if ch == "�":
        print("Encontrado U+FFFD (replacement character) -> extrator nao conseguiu mapear o glifo original")
        break

# 2) Varrer todas as paginas e coletar a 1a linha (cabecalho) + se contem certas palavras-chave
keywords = ["MODELO", "DESCRI", "ACESS", "OBSERVA", "ESTRUTURA", "TAMPO", "INDICE", "ÍNDICE", "DESCRIÇÃO TÉCNICA", "REDONDA", "LOUNGE", "STAFF"]
header_counter = {}
pages_with_keyword = {k: [] for k in keywords}

for i in range(n):
    text = reader.pages[i].extract_text() or ""
    first_line = text.strip().split("\n")[0][:70] if text.strip() else "<vazio>"
    header_counter.setdefault(first_line, []).append(i + 1)
    for k in keywords:
        if k in text.upper():
            pages_with_keyword[k].append(i + 1)

print("\n--- Cabecalhos (1a linha) mais comuns ---")
sorted_headers = sorted(header_counter.items(), key=lambda kv: -len(kv[1]))
for h, pages in sorted_headers[:15]:
    print(f"[{len(pages)}x] {h!r}  ex.paginas={pages[:5]}")

print("\n--- Paginas que contem cada palavra-chave (contagem e amostra) ---")
for k, pages in pages_with_keyword.items():
    print(f"{k}: {len(pages)} paginas. Amostra: {pages[:10]}")

# 3) Detectar paginas que tem poucas linhas / texto bem menor (podem ser capa/rodape/secao especial)
sizes = [(i + 1, len(reader.pages[i].extract_text() or "")) for i in range(n)]
sizes_sorted = sorted(sizes, key=lambda x: x[1])
print("\n--- 10 paginas com MENOS texto extraido ---")
for p, sz in sizes_sorted[:10]:
    print(f"pagina {p}: {sz} chars")
print("\n--- 10 paginas com MAIS texto extraido ---")
for p, sz in sizes_sorted[-10:]:
    print(f"pagina {p}: {sz} chars")
