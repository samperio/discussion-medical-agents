"""Convierte la respuesta JSON del webhook BIRADS 4B en un reporte PDF.

Uso: python generar_pdf.py resultado.json reporte.pdf
Requiere Google Chrome o Microsoft Edge (modo headless); no usa librerías externas.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 10.5pt/1.5 'Segoe UI', Arial, sans-serif; color: #1a1a1a; }
h1 { font-size: 18pt; margin: 0 0 4px; color: #123a63; }
h2 { font-size: 13.5pt; color: #123a63; border-bottom: 2px solid #123a63; padding-bottom: 3px; margin-top: 22px; }
h3 { font-size: 11.5pt; color: #123a63; margin: 14px 0 4px; }
h4 { font-size: 10.5pt; margin: 10px 0 2px; }
.meta { color: #555; font-size: 9.5pt; margin-bottom: 10px; }
.caso { background: #f2f6fa; border-left: 4px solid #123a63; padding: 8px 12px; }
.agente { margin-top: 12px; page-break-inside: avoid-page; }
.agente > .nombre { font-weight: 600; background: #e8eef5; padding: 4px 8px; border-radius: 3px; }
.vacio { color: #a40000; font-style: italic; }
.consenso { border: 1.5px solid #123a63; padding: 4px 14px 10px; border-radius: 4px; }
.aviso { margin-top: 24px; padding: 8px 12px; border: 1px solid #b00020; color: #6b0014; font-size: 9pt; }
ul, ol { margin: 4px 0 6px 20px; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9.5pt; }
th, td { border: 1px solid #b8c4d2; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #e8eef5; }
hr { border: 0; border-top: 1px solid #ccc; margin: 10px 0; }
"""


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


def md(text):
    """Markdown mínimo: encabezados, listas, negritas, reglas y párrafos."""
    out, lista = [], None

    def cerrar():
        nonlocal lista
        if lista:
            out.append(f"</{lista}>")
            lista = None

    tabla = []

    def volcar_tabla():
        nonlocal tabla
        if not tabla:
            return
        filas = [[c.strip() for c in f.strip("|").split("|")] for f in tabla]
        filas = [f for f in filas if not all(re.fullmatch(r":?-{2,}:?", c) for c in f if c)]
        h = "".join(f"<th>{inline(c)}</th>" for c in filas[0])
        b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in f) + "</tr>" for f in filas[1:])
        out.append(f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>")
        tabla = []

    for linea in text.replace("\r", "").split("\n"):
        s = linea.strip()
        if s.startswith("|") and s.count("|") >= 2:
            cerrar()
            tabla.append(s)
            continue
        volcar_tabla()
        m_h = re.match(r"^(#{1,6})\s+(.*)", s)
        m_ul = re.match(r"^[-*•]\s+(.*)", s)
        m_ol = re.match(r"^\d+[.)]\s+(.*)", s)
        if not s:
            cerrar()
        elif re.match(r"^[-_*]{3,}$", s):
            cerrar()
            out.append("<hr>")
        elif m_h:
            cerrar()
            nivel = min(len(m_h.group(1)) + 2, 4)  # los # del modelo bajan a h3/h4
            out.append(f"<h{nivel}>{inline(m_h.group(2))}</h{nivel}>")
        elif m_ul:
            if lista != "ul":
                cerrar()
                out.append("<ul>")
                lista = "ul"
            out.append(f"<li>{inline(m_ul.group(1))}</li>")
        elif m_ol:
            if lista != "ol":
                cerrar()
                out.append("<ol>")
                lista = "ol"
            out.append(f"<li>{inline(m_ol.group(1))}</li>")
        else:
            cerrar()
            out.append(f"<p>{inline(s)}</p>")
    cerrar()
    volcar_tabla()
    return "\n".join(out)


def ronda(titulo, bloque):
    partes = re.split(r"--- (.+?) ---\n", bloque)
    h = [f"<h2>{html.escape(titulo)}</h2>"]
    for i in range(1, len(partes), 2):
        cuerpo = partes[i + 1].strip()
        vacio = (not cuerpo) or cuerpo.startswith("Sin respuesta") or cuerpo.startswith("ERROR")
        contenido = (
            '<p class="vacio">El agente no devolvió respuesta en esta ronda.</p>' if vacio else md(cuerpo)
        )
        h.append(f'<div class="agente"><div class="nombre">{html.escape(partes[i])}</div>{contenido}</div>')
    return "\n".join(h)


def construir(d):
    dc = d["discusion_completa"]
    esp = "".join(f"<li>{html.escape(e)}</li>" for e in d["especialistas"])
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>{html.escape(d['titulo'])}</title><style>{CSS}</style></head><body>
<h1>{html.escape(d['titulo'])}</h1>
<div class="meta">Fecha: {html.escape(d['fecha'])} · Backend: {html.escape(d['backend'])} · Rondas: {d['rondas_completadas']}</div>
<h2>Caso clínico</h2><div class="caso">{html.escape(d['caso_clinico'])}</div>
<h3>Especialistas participantes</h3><ol>{esp}</ol>
<h2>Consenso final del comité</h2><div class="consenso">{md(d['consenso_final'].strip())}</div>
{ronda('Ronda 1 · Valoraciones iniciales', dc['ronda_1'].split('\n', 2)[-1])}
{ronda('Ronda 2 · Debate y contraposición', dc['ronda_2'].split('\n', 2)[-1])}
<div class="aviso"><strong>Aviso:</strong> {html.escape(d['disclaimer'])}</div>
</body></html>"""


def main(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    navegador = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not navegador:
        sys.exit("No se encontró Chrome ni Edge para generar el PDF.")
    with tempfile.TemporaryDirectory() as tmp:
        ruta_html = os.path.join(tmp, "reporte.html")
        open(ruta_html, "w", encoding="utf-8").write(construir(d))
        subprocess.run(
            [navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={os.path.abspath(dst)}", "file:///" + ruta_html.replace("\\", "/")],
            check=True, capture_output=True, timeout=120,
        )
    print("PDF generado:", os.path.abspath(dst), os.path.getsize(dst), "bytes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
