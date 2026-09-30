import html
import json
import os
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.common.base import AppiumOptions

import config as config_mod
import limpieza
from helpers.app import App

try:
    from pytest_html import extras as html_extras
except ImportError:  # sin pytest-html se ejecuta igual, solo sin reporte HTML
    html_extras = None

RESULTADOS = {}
SALIDA = None
PLATAFORMA = config_mod.PLATAFORMA
APP = None


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Crea la carpeta de la corrida y ubica el reporte HTML dentro de ella."""
    global SALIDA, APP
    vencidos = limpieza.limpiar()  # borra corridas e informes con más de 48 h
    if vencidos:
        print(f"Limpieza: se borraron {len(vencidos)} resultados con más de {limpieza.HORAS:g} h")
    SALIDA = limpieza.RAIZ / PLATAFORMA / "corridas" / time.strftime("%Y%m%d-%H%M%S")
    (SALIDA / "evidencias").mkdir(parents=True, exist_ok=True)
    (limpieza.RAIZ / PLATAFORMA / "informes").mkdir(parents=True, exist_ok=True)
    try:
        APP = config_mod.app_a_probar()
    except FileNotFoundError as e:
        raise pytest.UsageError(str(e))
    if hasattr(config.option, "htmlpath"):
        config.option.htmlpath = str(SALIDA / "reporte.html")
        # En CI el reporte se publica solo (reporte.html + evidencias/), así que conviene que
        # el CSS/JS de pytest-html vengan embebidos (self-contained) y no dependan de una
        # carpeta assets/ aparte. En corridas manuales se deja liviano, como antes.
        config.option.self_contained_html = os.environ.get("CI", "").lower() == "true"


def pytest_sessionstart(session):
    # La sección "Environment" (versión de Python, plataforma, plugins instalados, etc.)
    # ya se oculta con CSS en pytest_html_results_summary -- esto además evita que esos
    # datos técnicos queden embebidos en el HTML. pytest-metadata >= 3 los guarda en
    # config.stash (metadata_key), no en config._metadata (eso quedó deprecado, se limpia
    # igual por si hay una versión vieja instalada).
    try:
        from pytest_metadata.plugin import metadata_key
        session.config.stash[metadata_key].clear()
    except Exception:
        pass
    if hasattr(session.config, "_metadata"):
        session.config._metadata.clear()


@pytest.fixture(scope="session")
def driver():
    opciones = AppiumOptions()
    opciones.load_capabilities(config_mod.caps(APP))
    d = webdriver.Remote(config_mod.APPIUM_URL, options=opciones)
    yield d
    d.quit()


@pytest.fixture(scope="session")
def salida():
    yield SALIDA
    (SALIDA / "resultados.json").write_text(
        json.dumps(RESULTADOS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados, evidencias y reporte en: {SALIDA.resolve()}")


@pytest.fixture(scope="session")
def app(driver, salida):
    a = App(driver, salida)
    info = RESULTADOS.setdefault("_sesion", {"detalle": {}, "evidencias": []})["detalle"]
    caps = driver.capabilities
    # "actividad_inicial" (nombre de la Activity de Android) es un dato técnico interno,
    # no algo que le sirva a quien lee el reporte -- no se incluye en el resumen.
    info.update({"app": APP.name, "identificador": a.paquete,
                 "dispositivo": caps.get("deviceModel") or caps.get("deviceName"),
                 "sistema": f'{PLATAFORMA.capitalize()} {caps.get("platformVersion", "")}'.strip()})
    return a


@pytest.fixture
def registro(request):
    return RESULTADOS.setdefault(request.node.name, {"detalle": {}, "evidencias": []})


# ---------------------------------------------------------------- reporte HTML
def _valor(v):
    if isinstance(v, (dict, list)):
        return "<pre style='margin:0;white-space:pre-wrap'>" + html.escape(
            json.dumps(v, ensure_ascii=False, indent=2)) + "</pre>"
    return html.escape(str(v))


def _tabla_detalle(datos):
    # El nombre/descripción del caso ya se muestra en la columna "Caso de prueba" de la
    # tabla de resultados (ver pytest_html_results_table_row) -- no hace falta repetirlo acá.
    filas = "".join(
        f"<tr><td style='padding:4px 8px;border:1px solid #ddd;font-weight:bold;vertical-align:top;color:#333'>"
        f"{html.escape(str(k))}</td><td style='padding:4px 8px;border:1px solid #ddd;color:#333'>{_valor(v)}</td></tr>"
        for k, v in datos.get("detalle", {}).items())
    return f"<table style='border-collapse:collapse;margin-bottom:8px;font-size:12px'>{filas}</table>"


def _galeria(datos):
    tarjetas = []
    for ev in datos.get("evidencias", []):
        ruta = "evidencias/" + ev["archivo"]
        desc = html.escape(ev.get("descripcion", ""))
        if ev["archivo"].endswith(".mp4"):
            media = f"<video src='{ruta}' controls style='height:360px'></video>"
        else:
            media = f"<a href='{ruta}' target='_blank'><img src='{ruta}' style='height:360px;border:1px solid #ccc'></a>"
        tarjetas.append(f"<figure style='display:inline-block;margin:0 12px 12px 0;vertical-align:top;width:190px'>"
                        f"{media}<figcaption style='color:#333;font-size:11px'>{desc}</figcaption></figure>")
    return "<div>" + "".join(tarjetas) + "</div>" if tarjetas else ""


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    rep = resultado.get_result()
    if rep.when == "call" or (rep.when == "setup" and rep.failed):
        d = RESULTADOS.setdefault(item.name, {"detalle": {}, "evidencias": []})
        d["caso"] = (item.function.__doc__ or "").strip()
        d["estado"] = "APROBADO" if rep.passed else ("FALLIDO" if rep.failed else "OMITIDO")
        if rep.failed:
            d["error"] = str(rep.longrepr)[-1500:]
        if html_extras is not None:
            extras = getattr(rep, "extras", [])
            extras.append(html_extras.html(_tabla_detalle(d) + _galeria(d)))
            rep.extras = extras


def pytest_html_report_title(report):
    report.title = f"Suite app nativa ({PLATAFORMA}) · {APP.name if APP else ''}"


# "Environment" y la fila de checkboxes/contadores ("0 Failed, 6 Passed...") las arma
# pytest-html directo en su template (index.jinja2), no a través de additional_summary --
# no hay hook que las saque, así que se ocultan con CSS. "Passed" -> "OK" también se hace
# en el navegador (cosmético, con un MutationObserver por si la tabla se vuelve a dibujar
# al filtrar/ordenar) y NO tocando el texto de la celda en pytest_html_results_table_row:
# pytest-html usa justo ese texto (_hydrate_data, en basereport.py) para clasificar cada
# fila y decidir si el filtro la muestra -- cambiarlo ahí rompía el filtrado entero y el
# reporte quedaba en blanco ("No results found. Check the filters.").
_CSS_JS_REPORTE = """
<style>
  #environment-header, #environment { display: none !important; }
  .summary .filter, .summary .controls .filters { display: none !important; }
</style>
<script>
(function () {
  function relabel(root) {
    (root || document).querySelectorAll('td.col-result').forEach(function (td) {
      if (td.textContent.trim() === 'Passed') { td.textContent = 'OK'; }
    });
  }
  relabel();
  var target = document.getElementById('results-table') || document.body;
  new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (n) { if (n.nodeType === 1) relabel(n); });
    });
  }).observe(target, { childList: true, subtree: true });
})();
</script>
"""


def pytest_html_results_summary(prefix, summary, postfix):
    prefix.append(_CSS_JS_REPORTE)
    info = RESULTADOS.get("_sesion", {}).get("detalle", {})
    if info:
        prefix.append("<p style='color:#333'>" + " · ".join(
            f"<b>{html.escape(k.replace('_', ' ').capitalize())}:</b> {html.escape(str(v))}"
            for k, v in info.items()) + "</p>")


def pytest_html_results_table_header(cells):
    # La columna "Test" mostraba la ruta del archivo + nombre interno de la función de
    # pytest (ej. "tests/generados/test_ca02_generado.py::test_ca02_ca1") -- se renombra
    # para dejar en claro que ahí va el nombre del caso, no una ruta técnica.
    if len(cells) > 1:
        cells[1] = "<th>Caso de prueba</th>"


def pytest_html_results_table_row(report, cells):
    if len(cells) < 2:
        return
    nombre = report.nodeid.split("::")[-1]
    caso = RESULTADOS.get(nombre, {}).get("caso") or nombre
    cells[1] = f'<td class="col-name">{html.escape(caso)}</td>'
