import html
import json
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.common.base import AppiumOptions

import config
import limpieza
from helpers.player import Player

try:
    from pytest_html import extras as html_extras
except ImportError:  # sin pytest-html se ejecuta igual, solo sin reporte HTML
    html_extras = None

RESULTADOS = {}
SALIDA = None
PLATAFORMA = None


def pytest_addoption(parser):
    parser.addoption("--plataforma", default="android", choices=["android", "ios"],
                     help="Plataforma a probar: android o ios")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Crea la carpeta de la corrida y ubica el reporte HTML dentro de ella."""
    global SALIDA, PLATAFORMA
    PLATAFORMA = config.getoption("--plataforma")
    vencidos = limpieza.limpiar()  # borra corridas e informes con más de 48 h
    if vencidos:
        print(f"Limpieza: se borraron {len(vencidos)} resultados con más de {limpieza.HORAS:g} h")
    SALIDA = limpieza.RAIZ / PLATAFORMA / "corridas" / time.strftime("%Y%m%d-%H%M%S")
    (limpieza.RAIZ / PLATAFORMA / "informes").mkdir(parents=True, exist_ok=True)
    (SALIDA / "evidencias").mkdir(parents=True, exist_ok=True)
    if hasattr(config.option, "htmlpath"):
        # El reporte queda junto a sus evidencias, así las imágenes se ven al abrirlo
        config.option.htmlpath = str(SALIDA / "reporte.html")
        config.option.self_contained_html = False


@pytest.fixture(scope="session")
def plataforma():
    return PLATAFORMA


@pytest.fixture(scope="session")
def driver(plataforma):
    opciones = AppiumOptions()
    opciones.load_capabilities(config.caps_para(plataforma))
    d = webdriver.Remote(config.APPIUM_URL, options=opciones)
    yield d
    d.quit()


@pytest.fixture(scope="session")
def salida():
    yield SALIDA
    (SALIDA / "resultados.json").write_text(
        json.dumps(RESULTADOS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados, evidencias y reporte en: {SALIDA.resolve()}")


@pytest.fixture(scope="session")
def player(driver, plataforma, salida):
    return Player(driver, plataforma, salida)


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
    filas = "".join(
        f"<tr><td style='padding:4px 8px;border:1px solid #ddd;font-weight:bold;vertical-align:top;color:#333'>"
        f"{html.escape(str(k))}</td><td style='padding:4px 8px;border:1px solid #ddd;color:#333'>{_valor(v)}</td></tr>"
        for k, v in datos.get("detalle", {}).items())
    caso = html.escape(datos.get("caso", ""))
    return (f"<p style='color:#333;font-size:13px;margin:6px 0'><b>{caso}</b></p>"
            f"<table style='border-collapse:collapse;margin-bottom:8px;font-size:12px'>{filas}</table>")


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
    report.title = f"TNARC-4366 · Suite Appium · {PLATAFORMA.capitalize() if PLATAFORMA else ''}"


def pytest_html_results_summary(prefix, summary, postfix):
    info = RESULTADOS.get("test_00_version", {}).get("detalle", {})
    if info:
        prefix.append(
            f"<p style='color:#333'><b>Versión:</b> {html.escape(str(info.get('version_cargada')))} · "
            f"<b>Dispositivo:</b> {html.escape(str(info.get('dispositivo')))} · "
            f"<b>Sistema:</b> {html.escape(str(info.get('sistema')))} · "
            f"<b>URL:</b> {html.escape(str(info.get('url')))}</p>")
