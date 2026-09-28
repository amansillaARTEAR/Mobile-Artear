#!/usr/bin/env python3
"""
A partir del texto de un ticket de Jira, aplica técnicas de diseño de casos de
QA (no solo "escribí un test") para derivar varios escenarios — camino feliz
(positivo), caso negativo/alternativo y caso de borde, cuando el ticket da pie
a cada uno — documentados en formato Given-When-Then, y genera el código
pytest para cada uno usando la API de Claude. Todo queda en tests/generados/
para revisión humana antes de mergear (no se mezcla con la suite oficial hasta
que se aprueba el Pull Request).

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
ARCHIVO_SUITE = RAIZ / "tests" / "test_tnarc4366.py"
ARCHIVO_PLAYER = RAIZ / "helpers" / "player.py"
DIR_GENERADOS = RAIZ / "tests" / "generados"

MODELO = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

SYSTEM = """Sos un ingeniero de QA automation senior, experto en diseño de casos de
prueba y en Appium + pytest. Tu tarea es analizar un ticket de Jira aplicando técnicas
estándar de diseño de casos (no simplemente "escribir un test cualquiera") y producir
varias funciones de test nuevas para una suite existente de un player de videos
verticales (mobile web, Android/iOS, dispositivo real).

Proceso de diseño (hacelo antes de escribir código, pero NO lo muestres como texto
aparte — se refleja en los escenarios que elijas y en los comentarios Given/When/Then):
1. Identificá el camino feliz / caso POSITIVO que el ticket describe.
2. Si el ticket da pie a un caso NEGATIVO o alternativo razonable (algo que no debería
   pasar, un estado distinto al esperado, una acción en orden distinto), incluilo.
3. Si el ticket da pie a un caso de BORDE (un límite, una condición extrema, un estado
   inicial atípico), incluilo.
No inventes casos negativos/borde forzados si el ticket es demasiado simple para dar
pie a ellos — en ese caso alcanza con el positivo. Nunca generes más de 3 funciones.

Reglas estrictas para el código:
- Devolvé ÚNICAMENTE código Python válido, sin explicaciones fuera de comentarios, sin
  markdown, sin ```.
- Generá una función por escenario, con estos nombres exactos y en este orden (usá
  solo los que apliquen, salteando los que no correspondan): {nombres_funciones}
- Firma de cada función: def test_caXX_tipo(player, registro):  (misma firma que los
  casos existentes)
- Inmediatamente arriba de cada función, un bloque de comentarios con el escenario en
  formato Given-When-Then:
    # Escenario: <Positivo|Negativo|Borde>
    # Dado ...
    # Cuando ...
    # Entonces ...
- El docstring de una línea debe empezar con "POSITIVO:", "NEGATIVO:" o "BORDE:" según
  corresponda, seguido de la descripción (mismo estilo que los casos existentes que
  usan "CAxx: ...").
- Usá SOLO los métodos que ya existen en la clase Player (los que se listan abajo). Si
  algún escenario necesita una interacción que ningún método de Player permite hacer
  hoy, escribí el test igual con la mejor aproximación posible, y agregá un comentario
  "# TODO revisar:" explicando qué falta o qué se asumió, en vez de inventar selectores
  CSS al azar.
- Los diccionarios que devuelven los métodos de Player SOLO tienen las claves que se
  documentan abajo en "Forma de los datos que devuelve Player" -- no inventes una clave
  que no esté ahí (por ejemplo, no asumas "tiene_cierre" en lo que devuelve player.abrir()
  si no aparece en esa lista: eso hace que el assert compare siempre contra un valor por
  defecto y nunca falle, aunque el comportamiento real esté mal). Si necesitás verificar
  algo para lo que no hay una clave, usá "# TODO revisar:" en vez de asumirla.
- Seguí el mismo estilo que los casos existentes: uso de player.captura(...) para
  evidencias, asserts con mensaje descriptivo, y registro["evidencias"].append(...)
  para las capturas relevantes.
- No repitas imports ni fixtures: asumí que pytest, config y las fixtures player/registro
  ya están disponibles vía conftest.py (no hace falta importarlos ni definirlos).
- Si necesitás alguna constante o helper que no existe, no la inventes: resolvé el test
  con lo que ya hay en Player, aunque sea de forma menos elegante.
"""


def leer_metodos_player():
    src = ARCHIVO_PLAYER.read_text(encoding="utf-8")
    metodos = re.findall(r"    def (\w+)\(self[^)]*\):(?:\n        \"\"\"(.*?)\"\"\")?", src)
    lineas = []
    for nombre, doc in metodos:
        if nombre.startswith("_"):
            continue
        lineas.append(f"- player.{nombre}(...)" + (f"  # {doc.strip()}" if doc.strip() else ""))
    return "\n".join(lineas)


# Forma exacta de los diccionarios que devuelven los métodos más usados de Player, para
# que Claude no tenga que adivinar (ni inventar) qué claves existen. Mantenido a mano
# porque estos dicts se arman en JS embebido, no en docstrings de Python.
FORMA_DATOS_PLAYER = """Forma de los datos que devuelve Player (no existen otras claves además de éstas):

- player.abrir() y player.tocar_video() devuelven un "snap" del slide activo:
  {tab, idx, total, fin, video, reproduciendo, muteado, t, d, ancho_video, alto_video,
  barra, ratio, tiene_video, placeholders, sonando, version, url}
  (NO incluye nada sobre íconos de compartir/sonido/cierre ni sobre topbar/navbar).
- player.controles_visibles() devuelve una LISTA de strings (texto/aria-label de cada
  botón visible fuera del reproductor) -- no es un diccionario, no tiene .get(...).
- player.iconos_visibles() devuelve un diccionario ya resuelto en booleanos, pensado
  para tickets que piden verificar íconos puntuales:
  {tiene_share, tiene_sonido, tiene_cierre, botones}
  Preferí este método sobre controles_visibles() cuando el ticket pida comprobar la
  presencia de un ícono específico (compartir, sonido/volumen, cerrar).
"""


def leer_ejemplos():
    src = ARCHIVO_SUITE.read_text(encoding="utf-8")
    # Mandamos dos casos completos como referencia de estilo (no hace falta el archivo entero).
    partes = re.split(r"\n# -{10,} CA\d+\n", src)
    return "\n\n".join(partes[1:3]) if len(partes) > 2 else src[:4000]


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
                     help="Componente/elemento que toca el ticket (ej: Player, Portada) -- se guarda como tag "
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
    nombres_posibles = [f"test_{caso_id}_positivo", f"test_{caso_id}_negativo", f"test_{caso_id}_borde"]

    prompt = f"""Ticket de Jira:
---
{ticket}
---

Métodos disponibles en la clase Player:
{leer_metodos_player()}

{FORMA_DATOS_PLAYER}

Ejemplos de casos existentes (para copiar el estilo):
{leer_ejemplos()}

Generá entre 1 y 3 funciones, usando estos nombres exactos según el escenario
(saltea los que no correspondan, no agregues otros): {", ".join(nombres_posibles)}
"""
    system = SYSTEM.format(nombres_funciones=", ".join(nombres_posibles))

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
        + '"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño '
        'de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""\n\n'
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
