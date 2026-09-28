#!/usr/bin/env python3
"""
Genera un caso de prueba nuevo (función pytest) a partir del texto de un ticket
de Jira, usando la API de Claude, y lo deja en tests/generados/ para revisión
humana antes de mergear (no se mezcla con la suite oficial hasta que se aprueba
el Pull Request).

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

SYSTEM = """Sos un ingeniero de QA automation senior, experto en Appium + pytest.
Tu tarea es escribir UNA sola función de test nueva para una suite existente de
pruebas de un player de videos verticales (mobile web, Android/iOS, dispositivo real),
a partir de la descripción de un ticket de Jira.

Reglas estrictas:
- Devolvé ÚNICAMENTE código Python válido, sin explicaciones, sin markdown, sin ```.
- La función debe llamarse exactamente como se te indique en el pedido (nombre exacto dado).
- Firma: def test_caXX_algo(player, registro):  (misma firma que los casos existentes)
- Usá SOLO los métodos que ya existen en la clase Player (los que se listan abajo). Si el
  ticket pide una interacción que ningún método de Player permite hacer hoy, escribí el test
  igual con la mejor aproximación posible, y agregá un comentario "# TODO revisar:" explicando
  qué falta o qué se asumió, en vez de inventar selectores CSS al azar.
- Seguí el mismo estilo que los casos existentes: docstring de una línea empezando con
  "CAxx: ...", uso de player.captura(...) para evidencias, asserts con mensaje descriptivo,
  y registro["evidencias"].append(...) para las capturas relevantes.
- No repitas imports ni fixtures: asumí que pytest, config y las fixtures player/registro
  ya están disponibles vía conftest.py (no hace falta importarlos ni definirlos).
- Si necesitás alguna constante o helper que no existe, no la inventes: resolvé el test con
  lo que ya hay en Player, aunque sea de forma menos elegante.
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


def leer_ejemplos():
    src = ARCHIVO_SUITE.read_text(encoding="utf-8")
    # Mandamos dos casos completos como referencia de estilo (no hace falta el archivo entero).
    partes = re.split(r"\n# -{10,} CA\d+\n", src)
    return "\n\n".join(partes[1:3]) if len(partes) > 2 else src[:4000]


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
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("Falta ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    ticket = Path(args.ticket_file).read_text(encoding="utf-8").strip()
    if not ticket:
        print("El ticket está vacío", file=sys.stderr)
        return 1

    caso_id = siguiente_nombre()
    slug = re.sub(r"[^a-z0-9]+", "_", "generado").strip("_")
    nombre_funcion = f"test_{caso_id}_{slug}"

    prompt = f"""Ticket de Jira:
---
{ticket}
---

Métodos disponibles en la clase Player:
{leer_metodos_player()}

Ejemplos de casos existentes (para copiar el estilo):
{leer_ejemplos()}

Escribí la función con este nombre exacto: {nombre_funcion}
"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=MODELO,
            max_tokens=2000,
            system=SYSTEM,
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

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"test_{caso_id}_generado.py"
    out_file.write_text(
        '"""Caso generado automáticamente a partir de un ticket de Jira. REVISAR ANTES DE APROBAR EL PR."""\n\n'
        + codigo + "\n",
        encoding="utf-8",
    )
    print(f"Generado: {out_file}")
    print(f"NOMBRE_CASO={nombre_funcion}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
