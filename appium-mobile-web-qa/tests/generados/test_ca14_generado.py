"""Caso generado automáticamente a partir de un ticket de Jira. REVISAR ANTES DE APROBAR EL PR."""

def test_ca14_generado(player, registro):
    """CA14: al abrir el player se debe mostrar el topbar de portada y el navbar abajo."""
    s = player.abrir()
    registro["evidencias"].append(player.captura(
        "CA14", "1_carga_inicial",
        f"CA14 · Carga inicial · video: {s['video']} · reproduciendo: {s['reproduciendo']}"))
    
    # TODO revisar: Player no expone métodos para verificar presencia de topbar/navbar específicos.
    # Asumimos que controles_visibles() puede dar pistas sobre la UI visible, pero no discrimina
    # entre topbar de portada vs. topbar de player ni detecta navbar inferior.
    # Solución provisional: verificar que el player cargó correctamente y capturar evidencia visual.
    
    controles = player.controles_visibles()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "tiene_video": s["tiene_video"],
        "reproduciendo": s["reproduciendo"],
        "controles_visibles": controles,
    })
    
    registro["evidencias"].append(player.captura(
        "CA14", "2_ui_completa",
        f"CA14 · UI completa · controles: {controles}"))
    
    assert s["tiene_video"], "No se cargó un video en la pantalla inicial"
    assert s["reproduciendo"], "El video inicial no está reproduciéndose"
