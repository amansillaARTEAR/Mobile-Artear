# Componente: Regresión completa
"""Regresión completa de la app TN (Android e iOS).

Recorre la app como un usuario: navbar, Home y sus módulos, todas las secciones, vivo,
radio, notas (abrir, compartir, volver), notificaciones (Campana y Ajustes), redes,
juegos y deeplinks. Cada caso deja capturas como evidencia.

Los elementos se ubican por texto visible (la app no expone ids estables), así que si un
texto cambia en la app hay que ajustar las constantes de arriba.
"""
import os
import time

import pytest

NAVBAR = ("Inicio", "Secciones", "Ajustes")
MODULOS_HOME = ("Últimas noticias", "TN Shorts", "TN Juegos", "Los tenés que ver")
SECCIONES = ("Todo Noticias", "Política", "Deportivo", "Show", "La Viola", "Tecno", "Con Bienestar",
             "TN Estilo", "TN Autos", "TN y la Gente", "TN Campo", "TN Running")
TEMAS_NOTIFICACIONES = ("Último momento", "Política", "Economía", "Deportes", "Show",
                        "Servicios", "Autos", "Salud", "Música", "Internacional")
REDES = ("Facebook", "X", "Instagram", "Youtube", "TikTok", "Telegram")
JUEGOS = ("Crucigrama", "One Up", "Rompecabezas", "Letras Locas", "Lluvia de objetos")
# La nota se puede cambiar con TN_DEEPLINK_NOTA (las notas viejas pueden dejar de existir).
DEEPLINK_NOTA = os.getenv("TN_DEEPLINK_NOTA", "https://tn.com.ar/opinion/2026/11/01/milei-apura-a-sus-funcionarios-por-la-suspension-de-las-paso-y-el-presupuesto-porque-necesita-votos-que-no-estan/")
DEEPLINK_SECCION = "https://tn.com.ar/deportes/"
DEEPLINK_VIVO = "https://tn.com.ar/envivo/24hs/"


# ---------------------------------------------------------------- helpers
def _tab(app, nombre):
    """Toca un ítem del navbar por nombre. Devuelve True si lo encontró."""
    item = next((i for i in app.navbar() if nombre.lower() in i["etiqueta"].lower()), None)
    if not item:
        return False
    item["el"].click()
    time.sleep(2)
    return True


def _ir_a_inicio(app):
    app.volver_al_inicio()
    _tab(app, "Inicio")


def _tocar_texto(app, texto, espera=3):
    els = app.buscar(texto)
    if not els:
        return False
    els[0].click()
    time.sleep(espera)
    return True


_MAY = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ"
_MIN = "abcdefghijklmnopqrstuvwxyzaeiouun"


def _buscar_ci(app, texto):
    """Como app.buscar() pero sin distinguir mayúsculas ni tildes (ej. títulos en MAYÚSCULAS)."""
    if app.ios:
        return app.buscar(texto)
    app.cerrar_dialogo_permisos()
    t = texto.translate(str.maketrans(_MAY, _MIN)).lower()
    norm = lambda attr: f"translate(@{attr},'{_MAY}','{_MIN}')"
    xp = f"//*[@displayed='true' and (contains({norm('text')},'{t}') or contains({norm('content-desc')},'{t}'))]"
    try:
        return app.d.find_elements("xpath", xp)
    except Exception:
        return []


def _textos_visibles(app):
    """Textos cortos visibles en pantalla (para diagnosticar qué títulos muestra la app)."""
    try:
        if app.ios:
            # Una sola llamada (page_source): leer .text elemento por elemento son cientos de viajes
            # a Device Farm en pantallas largas como una nota.
            import html as _html, re as _re
            fuente = app.d.page_source
            textos = (_html.unescape(t).strip() for t in _re.findall(
                r'<XCUIElementTypeStaticText[^>]*?label="([^"]*)"', fuente))
            return {t for t in textos if t and len(t) <= 40}
        els = app.d.find_elements("xpath", "//android.widget.TextView[@displayed='true']")
        return {e.text.strip() for e in els if e.text and len(e.text.strip()) <= 40}
    except Exception:
        return set()


def _swipe(app, direccion="down", fraccion=0.4):
    """Desliza la pantalla con un swipe W3C (dedo de 70% a 30% del alto para "down").
    Reemplaza a App.scroll(): el gesto "mobile: swipeGesture" no movía la Home ni Ajustes."""
    tam = app.d.get_window_size()
    x = tam["width"] // 2
    a, b = int(tam["height"] * (0.5 + fraccion / 2)), int(tam["height"] * (0.5 - fraccion / 2))
    if direccion != "down":
        a, b = b, a
    try:
        app.deslizar(x, a, x, b, 700)
        return True
    except Exception:
        return False


def _buscar_scrolleando(app, texto, max_scrolls=25, direccion="down", vistos=None):
    """Scrollea hasta que `texto` aparece en pantalla. Devuelve la lista de elementos o [].
    Si se pasa `vistos` (set), acumula los textos cortos que fue viendo, para diagnóstico."""
    for _ in range(max_scrolls):
        els = _buscar_ci(app, texto)
        if els:
            return els
        if vistos is not None:
            vistos |= _textos_visibles(app)
        if not _swipe(app, direccion):
            break
        time.sleep(1)
    return []


def _atras(app, veces=1):
    for _ in range(veces):
        if not app.atras():  # Android: botón atrás; iOS: "‹" del topbar o swipe desde el borde
            break


def _abrir_seccion(app, nombre):
    _tab(app, "Secciones")
    for _ in range(4):  # la lista puede quedar scrolleada de antes
        _swipe(app, "up", 0.5)
    els = _buscar_scrolleando(app, nombre, max_scrolls=6)
    if not els:  # algunas (ej. «TN en las redes») aparecen recién tras «Ver más categorías»
        mas = _buscar_scrolleando(app, "Ver más categorías", max_scrolls=6)
        if mas:
            mas[0].click()
            time.sleep(2)
            els = _buscar_scrolleando(app, nombre, max_scrolls=6)
    if not els:
        return False
    els[0].click()
    time.sleep(5)
    return True


# ---------------------------------------------------------------- casos
def test_reg01_navbar(app, registro):
    """REG-01: el navbar muestra Inicio, Secciones y Ajustes."""
    _ir_a_inicio(app)
    navbar = [i["etiqueta"] for i in app.navbar()]
    faltan = [n for n in NAVBAR if not any(n.lower() in e.lower() for e in navbar)]
    registro["detalle"].update({"navbar": navbar, "tiene_shorts": any("short" in e.lower() for e in navbar)})
    registro["evidencias"].append(app.captura("REG01", "navbar", f"Navbar: {navbar}"))
    assert not faltan, f"Faltan ítems en el navbar: {faltan}"


def test_reg02_home_modulos(app, registro):
    """REG-02: la Home carga y muestra sus módulos principales al scrollear, sin crash."""
    encontrados, vistos = {}, set()
    for i, modulo in enumerate(MODULOS_HOME, 1):
        _ir_a_inicio(app)  # cada módulo se busca desde arriba (el orden en la Home puede variar)
        _tab(app, "Inicio")  # 2do toque: vuelve la Home al tope
        els = _buscar_scrolleando(app, modulo, max_scrolls=60, vistos=vistos)
        encontrados[modulo] = bool(els)
        if els:
            registro["evidencias"].append(app.captura("REG02", f"{i}_{modulo[:12]}", f"Módulo «{modulo}»"))
        else:
            registro["evidencias"].append(app.captura("REG02", f"{i}_no_encontrado", f"Sin «{modulo}»"))
    errores = app.errores_nuevos()
    registro["detalle"].update({"modulos": encontrados, "crashes_o_anr": errores,
                                "textos_vistos": sorted(vistos)[:150]})
    assert not errores, f"Crash o ANR: {errores}"
    assert all(encontrados.values()), f"Módulos no encontrados: {[m for m, v in encontrados.items() if not v]}"


def test_reg03_secciones(app, registro):
    """REG-03: cada sección abre con contenido y se vuelve a la lista con Atrás."""
    resultado = {}
    for i, nombre in enumerate(SECCIONES, 1):
        abrio = _abrir_seccion(app, nombre)
        contenido = app.esperar_contenido(timeout=15) if abrio else False
        resultado[nombre] = abrio and contenido
        if abrio:
            registro["evidencias"].append(app.captura("REG03", f"{i:02d}", f"Sección «{nombre}»"))
            _atras(app)
    errores = app.errores_nuevos()
    registro["detalle"].update({"secciones": resultado, "crashes_o_anr": errores})
    assert not errores, f"Crash o ANR: {errores}"
    assert all(resultado.values()), f"Secciones que no abrieron: {[s for s, v in resultado.items() if not v]}"


def test_reg04_vivo(app, registro):
    """REG-04: «EN VIVO» del topbar abre el player en vivo y se cierra volviendo a la app."""
    _ir_a_inicio(app)
    assert _tocar_texto(app, "EN VIVO", espera=8), "No se encontró el botón «EN VIVO» en el topbar"
    if app.ios:
        # El player de iOS no muestra la etiqueta LIVE: se da por abierto si el navbar
        # desapareció (el player ocupa toda la pantalla).
        live = not app.navbar()
    else:
        live = bool(app.buscar("LIVE"))
    registro["evidencias"].append(app.captura("REG04", "1_player", "Player en vivo"))
    time.sleep(10)
    registro["evidencias"].append(app.captura("REG04", "2_reproduce", "Player 10 s después"))
    _atras(app)
    volvio = app.esperar_contenido()
    errores = app.errores_nuevos()
    registro["detalle"].update({"etiqueta_live": live, "volvio": volvio, "crashes_o_anr": errores})
    assert live, "El player no se abrió (no se ve LIVE / el navbar sigue visible)"
    assert volvio and not errores, f"No volvió bien del vivo o hubo errores: {errores}"


def test_reg05_radio(app, registro):
    """REG-05: TN radio abre su pantalla y el play no cierra la app."""
    assert _abrir_seccion(app, "TN radio"), "No se encontró «TN radio» en Secciones"
    pantalla = bool(app.buscar("Escuchá en vivo"))
    registro["evidencias"].append(app.captura("REG05", "1_pantalla", "Pantalla TN radio"))
    tam = app.d.get_window_size()
    app.tocar(tam["width"] // 2, int(tam["height"] * 0.45))  # botón play central
    time.sleep(6)
    registro["evidencias"].append(app.captura("REG05", "2_play", "Después de tocar play"))
    app.tocar(tam["width"] // 2, int(tam["height"] * 0.45))  # pausa
    errores = app.errores_nuevos()
    registro["detalle"].update({"pantalla_radio": pantalla, "crashes_o_anr": errores})
    _atras(app)
    assert pantalla, "No se ve el texto de la pantalla de radio"
    assert not errores and app.en_primer_plano(), f"La radio cerró la app o hubo errores: {errores}"


def test_reg06_nota_compartir_y_volver(app, registro):
    """REG-06: abrir una nota desde la Home, abrir compartir y volver a la Home."""
    _ir_a_inicio(app)
    app.marcar_inicio()
    tam = app.d.get_window_size()
    app.tocar(tam["width"] // 2, int(tam["height"] * 0.55))  # nota principal
    time.sleep(6)
    # Si aparece el interstitial no se cierra con Atrás (eso cierra también la nota): se
    # espera a que se cierre solo.
    time.sleep(10)
    registro["evidencias"].append(app.captura("REG06", "1_nota", "Nota abierta"))
    compartir = [e for e in app.topbar() if "compart" in e["etiqueta"].lower() or "share" in e["etiqueta"].lower()]
    hoja = False
    if compartir:
        compartir[-1]["el"].click()
        time.sleep(3)
        # La hoja nativa de iOS no dice "Compartir" (viene en el idioma del sistema: "Copy", etc.)
        hoja = any(app.buscar(t) for t in ("Compartir", "Copiar", "Copy"))
        registro["evidencias"].append(app.captura("REG06", "2_compartir", "Hoja de compartir"))
        _atras(app)
    _atras(app)
    volvio = app.volver_al_inicio()
    registro["evidencias"].append(app.captura("REG06", "3_vuelta", "De vuelta en la Home"))
    errores = app.errores_nuevos()
    registro["detalle"].update({"boton_compartir": bool(compartir), "hoja_compartir": hoja,
                                "volvio_home": volvio, "crashes_o_anr": errores})
    assert not errores, f"Crash o ANR: {errores}"
    assert volvio, "No se pudo volver a la Home desde la nota"


def test_reg07_ajustes_notificaciones(app, registro):
    """REG-07: Ajustes lista los temas de notificaciones y la versión de la app."""
    _ir_a_inicio(app)
    assert _tab(app, "Ajustes"), "No se encontró «Ajustes» en el navbar"
    temas = {t: bool(_buscar_scrolleando(app, t, max_scrolls=8)) for t in TEMAS_NOTIFICACIONES}
    version = _buscar_scrolleando(app, "Versión", max_scrolls=5)
    registro["detalle"].update({"temas": temas, "version": app.etiqueta(version[0]) if version else None})
    registro["evidencias"].append(app.captura("REG07", "ajustes", "Ajustes: temas y versión"))
    assert all(temas.values()), f"Temas no encontrados: {[t for t, v in temas.items() if not v]}"
    assert version, "No se ve la versión de la app en Ajustes"


def test_reg08_toggle_notificacion(app, registro):
    """REG-08: activar y desactivar un tema de notificaciones cambia el switch y se restaura."""
    _tab(app, "Ajustes")
    for _ in range(3):
        _swipe(app, "up", 0.5)
    if app.ios:
        # Los toggles de iOS pueden ser custom (el estado igual viene en "value" "0"/"1"). Después
        # de tocar uno la pantalla se refresca (ej. alerta de permiso de notificaciones), así que
        # el elemento se vuelve a buscar cada vez en vez de reusar una referencia vieja.
        def hallar():
            for q in ("type == 'XCUIElementTypeSwitch'", "value IN {'0', '1'}"):
                els = app.d.find_elements("-ios predicate string", q)
                if els:
                    return els[0]
            return None
        estado = lambda: "true" if (hallar().get_attribute("value") in ("1", "true")) else "false"
        tocar = lambda: hallar().click()
        sw = hallar()
        if sw is not None:
            registro["detalle"]["tipo_switch"] = sw.get_attribute("type")
    else:
        def hallar():
            els = app.d.find_elements("xpath", "//*[@checkable='true' and @displayed='true']")
            return els[0] if els else None
        estado = lambda: hallar().get_attribute("checked")
        tocar = lambda: hallar().click()
        sw = hallar()
    assert sw is not None, "No se encontraron switches de notificaciones"
    antes = estado()
    tocar()
    time.sleep(2)
    app.cerrar_dialogo_permisos()
    despues = estado()
    registro["evidencias"].append(app.captura("REG08", "1_cambiado", f"Switch: {antes} → {despues}"))
    tocar()  # restaura
    time.sleep(2)
    app.cerrar_dialogo_permisos()
    restaurado = estado()
    registro["evidencias"].append(app.captura("REG08", "2_restaurado", f"Switch restaurado: {restaurado}"))
    registro["detalle"].update({"antes": antes, "despues": despues, "restaurado": restaurado})
    assert antes != despues, "El switch no cambió de estado"
    assert restaurado == antes, "El switch no volvió a su estado original"


def test_reg09_campana(app, registro):
    """REG-09: la campana del topbar abre la pantalla de Notificaciones."""
    _ir_a_inicio(app)
    top = app.topbar()
    assert top, "No se encontró el topbar"
    top[0]["el"].click()  # la campana es el primer elemento del topbar
    time.sleep(3)
    pantalla = bool(app.buscar("Notificaciones"))
    registro["evidencias"].append(app.captura("REG09", "campana", "Pantalla de notificaciones"))
    _atras(app)
    registro["detalle"]["pantalla_notificaciones"] = pantalla
    assert pantalla, "La campana no abrió la pantalla de Notificaciones"


def test_reg10_redes(app, registro):
    """REG-10: «TN en las redes» lista las 6 redes."""
    assert _abrir_seccion(app, "TN en las redes"), "No se encontró «TN en las redes» en Secciones"
    redes = {r: bool(app.buscar(r)) for r in REDES}
    registro["evidencias"].append(app.captura("REG10", "redes", "TN en las redes"))
    registro["detalle"]["redes"] = redes
    _atras(app)
    assert all(redes.values()), f"Redes no encontradas: {[r for r, v in redes.items() if not v]}"


def test_reg11_juegos(app, registro):
    """REG-11: el módulo TN Juegos muestra los juegos en el carrusel lateral."""
    _ir_a_inicio(app)
    _tab(app, "Inicio")
    assert _buscar_scrolleando(app, "Juegos", max_scrolls=60), "No se encontró el módulo «TN Juegos»"
    _swipe(app, "down", 0.2)
    vistos = set()
    for i in range(6):
        vistos |= {j for j in JUEGOS if app.buscar(j)}
        registro["evidencias"].append(app.captura("REG11", f"{i + 1}", "Carrusel de juegos"))
        tam = app.d.get_window_size()
        juego = app.buscar(next(iter(JUEGOS)))  # ubica la fila del carrusel
        y = juego[0].rect["y"] + 20 if juego else int(tam["height"] * 0.5)
        app.deslizar(int(tam["width"] * 0.85), y, int(tam["width"] * 0.15), y, 400)
        time.sleep(1)
    registro["detalle"]["juegos_vistos"] = sorted(vistos)
    assert set(JUEGOS) <= vistos, f"Juegos no vistos: {sorted(set(JUEGOS) - vistos)}"


def _deeplink(app, registro, caso, url):
    if app.ios:
        # En AWS Device Farm la app se re-firma y los universal links abren Safari en vez de la app.
        pytest.skip("Deeplinks no concluyentes en Device Farm (iOS)")
    app.d.execute_script("mobile: deepLink", {"url": url, "package": app.paquete})
    time.sleep(8)
    en_app = app.en_primer_plano()
    registro["evidencias"].append(app.captura(caso, "deeplink", f"Deeplink: {url}"))
    _atras(app, 2)
    app.volver_a_la_app()
    registro["detalle"].update({"url": url, "abrio_en_app": en_app})
    assert en_app, f"El deeplink {url} no abrió la app"


def test_reg12_deeplink_nota(app, registro):
    """REG-12: un link de nota de tn.com.ar abre la nota dentro de la app."""
    _deeplink(app, registro, "REG12", DEEPLINK_NOTA)


def test_reg13_deeplink_seccion(app, registro):
    """REG-13: un link de sección de tn.com.ar abre la sección dentro de la app."""
    _deeplink(app, registro, "REG13", DEEPLINK_SECCION)


def test_reg14_deeplink_vivo(app, registro):
    """REG-14: el link del vivo de tn.com.ar abre el player dentro de la app."""
    _deeplink(app, registro, "REG14", DEEPLINK_VIVO)


def test_reg15_estabilidad_final(app, registro):
    """REG-15: después de toda la regresión la app sigue abierta y sin crashes."""
    app.volver_a_la_app()
    _ir_a_inicio(app)
    errores = app.errores_nuevos()
    registro["evidencias"].append(app.captura("REG15", "final", "Estado final"))
    registro["detalle"]["crashes_o_anr"] = errores
    assert app.en_primer_plano() and not errores, f"La app no quedó estable: {errores}"


def _abrir_nota_comun(app, registro, intentos=6):
    """Abre una nota de la Home que NO sea un liveblog («Minuto a minuto») ni tenga el player de
    vivo. Prueba una nota por intento, scrolleando la Home un poco más cada vez. Devuelve True si
    quedó parada en una nota común."""
    tam = app.d.get_window_size()
    for n in range(intentos):
        _ir_a_inicio(app)
        _tab(app, "Inicio")
        for _ in range(n):
            _swipe(app, "down", 0.4)
        app.tocar(tam["width"] // 2, int(tam["height"] * 0.55))
        time.sleep(14)  # incluye la espera del interstitial, como en REG-06
        if not app.buscar("Minuto a minuto") and not app.buscar("EN VIVO"):
            return True
        registro["detalle"].setdefault("notas_descartadas", []).append(n + 1)
        _atras(app)
    return False


def _scroll_nota(app):
    """Baja una "página" dentro de una nota. En iOS el arrastre simple no mueve la nota, así que
    se usa el gesto nativo "mobile: swipe"."""
    if app.ios:
        try:
            app.d.execute_script("mobile: swipe", {"direction": "up"})
            return True
        except Exception:
            return False
    return _swipe(app, "down", 0.6)


def _scrollear_hasta_el_final(app, registro, caso, max_scrolls=40):
    """Baja la nota hasta que la pantalla deja de cambiar (llegó al final). Deja una captura
    cada 3 scrolls. Devuelve la cantidad de scrolls que hizo."""
    import hashlib
    ultima, iguales = None, 0
    for i in range(1, max_scrolls + 1):
        _scroll_nota(app)
        time.sleep(1.5)
        huella = hashlib.md5(app.d.get_screenshot_as_base64().encode()).hexdigest()
        iguales = iguales + 1 if huella == ultima else 0
        ultima = huella
        if i % 3 == 0:
            registro["evidencias"].append(app.captura(caso, f"{i:02d}_scroll", f"Nota, scroll {i}"))
        if iguales >= 2:
            return i
    return max_scrolls


def test_reg16_tags_nota(app, registro):
    """REG-16: (exploratorio) una nota común muestra sus tags al final y tocar uno abre su listado."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    registro["evidencias"].append(app.captura("REG16", "00_nota", "Nota abierta"))
    n = _scrollear_hasta_el_final(app, registro, "REG16")
    registro["evidencias"].append(app.captura("REG16", "99_final", "Final de la nota"))
    registro["detalle"]["scrolls_hasta_el_final"] = n
