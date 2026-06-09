"""Spike: ler o xlsx no nivel de zip/xml bruto (openpyxl falhou por XML invalido) so para
confirmar nomes de abas e dar uma espiada no shape -- objetivo e apenas confirmar se
data/prices.xlsx parece ser a planilha-fonte do PDF (mesmo dominio/colunas)."""
import zipfile
import re

PATH = r"C:\projects\codex\helence\helence-orcamento\data\prices.xlsx"
z = zipfile.ZipFile(PATH)

wb_xml = z.read("xl/workbook.xml").decode("utf-8", errors="replace")
sheet_names = re.findall(r'<sheet name="([^"]+)"', wb_xml)
print("Nomes das abas:", sheet_names)

for sheet_file in ["xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"]:
    raw = z.read(sheet_file)
    text = raw.decode("utf-8", errors="replace")
    print("=" * 80)
    print(f"{sheet_file} -- {len(raw)} bytes")
    # Conta linhas <row> e celulas <c>
    rows = re.findall(r'<row r="(\d+)"', text)
    print(f"Numero de <row>: {len(rows)} (primeiras: {rows[:5]}, ultimas: {rows[-5:] if rows else []})")
    # Mostra um trecho cru perto do inicio
    print("--- trecho inicial (1500 chars) ---")
    print(text[:1500])
    # Procura por caracteres de controle invalidos em XML (fora de \t\n\r e >= 0x20)
    bad = [m.start() for m in re.finditer(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text)]
    print(f"Posicoes com caracteres de controle invalidos para XML: {len(bad)} (primeiras 5: {bad[:5]})")
    if bad:
        pos = bad[0]
        print("Contexto ao redor do 1o caractere invalido:", repr(text[max(0,pos-80):pos+20]))
