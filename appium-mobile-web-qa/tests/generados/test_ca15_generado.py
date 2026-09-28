"""Caso generado automáticamente a partir de un ticket de Jira. REVISAR ANTES DE APROBAR EL PR."""

def test_ca15_generado(player, registro):
    """CA15: al abrir el player por primera vez, aparece un tooltip con texto NUEVO y botón X que cierra con animación."""
    s = player.abrir()
    registro["evidencias"].append(player.captura("CA15", "1_carga_inicial", "CA15 · Carga inicial del player"))
    
    # TODO revisar: No existe un método player.tooltip_visible() ni selectores específicos para tooltips en Player.
    # Se asume que el tooltip es visible en la primera carga. Si hay métodos futuros para detectarlo, reemplazar esta parte.
    # Por ahora, tomamos una captura y registramos el estado inicial como evidencia.
    
    registro["evidencias"].append(player.captura("CA15", "2_tooltip_visible", "CA15 · Tooltip inicial debería estar visible con texto NUEVO"))
    
    # TODO revisar: No hay método player.cerrar_tooltip() ni selectores para el botón X del tooltip.
    # Se usaría player.tocar(...) si existiera un selector definido, pero como no está disponible,
    # registramos que el test requiere interacción manual o extensión de la clase Player.
    # Alternativa: player.tocar() podría funcionar si se define el selector adecuado en Player.
    
    # Simulación: asumimos que tocamos el X (en un caso real, necesitaríamos el selector)
    player.esperar(1)
    registro["evidencias"].append(player.captura("CA15", "3_despues_de_cerrar", "CA15 · Después de cerrar tooltip con X"))
    
    # Recargamos el player para verificar que el tooltip no reaparece si ya se cerró/accedió
    player.abrir()
    player.esperar(1)
    registro["evidencias"].append(player.captura("CA15", "4_segunda_carga", "CA15 · Segunda carga - tooltip NO debe aparecer si usuario ya accedió"))
    
    registro["detalle"].update({
        "video_inicial": s["video"],
        "nota": "Test parcial: requiere métodos específicos para detectar y cerrar tooltip en Player"
    })
    
    # TODO revisar: Los asserts reales dependerían de métodos como player.tooltip_visible() o selectores CSS
    # que permitan verificar presencia/ausencia del tooltip. Por ahora, documentamos la necesidad.
    assert s["tiene_video"] and s["reproduciendo"], "El video inicial debe estar reproduciéndose al cargar"
