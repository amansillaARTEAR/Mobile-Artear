#!/usr/bin/env python3
"""
A partir del texto de un ticket de Jira, identifica cada criterio de aceptación (CA)
que el ticket enumera y genera una función de test pytest por cada uno -- trazable
1 a 1 al CA que cubre (si el ticket tiene 6 CA, se generan 6 funciones) -- usando la
API de Claude. Todo queda en tests/generados/ para revisión humana antes de mergear
(no se mezcla con la suite oficial hasta que se aprueba el Pull Request).

Es la versión de esta suite (app nativa Android/iOS instalada en el
dispositivo) del script equivalente de appium-mobile-web-qa — misma mecánica,
adaptado a la clase App (helpers/app.py) en vez de Player.

Uso:
    python scripts/generar_caso.py --ticket-file /tmp/ticket.txt

Requiere la variable de entorno ANTHROPIC_API_KEY.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import anthropic

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVOS_EJEMPLO = [RAIZ / "tests" / "test_smoke.py", RAIZ / "tests" / "test_amr2083.py"]
ARCHIVO_APP = RAIZ / "helpers" / "app.py"
DIR_GENERADOS = RAIZ / "tests" / "generados"

MODELO = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

SYSTEM = """Sos un ingeniero de QA automation senior, experto en Appium + pytest. Tu
tarea es analizar un ticket de Jira y producir una función de test por cada criterio
de aceptación (CA) que el ticket enumera, para una suite existente que prueba una app
nativa Android (y a futuro iOS) instalada en un dispositivo real.

Proceso (hacelo antes de escribir código, pero NO lo muestres como texto aparte):
1. Encontrá la lista de criterios de aceptación del ticket (suele estar numerada:
   "1.", "2.", ... o con subitems tipo "6a", "6b"). Tomalos en el orden en que
   aparecen en el ticket, tal como están escritos.
2. Para CADA criterio de aceptación (incluyendo subitems), generá EXACTAMENTE UNA
   función de test que lo verifique. No agrupes dos CA en una sola función ni
   dividas un CA en varias. Si el ticket tiene 6 criterios de aceptación (contando
   subitems como propios, ej. 6a y 6b cuentan como 2), el resultado son 6 funciones.
3. No inventes criterios que el ticket no menciona, y no omitas ninguno de los que
   sí menciona, aunque te parezca trivial o difícil de automatizar con los métodos
   disponibles (en ese caso, hacé la mejor aproximación posible y usá "# TODO
   revisar:" para lo que falte, pero generá la función igual).

Reglas estrictas para el código:
- Devolvé ÚNICAMENTE código Python válido, sin explicaciones fuera de comentarios, sin
  markdown, sin ```.
- Nombrá cada función test_{caso_id}_caN (o test_{caso_id}_caNa / test_{caso_id}_caNb
  para subitems), donde N es el número de criterio de aceptación tal como figura en
  el ticket, en el mismo orden. Ej: con 6 CA (el 6to con subitems a/b) generás
  test_{caso_id}_ca1, test_{caso_id}_ca2, test_{caso_id}_ca3, test_{caso_id}_ca4,
  test_{caso_id}_ca5, test_{caso_id}_ca6a, test_{caso_id}_ca6b. No uses "positivo",
  "negativo" ni "borde" en ningún nombre, comentario ni docstring.
- Firma de cada función: def test_caXX_caN(app, registro):  (misma firma que los
  casos existentes)
- Inmediatamente arriba de cada función, un bloque de comentarios que cite (textual
  o casi textual) el criterio de aceptación que cubre, y lo traduzca a Given-When-Then:
    # CA<N>: <texto del criterio de aceptación, tal como está en el ticket>
    # Dado ...
    # Cuando ...
    # Entonces ...
- El docstring de una línea debe empezar con "CA<N>: " (ej. "CA6b: ...", igual que
  en el comentario de arriba), seguido de una descripción breve de qué verifica esa
  función (mismo estilo que los casos existentes que usan "SMK-xx: ..." o
  "AMR-xxxx CAx: ...").
- Usá SOLO los métodos que ya existen en la clase App (los que se listan abajo). Si
  algún escenario necesita una interacción que ningún método de App permite hacer hoy,
  escribí el test igual con la mejor aproximación posible, y agregá un comentario
  "# TODO revisar:" explicando qué falta o qué se asumió, en vez de inventar selectores
  XPath al azar.
- Los diccionarios/listas que devuelven los métodos de App SOLO tienen la forma que se
  documenta abajo en "Forma de los datos que devuelve App" -- no inventes una clave que
  no esté ahí (por ejemplo, no asumas una clave "visible" en lo que devuelve
  app.navbar() si no aparece en esa lista: eso hace que el assert compare siempre
  contra un valor por defecto y nunca falle, aunque el comportamiento real esté mal).
  Si necesitás verificar algo para lo que no hay una clave, usá "# TODO revisar:" en
  vez de asumirla.
- Seguí el mismo estilo que los casos existentes: uso de app.captura(...) para
  evidencias, asserts con mensaje descriptivo, y registro["evidencias"].append(...)
  para las capturas relevantes, registro["detalle"].update({{...}}) para los datos
  medidos.
- No repitas imports ni fixtures: asumí que pytest, config y las fixtures app/registro
  ya están disponibles vía conftest.py (no hace falta importarlos ni definirlos).
- Si necesitás alguna constante o helper que no existe, no la inventes: resolvé el test
  con lo que ya hay en App, aunque sea de forma menos elegante.
"""


def leer_metodos_app():
    src = ARCHIVO_APP.read_text(encoding="utf-8")
    metodos = re.findall(r"    def (\w+)\(self[^)]*\):(?:\n        \"\"\"(.*?)\"\"\")?", src)
    lineas = []
    for nombre, doc in metodos:
        if nombre.startswith("_"):
            continue
        lineas.append(f"- app.{nombre}(...)" + (f"  # {doc.strip()}" if doc.strip() else ""))
    return "\n".join(lineas)


# Forma exacta de lo que devuelven los métodos menos autodescriptivos de App, para que
# Claude no tenga que adivinar (ni inventar) qué claves existen.
FORMA_DATOS_APP = """Forma de los datos que devuelve App (no existen otras claves además de éstas):

- app.clickeables() y app.buscar(texto) devuelven una LISTA de elementos de Selenium/
  Appium crudos (WebElement) -- no diccionarios. Para el texto visible de cada uno,
  usá app.etiqueta(el).
- app.navbar() y app.topbar() devuelven una LISTA de diccionarios:
  {etiqueta, x, seleccionado, el}  (el = el WebElement, para poder hacer click)
- app.errores_nuevos() devuelve una LISTA de strings (cada uno un crash/ANR encontrado
  en el logcat desde la última consulta) -- lista vacía si no hubo ninguno.
- app.reiniciar() devuelve un float: los segundos que tardó en volver a mostrar
  contenido tras un arranque en frío.
- app.en_primer_plano(), app.esperar_primer_plano(), app.esperar_contenido(),
  app.en_inicio(), app.volver_al_inicio() devuelven bool.
- app.captura(caso, paso, descripcion) devuelve {archivo, descripcion} -- lo que hay
  que appendear a registro["evidencias"].
"""


def leer_ejemplos():
    # Mandamos 2 casos completos como referencia de estilo (no hace falta el archivo
    # entero). A diferencia de la suite web, acá no hay un separador "# ---- CAxx"
    # fijo, así que partimos directamente por cada "def test_".
    bloques = []
    for archivo in ARCHIVOS_EJEMPLO:
        if not archivo.exists():
            continue
        src = archivo.read_text(encoding="utf-8")
        partes = re.split(r"\ndef test_", src)
        for parte in partes[1:3]:
            bloques.append("def test_" + parte.split("\n\n\ndef ")[0].rstrip())
        if len(bloques) >= 2:
            break
    return "\n\n\n".join(bloques[:2]) if bloques else ""


def extraer_ticket_key(ticket_texto):
    """Busca el identificador del ticket (ej: TNARC-4381, AMR-2087) para poder
    identificar cada caso generado en el dashboard. El XML exportado de Jira siempre
    pone "Ticket: <key>" como primera línea (ver extraerTicketDeXml en docs/index.html);
    si el usuario pegó el texto a mano puede no estar, así que como respaldo buscamos
    cualquier patrón tipo PROYECTO-1234 en las primeras líneas."""
    m = re.search(r"^Ticket:\s*(\S+)", ticket_texto, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b", ticket_texto[:500])
    return m.group(1) if m else ""


def siguiente_nombre():
    existentes = set()
    for carpeta in (RAIZ / "tests", DIR_GENERADOS):
        if carpeta.exists():
            for f in carpeta.glob("**/*.py"):
                existentes.update(re.findall(r"test_ca(\d+)_", f.read_text(encoding="utf-8")))
    numeros = [int(n) for n in existentes] or [0]
    siguiente = max(numeros) + 1
    return f"ca{siguiente:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket-file", required=True, help="Archivo de texto con el contenido del ticket de Jira")
    ap.add_argument("--out-dir", default=str(DIR_GENERADOS))
    ap.add_argument("--componente", default="Sin clasificar",
                     help="Componente/elemento que toca el ticket (ej: Navbar, Player) -- se guarda como tag "
                          "en el archivo generado para que el dashboard agrupe los casos por componente")
    args = ap.parse_args()
    componente = (args.componente or "Sin clasificar").strip() or "Sin clasificar"

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("Falta ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    ticket = Path(args.ticket_file).read_text(encoding="utf-8").strip()
    if not ticket:
        print("El ticket está vacío", file=sys.stderr)
        return 1

    ticket_key = extraer_ticket_key(ticket)
    caso_id = siguiente_nombre()

    prompt = f"""Ticket de Jira:
---
{ticket}
---

Métodos disponibles en la clase App:
{leer_metodos_app()}

{FORMA_DATOS_APP}

Ejemplos de casos existentes (para copiar el estilo):
{leer_ejemplos()}

Generá una función por cada criterio de aceptación del ticket (ni más ni menos),
nombrada test_{caso_id}_caN (o test_{caso_id}_caNa/caNb para subitems), respetando
el número/letra tal como figura en el ticket y el orden en que aparecen. Como límite
de seguridad, no generes más de 12 funciones -- si el ticket tuviera más criterios
que eso, agregá un comentario "# TODO revisar:" al final indicando cuáles quedaron
sin cubrir.
"""
    system = SYSTEM.format(caso_id=caso_id)

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=MODELO,
            max_tokens=3000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        print(f"La API de Anthropic devolvio error {e.status_code}: {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIError as e:
        print(f"Fallo la llamada a la API de Anthropic: {e}", file=sys.stderr)
        return 1

    codigo = "".join(b.text for b in resp.content if b.type == "text").strip()
    codigo = re.sub(r"^```(?:python)?\n|\n```$", "", codigo).strip()

    funciones_generadas = re.findall(r"^def (test_\w+)\(", codigo, re.MULTILINE)
    if not funciones_generadas:
        print("Claude no devolvió ninguna función de test reconocible. Salida cruda:", file=sys.stderr)
        print(codigo, file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"test_{caso_id}_generado.py"
    encabezado = f"# Componente: {componente}\n"
    if ticket_key:
        encabezado += f"# Ticket: {ticket_key}\n"
    out_file.write_text(
        encabezado
        + '"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada '
        'criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""\n\n'
        + codigo + "\n",
        encoding="utf-8",
    )
    print(f"Generado: {out_file} ({len(funciones_generadas)} escenario(s): {', '.join(funciones_generadas)})")
    print(f"NOMBRE_CASO={caso_id}")
    print(f"ESCENARIOS={','.join(funciones_generadas)}")
    print(f"TICKET_KEY={ticket_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
