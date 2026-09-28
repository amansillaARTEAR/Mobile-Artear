# Componente: Sin clasificar
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

# Escenario: Positivo
# Dado que el usuario ingresa por primera vez a la app
# Cuando se carga el player con la navbar visible
# Entonces debe aparecer un tooltip con el texto "NUEVO - Informate con nuestros videos verticales" y debe poder cerrarse tocando la X
def test_ca17_positivo(player, registro):
    """POSITIVO: el tooltip de la nueva sección se muestra al iniciar por primera vez y se cierra al tocar la X."""
    s = player.abrir()
    player.esperar(1)  # Dar tiempo a la animación del tooltip
    registro["evidencias"].append(player.captura("CA17", "1_tooltip_inicial", "Tooltip visible al cargar el player"))
    
    controles = player.controles_visibles()
    iconos = player.iconos_visibles()
    
    # Verificar presencia del tooltip por el texto esperado
    tiene_tooltip = any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles)
    tiene_cierre = iconos.get("tiene_cierre", False) or any("cerrar" in str(c).lower() or "×" in str(c) or "x" in str(c).lower() for c in controles)
    
    registro["detalle"].update({
        "tooltip_mostrado": tiene_tooltip,
        "tiene_boton_cierre": tiene_cierre,
        "controles_visibles": controles,
        "iconos": iconos,
    })
    
    assert tiene_tooltip, f"No se encontró el tooltip con el texto esperado. Controles visibles: {controles}"
    assert tiene_cierre, f"No se encontró el botón de cierre (X) del tooltip. Controles: {controles}, Iconos: {iconos}"
    
    # TODO revisar: se asume que el botón de cierre está disponible en controles_visibles() o iconos_visibles()
    # pero puede requerir un selector específico si está implementado como overlay independiente
    
    # Intentar cerrar el tooltip tocando en la zona superior donde debería estar la X
    player.tocar("navbar")  # Aproximación: tocar en el área del navbar/topbar
    player.esperar(1)  # Esperar el efecto de cierre
    
    controles_despues = player.controles_visibles()
    tooltip_cerrado = not any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_despues)
    
    registro["detalle"]["tooltip_cerrado"] = tooltip_cerrado
    registro["evidencias"].append(player.captura("CA17", "2_tooltip_cerrado", "Tooltip cerrado después de tocar X"))
    
    assert tooltip_cerrado, f"El tooltip no se cerró correctamente. Controles después: {controles_despues}"


# Escenario: Negativo
# Dado que el usuario ya accedió a la sección de videos verticales en una sesión anterior
# Cuando vuelve a ingresar a la app
# Entonces el tooltip NO debe mostrarse
def test_ca17_negativo(player, registro):
    """NEGATIVO: el tooltip no aparece si el usuario ya accedió a la sección en visitas anteriores."""
    # Primera visita: abrir y simular acceso a la sección
    s = player.abrir()
    player.esperar(1)
    
    controles_primera = player.controles_visibles()
    tiene_tooltip_primera = any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_primera)
    
    registro["evidencias"].append(player.captura("CA17_neg", "1_primera_visita", "Primera visita con tooltip"))
    
    # Simular navegación a la pestaña (si hay pestañas disponibles)
    # TODO revisar: se asume que tocar en el navbar o cambiar de pestaña cuenta como "acceder a la sección"
    player.tocar("navbar")
    player.esperar(1)
    
    # Cambiar de pestaña para simular que accedió a la sección
    tabs = ["Lo importante", "Lo último"]
    for tab in tabs:
        try:
            player.pestana(tab)
            player.esperar(1)
            break
        except:
            continue
    
    registro["evidencias"].append(player.captura("CA17_neg", "2_acceso_seccion", "Usuario accedió a la sección"))
    
    # Simular cierre y reapertura (en una prueba real esto requeriría reiniciar el navegador/app)
    # Como aproximación, volvemos a cargar el player
    # TODO revisar: esta aproximación puede no reflejar el comportamiento real de persistencia entre sesiones
    # que requeriría cookies/localStorage o reinicio completo de la app
    s = player.abrir()
    player.esperar(1)
    
    controles_segunda = player.controles_visibles()
    tiene_tooltip_segunda = any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_segunda)
    
    registro["detalle"].update({
        "tooltip_primera_visita": tiene_tooltip_primera,
        "tooltip_segunda_visita": tiene_tooltip_segunda,
        "controles_segunda": controles_segunda,
    })
    
    registro["evidencias"].append(player.captura("CA17_neg", "3_segunda_visita", "Segunda visita - tooltip no debe aparecer"))
    
    # TODO revisar: la verificación depende de que el player mantenga estado entre llamadas a abrir()
    # o que haya un mecanismo de persistencia que esta prueba pueda activar
    assert not tiene_tooltip_segunda, f"El tooltip apareció nuevamente después de acceder a la sección. Controles: {controles_segunda}"


# Escenario: Borde
# Dado que el usuario cerró el tooltip sin acceder a la sección
# Cuando vuelve a ingresar a la app
# Entonces el tooltip debe volver a mostrarse
def test_ca17_borde(player, registro):
    """BORDE: el tooltip reaparece si el usuario lo cerró sin acceder a la sección de videos."""
    s = player.abrir()
    player.esperar(1)
    
    controles_inicial = player.controles_visibles()
    tiene_tooltip_inicial = any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_inicial)
    
    registro["evidencias"].append(player.captura("CA17_borde", "1_tooltip_inicial", "Tooltip visible en primera carga"))
    
    assert tiene_tooltip_inicial, f"El tooltip no apareció en la carga inicial. Controles: {controles_inicial}"
    
    # Cerrar el tooltip sin acceder a la sección (solo tocar X)
    player.tocar("navbar")
    player.esperar(1)
    
    controles_cerrado = player.controles_visibles()
    tooltip_cerrado = not any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_cerrado)
    
    registro["evidencias"].append(player.captura("CA17_borde", "2_tooltip_cerrado_sin_acceso", "Tooltip cerrado sin acceder a sección"))
    
    assert tooltip_cerrado, "El tooltip no se cerró correctamente"
    
    # Simular nueva visita sin haber accedido a la sección
    # TODO revisar: similar al test negativo, esto requiere persistencia real entre sesiones
    # En ausencia de un método para resetear/recargar respetando el estado de "no accedió",
    # esta aproximación puede no ser suficiente
    s = player.abrir()
    player.esperar(1)
    
    controles_reaparicion = player.controles_visibles()
    tiene_tooltip_reaparicion = any("NUEVO" in str(c) and "videos verticales" in str(c) for c in controles_reaparicion)
    
    registro["detalle"].update({
        "tooltip_inicial": tiene_tooltip_inicial,
        "tooltip_cerrado": tooltip_cerrado,
        "tooltip_reaparecio": tiene_tooltip_reaparicion,
        "controles_reaparicion": controles_reaparicion,
    })
    
    registro["evidencias"].append(player.captura("CA17_borde", "3_tooltip_reaparecio", "Tooltip debe reaparecer tras nueva visita"))
    
    assert tiene_tooltip_reaparicion, f"El tooltip no reapareció después de cerrarlo sin acceder a la sección. Controles: {controles_reaparicion}"
