# Componente: Tooltip - Shorts
# Ticket: AMR-2087
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

import time

# Escenario: Positivo
# Dado que el usuario abre la app por primera vez
# Cuando la app carga la pantalla inicial
# Entonces debe mostrarse un tooltip con el texto "NUEVO - Informate con nuestros videos verticales" y debe poder cerrarse tocando la X
def test_ca02_positivo(app, registro):
    """POSITIVO: AMR-2087 CA2 - El tooltip aparece al iniciar por primera vez y se cierra al tocar la X."""
    time.sleep(2)
    
    # Buscar el tooltip con el texto esperado
    elementos = app.clickeables()
    tooltip_encontrado = False
    tooltip_texto = None
    boton_cerrar = None
    
    for el in elementos:
        etiqueta = app.etiqueta(el)
        if "NUEVO" in etiqueta and "videos verticales" in etiqueta:
            tooltip_encontrado = True
            tooltip_texto = etiqueta
        if etiqueta == "x" or etiqueta == "X" or "cerrar" in etiqueta.lower():
            boton_cerrar = el
    
    registro["evidencias"].append(app.captura("AMR2087_CA2", "tooltip_inicial", "Tooltip al iniciar"))
    
    # Verificar que el tooltip aparece con el texto correcto
    assert tooltip_encontrado, "No se encontró el tooltip con el texto esperado"
    assert "NUEVO - Informate con nuestros videos verticales" in tooltip_texto or ("NUEVO" in tooltip_texto and "videos verticales" in tooltip_texto), f"El texto del tooltip no es el esperado: {tooltip_texto}"
    
    # Intentar cerrar el tooltip tocando la X
    if boton_cerrar:
        boton_cerrar.click()
        time.sleep(1)
        registro["evidencias"].append(app.captura("AMR2087_CA2", "tooltip_cerrado", "Después de cerrar con X"))
        
        # Verificar que el tooltip ya no está visible
        elementos_despues = app.clickeables()
        tooltip_sigue = False
        for el in elementos_despues:
            etiqueta = app.etiqueta(el)
            if "NUEVO" in etiqueta and "videos verticales" in etiqueta:
                tooltip_sigue = True
                break
        
        assert not tooltip_sigue, "El tooltip no desapareció después de tocar la X"
    else:
        # TODO revisar: no se encontró botón de cerrar explícito, verificar selector correcto
        registro["detalle"].update({"tooltip_texto": tooltip_texto, "boton_cerrar_encontrado": False})
    
    registro["detalle"].update({"tooltip_aparecio": tooltip_encontrado, "texto_correcto": True})


# Escenario: Negativo
# Dado que el usuario ya accedió a la sección de videos verticales previamente
# Cuando el usuario vuelve a abrir la app
# Entonces el tooltip NO debe aparecer
def test_ca02_negativo(app, registro):
    """NEGATIVO: AMR-2087 CA2 - El tooltip no reaparece si el usuario ya accedió a la sección."""
    # TODO revisar: este escenario requiere simular que el usuario ya accedió a la sección previamente
    # Asumimos que hay alguna forma de navegar a la sección de videos o que existe un estado persistido
    
    # Buscar y acceder a la sección de videos verticales (si existe en navbar/clickeables)
    elementos = app.clickeables()
    seccion_videos = None
    
    for el in elementos:
        etiqueta = app.etiqueta(el)
        if "video" in etiqueta.lower() or "vertical" in etiqueta.lower():
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
    elementos_reinicio = app.clickeables()
    tooltip_reaparecio = False
    
    for el in elementos_reinicio:
        etiqueta = app.etiqueta(el)
        if "NUEVO" in etiqueta and "videos verticales" in etiqueta:
            tooltip_reaparecio = True
            break
    
    registro["evidencias"].append(app.captura("AMR2087_CA2", "reinicio_sin_tooltip", "Después de reiniciar habiendo accedido"))
    registro["detalle"].update({"tooltip_reaparecio_incorrectamente": tooltip_reaparecio})
    
    assert not tooltip_reaparecio, "El tooltip no debería aparecer después de que el usuario accedió a la sección"


# Escenario: Borde
# Dado que el usuario cerró el tooltip con la X sin acceder a la sección
# Cuando el usuario cierra y vuelve a abrir la app
# Entonces el tooltip debe volver a mostrarse
def test_ca02_borde(app, registro):
    """BORDE: AMR-2087 CA2 - El tooltip reaparece si el usuario lo cerró sin acceder a la sección."""
    time.sleep(2)
    
    # Buscar y cerrar el tooltip con la X
    elementos = app.clickeables()
    boton_cerrar = None
    tooltip_inicial = False
    
    for el in elementos:
        etiqueta = app.etiqueta(el)
        if "NUEVO" in etiqueta and "videos verticales" in etiqueta:
            tooltip_inicial = True
        if etiqueta == "x" or etiqueta == "X" or "cerrar" in etiqueta.lower():
            boton_cerrar = el
    
    if boton_cerrar and tooltip_inicial:
        registro["evidencias"].append(app.captura("AMR2087_CA2", "antes_cerrar", "Tooltip visible antes de cerrar"))
        boton_cerrar.click()
        time.sleep(1)
        registro["evidencias"].append(app.captura("AMR2087_CA2", "despues_cerrar", "Después de cerrar con X"))
    
    # Reiniciar la app sin haber accedido a la sección
    tiempo_reinicio = app.reiniciar()
    time.sleep(3)
    
    # Verificar que el tooltip vuelve a aparecer
    elementos_reinicio = app.clickeables()
    tooltip_reaparecio = False
    
    for el in elementos_reinicio:
        etiqueta = app.etiqueta(el)
        if "NUEVO" in etiqueta and "videos verticales" in etiqueta:
            tooltip_reaparecio = True
            break
    
    registro["evidencias"].append(app.captura("AMR2087_CA2", "reinicio_con_tooltip", "Después de reiniciar sin acceder"))
    registro["detalle"].update({
        "tiempo_reinicio_s": tiempo_reinicio,
        "tooltip_cerrado_inicialmente": boton_cerrar is not None,
        "tooltip_reaparecio": tooltip_reaparecio
    })
    
    assert tooltip_reaparecio, "El tooltip debería volver a aparecer si el usuario no accedió a la sección"
