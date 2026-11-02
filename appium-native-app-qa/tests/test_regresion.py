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
        # Es una nota si el topbar tiene el botón de compartir (un aviso o un player no lo tienen) y
        # no es un liveblog.
        es_nota = any("compart" in e["etiqueta"].lower() or "share" in e["etiqueta"].lower() for e in app.topbar())
        if es_nota and not app.buscar("Minuto a minuto") and not app.buscar("EN VIVO"):
            return True
        registro["detalle"].setdefault("notas_descartadas", []).append(n + 1)
        _atras(app)
    return False


def _flick(app, x1, y1, x2, y2):
    """Deslizamiento rápido (con inercia) de (x1,y1) a (x2,y2). En iOS el arrastre simple no mueve
    las notas ni las filas de tags, así que se usa un gesto táctil W3C; en Android, el swipe normal."""
    if not app.ios:
        app.deslizar(x1, y1, x2, y2, 300)
        return True
    try:
        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput
        ab = ActionBuilder(app.d, mouse=PointerInput(interaction.POINTER_TOUCH, "finger"))
        ab.pointer_action.move_to_location(x1, y1)
        ab.pointer_action.pointer_down()
        ab.pointer_action.pause(0.05)
        ab.pointer_action.move_to_location(x2, y2)
        ab.pointer_action.release()
        ab.perform()
        return True
    except Exception:
        return False


def _cerrar_te_puede_interesar(app, intentos=4):
    """En Android, al bajar por una nota aparece el panel «Te puede interesar» pegado abajo, que tapa
    buena parte de la pantalla y se queda con los gestos (la nota deja de scrollear). Se cierra con
    su «X» (el tocable de la misma fila del título, a la derecha). El panel cambia de estado (asoma
    abajo, se abre a mitad de pantalla) y la «X» cambia de lugar, así que hay que tocarla más de una
    vez, volviéndola a buscar cada vez, hasta que el panel desaparece."""
    cerro = False
    for _ in range(intentos):
        try:
            titulo = _buscar_ci(app, "Te puede interesar")
            if not titulo:
                return cerro
            t = titulo[0].rect
            centro = t["y"] + t["height"] / 2
            todos = app.d.find_elements("xpath", "//*[@clickable='true' and @displayed='true']")
            derecha = [e for e in todos
                       if abs(e.rect["y"] + e.rect["height"] / 2 - centro) < 60 and e.rect["x"] >= t["x"] + t["width"] - 5]
            if not derecha:
                return cerro
            r = max(derecha, key=lambda e: e.rect["x"]).rect
            app.tocar(int(r["x"] + r["width"] / 2), int(r["y"] + r["height"] / 2))
        except Exception:
            time.sleep(0.5)  # el panel se está moviendo: se vuelve a intentar
            continue
        cerro = True
        time.sleep(1)
    return cerro


def _scroll_nota(app):
    """Baja casi una pantalla dentro de una nota (dedo de 80% a 25% del alto)."""
    tam = app.d.get_window_size()
    if not app.ios:
        # Android: arrastre corto y lento (sin inercia) para no saltearse secciones cortas como
        # «Temas de la nota», que con un gesto rápido quedan entre dos pantallas.
        _cerrar_te_puede_interesar(app)
        x = tam["width"] // 2
        app.deslizar(x, int(tam["height"] * 0.75), x, int(tam["height"] * 0.25), 1200)
        return True
    return _flick(app, tam["width"] // 2, int(tam["height"] * 0.8), tam["width"] // 2, int(tam["height"] * 0.25))


def _scrollear_hasta(app, texto, max_scrolls=60):
    """Baja la nota hasta que `texto` aparece en pantalla (sin distinguir mayúsculas/tildes).
    Devuelve la lista de elementos encontrados, o [] si llegó al límite sin verlo."""
    if not app.ios:
        # Android: scroll nativo de UiAutomator hasta que el texto aparece (mucho más rápido que
        # bajar de a pasos). Se cierra antes el panel «Te puede interesar», que trababa el scroll.
        import re
        _cerrar_te_puede_interesar(app)
        patron = "(?i).*" + re.sub(r"[aáeéiíoóuú]", lambda m: "[" + {"a": "aá", "e": "eé", "i": "ií", "o": "oó", "u": "uú"}[
            m.group(0).translate(str.maketrans("áéíóú", "aeiou"))] + "]", texto.lower()) + ".*"
        try:
            app.d.find_element(
                "-android uiautomator",
                'new UiScrollable(new UiSelector().scrollable(true)).setMaxSearchSwipes(%d)'
                '.scrollIntoView(new UiSelector().textMatches("%s"))' % (max_scrolls, patron))
        except Exception:
            pass  # no lo encontró por esta vía: se intenta igual el recorrido manual de abajo
        els = _buscar_ci(app, texto)
        if els:
            return els
    for _ in range(max_scrolls):
        els = _buscar_ci(app, texto)
        if els:
            return els
        _scroll_nota(app)
        time.sleep(1)
    return []


def _notas_visibles(app):
    """Titulares de notas visibles: textos largos. En Android las notas de un listado no son
    tocables con texto (son TextView sueltos), en iOS sí son botones."""
    if app.ios:
        return [app.etiqueta(e) for e in app.clickeables() if len(app.etiqueta(e)) > 25]
    try:
        els = app.d.find_elements("xpath", "//android.widget.TextView[@displayed='true']")
        return [e.text for e in els if e.text and len(e.text.strip()) > 25]
    except Exception:
        return []


def _huella(app):
    import hashlib
    return hashlib.md5(app.d.get_screenshot_as_base64().encode()).hexdigest()


def test_reg16_tags_nota(app, registro):
    """REG-16: «Temas de la nota» muestra los tags (píldoras), scrollean al costado si hay muchos y al tocar uno abre su listado."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    titulo = _scrollear_hasta(app, "Temas de la nota")
    registro["evidencias"].append(app.captura("REG16", "1_temas", "Sección «Temas de la nota»"))
    assert titulo, "La nota no muestra la sección «Temas de la nota»"
    # Las píldoras son los tocables que están justo debajo del título de la sección.
    tam = app.d.get_window_size()
    ancho, alto = tam["width"], tam["height"]
    y_titulo = titulo[0].rect["y"]

    def leer_pildoras():
        return [e for e in app.clickeables()
                if y_titulo < e.rect["y"] < y_titulo + alto * 0.25 and app.etiqueta(e)]

    pildoras = leer_pildoras()
    tags = [app.etiqueta(e) for e in pildoras]
    registro["detalle"]["tags"] = tags
    assert pildoras, "«Temas de la nota» no tiene ningún tag"

    # Scroll lateral: solo aplica si hay tantos tags que no entran en el ancho (no siempre pasa).
    # Una píldora cortada en el borde derecho (o izquierdo) indica que la fila se puede scrollear.
    def desborde(els):
        return any(e.rect["x"] + e.rect["width"] > ancho - 2 or e.rect["x"] < 2 for e in els)

    hay_desborde = desborde(pildoras)
    registro["detalle"]["hay_scroll_lateral"] = hay_desborde
    if hay_desborde:
        x_antes = {app.etiqueta(e): e.rect["x"] for e in pildoras}
        y_fila = int(pildoras[0].rect["y"] + pildoras[0].rect["height"] / 2)
        _flick(app, int(ancho * 0.85), y_fila, int(ancho * 0.15), y_fila)
        time.sleep(1.5)
        pildoras = leer_pildoras()
        x_despues = {app.etiqueta(e): e.rect["x"] for e in pildoras}
        movidas = [t for t in x_despues if t in x_antes and abs(x_despues[t] - x_antes[t]) > 20]
        nuevas = [t for t in x_despues if t not in x_antes]
        registro["detalle"]["tags_tras_scroll_lateral"] = list(x_despues)
        registro["evidencias"].append(app.captura("REG16", "2_scroll_lateral", f"Scroll lateral de tags: {list(x_despues)}"))
        assert movidas or nuevas, "El scroll lateral no movió la fila de tags"
        tags = [app.etiqueta(e) for e in pildoras]

    tag = tags[0]
    antes = _huella(app)
    pildoras[0].click()
    time.sleep(6)
    # El listado del tag es una pantalla propia de la app: el nombre del tag va en el título (arriba)
    # y debajo hay notas de ese tema (tarjetas tocables con un titular largo).
    en_titulo = any(e.rect["y"] < alto * 0.15 for e in _buscar_ci(app, tag))
    notas = _notas_visibles(app)
    abrio = _huella(app) != antes and en_titulo and bool(notas)
    registro["detalle"].update({"titulo_con_el_tag": en_titulo, "notas_en_el_listado": len(notas)})
    registro["evidencias"].append(app.captura("REG16", "3_listado", f"Listado del tag «{tag}»"))
    registro["detalle"].update({"tag_tocado": tag, "abrio_listado": abrio})
    _atras(app)
    volvio = app.esperar_contenido()
    registro["evidencias"].append(app.captura("REG16", "4_vuelta", "De vuelta en la nota"))
    assert abrio, f"Al tocar el tag «{tag}» no se abrió el listado de ese tag"
    assert volvio and app.en_primer_plano(), "No se pudo volver de la nota después de tocar el tag"


def test_reg17_lee_tambien(app, registro):
    """REG-17: el link «Lee también» de una nota común abre otra nota y se vuelve a la original."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    link = _scrollear_hasta(app, "Lee también")
    registro["evidencias"].append(app.captura("REG17", "1_lee_tambien", "«Lee también» en la nota"))
    assert link, "La nota no muestra ningún «Lee también»"
    # «Leé también» es solo el título de la sección: el link es la tarjeta de nota que está debajo.
    alto = app.d.get_window_size()["height"]
    y_titulo = link[0].rect["y"]
    tarjetas = [e for e in app.clickeables()
                if y_titulo + link[0].rect["height"] <= e.rect["y"] < y_titulo + alto * 0.3]
    registro["detalle"]["tarjetas"] = [app.etiqueta(e) for e in tarjetas]
    assert tarjetas, "«Leé también» no tiene ninguna nota debajo"
    antes = _huella(app)
    r = tarjetas[0].rect
    app.tocar(int(r["x"] + r["width"] / 2), int(r["y"] + r["height"] / 2))  # por coordenadas: el click del elemento falla en Android
    time.sleep(8)
    cambio = _huella(app) != antes
    registro["evidencias"].append(app.captura("REG17", "2_otra_nota", "Nota abierta desde «Lee también»"))
    registro["detalle"]["abrio_otra_nota"] = cambio
    _atras(app)
    volvio = app.esperar_contenido()
    registro["evidencias"].append(app.captura("REG17", "3_vuelta", "De vuelta en la nota original"))
    assert cambio, "Al tocar «Lee también» no se abrió otra nota"
    assert volvio and app.en_primer_plano(), "No se pudo volver a la nota original"


def _botones_en_la_fila(app, elemento):
    """Tocables (con o sin texto) que están en la misma fila que `elemento` y a su izquierda.
    Sirve para el botón de auriculares de la nota, que no tiene texto y va al lado de «Seguir»."""
    r = elemento.rect
    centro = r["y"] + r["height"] / 2
    try:
        if app.ios:
            todos = app.d.find_elements("-ios predicate string",
                                        "type IN {'XCUIElementTypeButton','XCUIElementTypeOther'} AND visible == 1")
        else:
            todos = app.d.find_elements("xpath", "//*[@clickable='true' and @displayed='true']")
    except Exception:
        return []
    fila = [e for e in todos
            if abs(e.rect["y"] + e.rect["height"] / 2 - centro) < 40 and e.rect["x"] + e.rect["width"] <= r["x"]
            and 20 < e.rect["width"] < 200]
    return sorted(fila, key=lambda e: e.rect["x"])


def _tiempo_reproductor(app):
    """Primer contador mm:ss visible (posición del audio), o None."""
    import re
    for t in sorted(_textos_visibles(app)):
        if re.fullmatch(r"\d{1,2}:\d{2}", t):
            return t
    return None


def test_reg18_audionota(app, registro):
    """REG-18: el botón de audionota (auriculares) abre el reproductor «Escuchando artículo» con el primer toque y el audio avanza."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    seguir = _scrollear_hasta(app, "Seguir", max_scrolls=15)
    assert seguir, "La nota no muestra la fila con el botón de audionota y «Seguir»"
    botones = _botones_en_la_fila(app, seguir[0])
    assert botones, "No se encontró el botón de audionota (auriculares) junto a «Seguir»"
    registro["evidencias"].append(app.captura("REG18", "1_nota", "Nota con el botón de audionota"))
    botones[0].click()  # un solo toque: es justo lo que se valida
    inicio = time.time()
    abrio = False
    while time.time() - inicio < 12:  # el reproductor puede tardar en cargar la primera vez
        time.sleep(1)
        if _buscar_ci(app, "Escuchando"):
            abrio = True
            break
    registro["detalle"]["segundos_hasta_reproductor"] = round(time.time() - inicio, 1) if abrio else None
    registro["evidencias"].append(app.captura("REG18", "2_reproductor", "Reproductor tras el primer toque"))
    registro["detalle"]["reproductor_con_un_toque"] = abrio
    if not abrio:
        # Evidencia para el reporte de bug: ¿el botón es el correcto y responde recién al segundo toque?
        botones[0].click()
        time.sleep(5)
        registro["detalle"]["reproductor_con_dos_toques"] = bool(_buscar_ci(app, "Escuchando"))
        registro["evidencias"].append(app.captura("REG18", "2b_segundo_toque", "Reproductor tras el segundo toque"))
    assert abrio, "Con el primer toque no se abrió el reproductor de la audionota"
    t1 = _tiempo_reproductor(app)
    time.sleep(6)
    t2 = _tiempo_reproductor(app)
    registro["evidencias"].append(app.captura("REG18", "3_avanza", f"Audio: {t1} → {t2}"))
    registro["detalle"].update({"tiempo_inicial": t1, "tiempo_despues": t2})
    if not (t1 and t2):
        registro["detalle"]["textos_en_pantalla"] = sorted(_textos_visibles(app))[:30]
    assert t1 and t2 and t1 != t2, f"El audio no avanza ({t1} → {t2})"


def test_reg19_seguir_en_google(app, registro):
    """REG-19: «Seguir» (Google) sale de la app y abre la página de Google para agregar TN como fuente preferida."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    seguir = _scrollear_hasta(app, "Seguir", max_scrolls=15)
    assert seguir, "La nota no muestra el botón «Seguir» de Google"
    registro["evidencias"].append(app.captura("REG19", "1_nota", "Nota con «Seguir»"))
    seguir[0].click()
    time.sleep(8)
    salio = not app.en_primer_plano()
    google = False
    if salio and not app.ios:  # en Android se puede leer el navegador; en iOS la sesión queda atada a la app
        google = bool(_buscar_ci(app, "google.com"))
        registro["detalle"]["texto_pantalla"] = sorted(_textos_visibles(app))[:40]
    registro["evidencias"].append(app.captura("REG19", "2_google", "Destino de «Seguir»"))
    registro["detalle"].update({"salio_de_la_app": salio, "en_google": google})
    try:
        app.volver_a_la_app()
    except Exception:
        pass
    assert salio, "«Seguir» no abrió el navegador"
    assert app.ios or google, "El navegador no abrió una página de google.com"


def test_reg20_mas_sobre(app, registro):
    """REG-20: «Más sobre <sección>» al final de la nota muestra notas relacionadas y al tocar una abre otra nota."""
    assert _abrir_nota_comun(app, registro), "No se encontró una nota común (todas eran liveblog)"
    titulo = _scrollear_hasta(app, "Más sobre")
    registro["evidencias"].append(app.captura("REG20", "1_mas_sobre", "Bloque «Más sobre»"))
    assert titulo, "La nota no muestra el bloque «Más sobre»"
    alto = app.d.get_window_size()["height"]
    y = titulo[0].rect["y"]
    tarjetas = [e for e in app.clickeables()
                if y + titulo[0].rect["height"] <= e.rect["y"] < y + alto * 0.5 and len(app.etiqueta(e)) > 25]
    registro["detalle"]["tarjetas"] = [app.etiqueta(e) for e in tarjetas]
    assert tarjetas, "«Más sobre» no lista ninguna nota"
    antes = _huella(app)
    tarjetas[0].click()
    time.sleep(8)
    cambio = _huella(app) != antes
    registro["evidencias"].append(app.captura("REG20", "2_otra_nota", "Nota abierta desde «Más sobre»"))
    registro["detalle"]["abrio_otra_nota"] = cambio
    _atras(app)
    volvio = app.esperar_contenido()
    assert cambio, "Al tocar una nota de «Más sobre» no se abrió otra nota"
    assert volvio and app.en_primer_plano(), "No se pudo volver a la nota original"
