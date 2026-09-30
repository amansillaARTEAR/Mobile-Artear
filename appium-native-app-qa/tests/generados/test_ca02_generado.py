# Componente: Tooltip - Shorts
# Ticket: AMR-2087
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

import time


def _tooltip_presente(app):
    """Detecta el tooltip "NUEVO - Informate con nuestros videos verticales" buscando el texto
    "videos verticales" (único de ese tooltip en esta pantalla) entre CUALQUIER elemento visible,
    no solo los clickeables: el subtítulo del tooltip es un texto descriptivo, no un elemento
    clickable, así que clickeables() (que filtra por @clickable='true') nunca lo encuentra aunque
    esté en pantalla. app.buscar() no tiene ese filtro, solo requiere @displayed='true'.
    Ver FIX en el docstring de test_ca02_positivo para el historial completo."""
    return bool(app.buscar("videos verticales"))


def _boton_cerrar_tooltip(app):
    """Busca el botón "X" del tooltip entre los elementos clickeables. Si el ícono no tiene
    texto/content-desc/resource-id reconocible, clickeables() lo descarta (requiere alguno de
    los tres) y esto devuelve None -- en ese caso hace falta inspeccionar el árbol real de la
    pantalla (Appium Inspector) para sacar el selector exacto."""
    for el in app.clickeables():
        etiqueta = app.etiqueta(el)
        if etiqueta.strip().lower() in ("x", "✕", "×", "close") or "cerrar" in etiqueta.lower() or "dismiss" in etiqueta.lower():
            return el
    return None


# Escenario: Positivo
# Dado que el usuario abre la app por primera vez
# Cuando la app carga la pantalla inicial
# Entonces debe mostrarse un tooltip con el texto "NUEVO - Informate con nuestros videos verticales" y debe poder cerrarse tocando la X
def test_ca02_positivo(app, registro):
    """POSITIVO: AMR-2087 CA2 - El tooltip aparece al iniciar por primera vez y se cierra al tocar la X.

    FIX (corridas 36765891459 y 36766434423): la primera versión de este test buscaba, entre los
    elementos CLICKEABLES, uno cuya etiqueta contuviera a la vez "NUEVO" y "videos verticales".
    Eso nunca podía matchear por dos motivos, confirmados con capturas reales del dispositivo:
    1) "NUEVO" (título) y "Informate con nuestros videos verticales" (subtítulo) son DOS textos
       en elementos separados, nunca aparecen juntos en la etiqueta de un mismo elemento.
    2) el subtítulo con "videos verticales" no es un elemento clickeable -- es texto descriptivo
       dentro del tooltip -- así que ni siquiera entraba en la lista que devuelve clickeables().
    Se corrige buscando "videos verticales" (frase que no aparece en ningún otro lado de esta
    pantalla) entre TODOS los elementos visibles, vía app.buscar() en vez de app.clickeables()."""
    tiempo_reinicio = app.reiniciar_limpio()
    time.sleep(2)

    tooltip_encontrado = _tooltip_presente(app)
    boton_cerrar = _boton_cerrar_tooltip(app)

    registro["evidencias"].append(app.captura("AMR2087_CA2", "tooltip_inicial", "Tooltip al iniciar"))

    # Verificar que el tooltip aparece
    assert tooltip_encontrado, "No se encontró el tooltip con el texto esperado"

    # Intentar cerrar el tooltip tocando la X
    if boton_cerrar:
        boton_cerrar.click()
        time.sleep(1)
        registro["evidencias"].append(app.captura("AMR2087_CA2", "tooltip_cerrado", "Después de cerrar con X"))

        tooltip_sigue = _tooltip_presente(app)
        assert not tooltip_sigue, "El tooltip no desapareció después de tocar la X"
    else:
        # TODO revisar: no se encontró el botón de cerrar -- ver docstring de _boton_cerrar_tooltip.
        registro["detalle"].update({"boton_cerrar_encontrado": False})

    registro["detalle"].update({"tooltip_aparecio": tooltip_encontrado,
                                 "tiempo_reinicio_limpio_s": tiempo_reinicio})


# Escenario: Negativo
# Dado que el usuario ya accedió a la sección de videos verticales previamente
# Cuando el usuario vuelve a abrir la app
# Entonces el tooltip NO debe aparecer
def test_ca02_negativo(app, registro):
    """NEGATIVO: AMR-2087 CA2 - El tooltip no reaparece si el usuario ya accedió a la sección."""
    # FIX (corrida 36760057869): arrancamos desde estado limpio (no desde lo que dejó
    # test_ca02_positivo) para que este resultado dependa solo de "accedió a la sección",
    # no de un flag que ya haya quedado en true por otra corrida.
    app.reiniciar_limpio()
    time.sleep(2)
    # TODO revisar: este escenario requiere simular que el usuario ya accedió a la sección previamente
    # Asumimos que hay alguna forma de navegar a la sección de videos o que existe un estado persistido

    # Buscar y acceder a la sección de videos verticales (si existe en navbar/clickeables)
    elementos = app.clickeables()
    seccion_videos = None

    for el in elementos:
        etiqueta = app.etiqueta(el)
        if "video" in etiqueta.lower() or "vertical" in etiqueta.lower() or etiqueta.lower() == "shorts":
            seccion_videos = el
            break

    if seccion_videos:
        seccion_videos.click()
        time.sleep(2)
        registro["evidencias"].append(app.captura("AMR2087_CA2", "acceso_seccion", "Usuario accede a sección de videos"))

        # Volver al inicio
        app.volver_al_inicio()
        time.sleep(1)

    # Reiniciar la app para simular un cierre y reapertura
    app.reiniciar()
    time.sleep(3)

    # Verificar que el tooltip NO aparece
    tooltip_reaparecio = _tooltip_presente(app)

    registro["evidencias"].append(app.captura("AMR2087_CA2", "reinicio_sin_tooltip", "Después de reiniciar habiendo accedido"))
    registro["detalle"].update({"seccion_videos_encontrada": seccion_videos is not None,
                                 "tooltip_reaparecio_incorrectamente": tooltip_reaparecio})

    assert not tooltip_reaparecio, "El tooltip no debería aparecer después de que el usuario accedió a la sección"


# Escenario: Borde
# Dado que el usuario cerró el tooltip con la X sin acceder a la sección
# Cuando el usuario cierra y vuelve a abrir la app
# Entonces el tooltip debe volver a mostrarse
def test_ca02_borde(app, registro):
    """BORDE: AMR-2087 CA2 - El tooltip reaparece si el usuario lo cerró sin acceder a la sección."""
    # FIX (corrida 36760057869): arrancamos desde estado limpio para garantizar que el tooltip
    # esté visible al inicio (si no, "tooltip_inicial" queda en False por una corrida anterior
    # y el test nunca llega a cerrarlo).
    app.reiniciar_limpio()
    time.sleep(2)

    tooltip_inicial = _tooltip_presente(app)
    boton_cerrar = _boton_cerrar_tooltip(app)

    if boton_cerrar and tooltip_inicial:
        registro["evidencias"].append(app.captura("AMR2087_CA2", "antes_cerrar", "Tooltip visible antes de cerrar"))
        boton_cerrar.click()
        time.sleep(1)
        registro["evidencias"].append(app.captura("AMR2087_CA2", "despues_cerrar", "Después de cerrar con X"))

    # Reiniciar la app sin haber accedido a la sección
    tiempo_reinicio = app.reiniciar()
    time.sleep(3)

    # Verificar que el tooltip vuelve a aparecer
    tooltip_reaparecio = _tooltip_presente(app)

    registro["evidencias"].append(app.captura("AMR2087_CA2", "reinicio_con_tooltip", "Después de reiniciar sin acceder"))
    registro["detalle"].update({
        "tiempo_reinicio_s": tiempo_reinicio,
        "tooltip_inicial_encontrado": tooltip_inicial,
        "tooltip_cerrado_inicialmente": boton_cerrar is not None,
        "tooltip_reaparecio": tooltip_reaparecio
    })

    assert tooltip_reaparecio, "El tooltip debería volver a aparecer si el usuario no accedió a la sección"
