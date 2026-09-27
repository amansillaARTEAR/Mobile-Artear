"""AMR-2083 · TN Videos verticales | Navbar | Crear acceso en navbar.

CA1: Se debe incorporar en el navbar el acceso a la nueva sección de video.
CA2: Se debe abrir como una portada manteniendo el topbar de portada, y el navbar abajo.
CA3: Al abrir la sección se debe mostrar el reproductor como el de short player pero no en formato modal.

Diseño (Figma, TN-App-Navigation 9904-54301): navbar Inicio · Shorts · Secciones · Perfil; la sección
Shorts mantiene el topbar (campana, logo, EN VIVO) y muestra las pestañas «Lo importante» / «Tenés que ver».
El nombre del acceso se puede cambiar con TN_NAVBAR_VIDEOS (por defecto «Shorts»).
"""
import os
import time

import pytest

ACCESO = os.getenv("TN_NAVBAR_VIDEOS", "Shorts")
PESTANAS = ("Lo importante", "Tenés que ver")


def _etiquetas(items):
    return [i["etiqueta"] for i in items]


def _acceso(app):
    return next((i for i in app.navbar() if ACCESO.lower() in i["etiqueta"].lower()), None)


def _boton_cerrar(app):
    """Botón «Cerrar»/«Close» (indica que la sección se abrió como modal)."""
    return [e for e in (app.etiqueta(x) for x in app.buscar("errar") + app.buscar("lose"))
            if e.strip().lower() in ("cerrar", "close", "cerrar reproductor")]


def _ir_a_inicio(app):
    app.volver_al_inicio()
    inicio = next((i for i in app.navbar() if "inicio" in i["etiqueta"].lower()), None)
    if inicio:
        inicio["el"].click()
        time.sleep(2)


def _abrir_seccion(app):
    _ir_a_inicio(app)
    acceso = _acceso(app)
    if not acceso:
        pytest.skip(f"El APK no tiene el acceso «{ACCESO}» en el navbar (ver CA1)")
    acceso["el"].click()
    time.sleep(4)
    return acceso


def test_amr2083_ca1_acceso_en_navbar(app, registro):
    """AMR-2083 CA1: el navbar incluye el acceso a la sección de videos verticales."""
    _ir_a_inicio(app)
    navbar = app.navbar()
    orden = _etiquetas(navbar)
    tooltip = [app.etiqueta(e) for e in app.buscar("videos verticales")]
    registro["detalle"].update({"acceso_buscado": ACCESO, "navbar": orden,
                                "orden_esperado_diseno": ["Inicio", "Shorts", "Secciones", "Perfil"],
                                "tooltip_nuevo": tooltip})
    registro["evidencias"].append(app.captura("AMR2083_CA1", "navbar", f"Navbar en inicio: {orden}"))
    assert navbar, "No se encontró la barra de navegación inferior"
    assert _acceso(app), f"El navbar no tiene el acceso «{ACCESO}». Navbar actual: {orden}"


def test_amr2083_ca2_portada_con_topbar_y_navbar(app, registro):
    """AMR-2083 CA2: la sección abre como portada, con el topbar de portada arriba y el navbar abajo."""
    _ir_a_inicio(app)
    topbar_inicio = _etiquetas(app.topbar())
    _abrir_seccion(app)
    topbar = _etiquetas(app.topbar())
    navbar = app.navbar()
    acceso = _acceso(app)
    cerrar = _boton_cerrar(app)
    registro["detalle"].update({"topbar_en_inicio": topbar_inicio, "topbar_en_seccion": topbar,
                                "navbar_en_seccion": _etiquetas(navbar),
                                "acceso_seleccionado": bool(acceso and acceso["seleccionado"]),
                                "boton_cerrar_modal": cerrar})
    registro["evidencias"].append(app.captura("AMR2083_CA2", "seccion", f"Sección abierta · topbar: {topbar}"))
    faltan = [t for t in topbar_inicio if t not in topbar]
    assert not faltan, f"El topbar de la sección no mantiene elementos del topbar de portada: {faltan}"
    assert acceso, "El navbar no se ve dentro de la sección"
    assert not cerrar, "La sección muestra un botón «Cerrar» propio de un modal"


def test_amr2083_ca3_reproductor_no_modal(app, registro):
    """AMR-2083 CA3: la sección muestra el reproductor tipo short player, integrado (no modal)."""
    _abrir_seccion(app)
    pestanas = {p: bool(app.buscar(p)) for p in PESTANAS}
    registro["evidencias"].append(app.captura("AMR2083_CA3", "1_reproductor", f"Reproductor · pestañas: {pestanas}"))
    # Swipe vertical para pasar al siguiente video, como en el short player
    tam = app.d.get_window_size()
    app.d.swipe(tam["width"] // 2, int(tam["height"] * 0.7), tam["width"] // 2, int(tam["height"] * 0.3), 300)
    time.sleep(3)
    navbar_despues = _etiquetas(app.navbar())
    registro["evidencias"].append(app.captura("AMR2083_CA3", "2_siguiente", "Después del swipe al siguiente video"))
    errores = app.errores_nuevos()
    cerrar = _boton_cerrar(app)
    registro["detalle"].update({"pestanas_short_player": pestanas, "navbar_tras_swipe": navbar_despues,
                                "boton_cerrar_modal": cerrar, "crashes_o_anr": errores})
    assert all(pestanas.values()), f"Faltan pestañas del short player: {[p for p, v in pestanas.items() if not v]}"
    assert any(ACCESO.lower() in n.lower() for n in navbar_despues), "El navbar desaparece al pasar de video (comportamiento de modal)"
    assert not cerrar, "El reproductor muestra un botón «Cerrar» propio de un modal"
    assert not errores, f"Crash o ANR: {errores}"
