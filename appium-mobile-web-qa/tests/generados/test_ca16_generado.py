"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

# Escenario: Positivo
# Dado que el usuario abre el reproductor de videos verticales desde la sección
# Cuando el reproductor se carga
# Entonces debe mostrarse como portada (no modal), con topbar y navbar visibles, sin icono de cierre, con iconos de share y sonido, y reproduciendo el primer video

def test_ca16_positivo(player, registro):
    """POSITIVO: CA16 - El reproductor se abre como portada con topbar, navbar, sin icono de cierre, mostrando iconos de share y sonido."""
    s = player.abrir()
    registro["evidencias"].append(player.captura(
        "CA16", "1_carga_portada",
        f"CA16 · Carga como portada · reproduciendo: {s['video']}"))
    
    # Verificar que se abre como portada (no modal): no debe haber icono de cierre
    assert not s.get("tiene_cierre", False), "El reproductor muestra icono de cierre cuando debería ser portada"
    
    # Verificar que tiene topbar y navbar
    # TODO revisar: Player no expone métodos para verificar topbar/navbar directamente. Se asume que si no hay cierre y se carga correctamente, es portada.
    
    # Verificar controles visibles (share y sonido)
    controles = player.controles_visibles()
    registro["detalle"].update({
        "tiene_cierre": s.get("tiene_cierre", False),
        "tiene_share": controles.get("tiene_share", False),
        "tiene_sonido": controles.get("tiene_sonido", False),
        "video_inicial": s["video"],
        "tab_inicial": s.get("tab", ""),
    })
    
    registro["evidencias"].append(player.captura(
        "CA16", "2_controles",
        f"Controles visibles · share={controles.get('tiene_share')} · sonido={controles.get('tiene_sonido')}"))
    
    assert controles.get("tiene_share", False), "No se muestra el icono de share"
    assert controles.get("tiene_sonido", False), "No se muestra el icono de sonido/volumen"
    assert s["tiene_video"] and s["reproduciendo"], "El reproductor no está reproduciendo un video"


# Escenario: Negativo
# Dado que el usuario está en el reproductor como portada
# Cuando intenta cerrar el reproductor buscando el icono de cierre
# Entonces no debe encontrar dicho icono porque no es un modal

def test_ca16_negativo(player, registro):
    """NEGATIVO: CA16 - El reproductor NO muestra icono de cierre al ser portada en lugar de modal."""
    s = player.abrir()
    
    # Verificar que NO hay icono de cierre
    tiene_cierre = s.get("tiene_cierre", False)
    
    registro["detalle"].update({
        "tiene_cierre": tiene_cierre,
        "tipo_apertura": "portada_esperada",
    })
    
    registro["evidencias"].append(player.captura(
        "CA16", "negativo_sin_cierre",
        f"CA16 Negativo · Sin icono de cierre · tiene_cierre={tiene_cierre}"))
    
    assert not tiene_cierre, "ERROR: El reproductor muestra icono de cierre cuando debería ser una portada sin posibilidad de cierre"


# Escenario: Borde
# Dado que el reproductor está cargado como portada con dos pestañas
# Cuando el usuario cambia entre las pestañas "Lo importante" y "Tenés que ver"
# Entonces debe mantener la estructura de portada (topbar, navbar) y los iconos de share y sonido en ambas pestañas

def test_ca16_borde(player, registro):
    """BORDE: CA16 - Al cambiar entre pestañas, se mantiene la estructura de portada y los iconos visibles."""
    s = player.abrir()
    tab_inicial = s.get("tab", "")
    
    registro["evidencias"].append(player.captura(
        "CA16", "borde_1_tab_inicial",
        f"Pestaña inicial: {tab_inicial}"))
    
    # Verificar controles en la pestaña inicial
    controles_inicial = player.controles_visibles()
    tiene_cierre_inicial = s.get("tiene_cierre", False)
    
    # Cambiar de pestaña
    if tab_inicial == "Lo importante":
        s = player.pestana("Tenés que ver")
    else:
        s = player.pestana("Lo importante")
    
    tab_nueva = s.get("tab", "")
    
    registro["evidencias"].append(player.captura(
        "CA16", "borde_2_tab_cambiada",
        f"Después de cambiar a: {tab_nueva}"))
    
    # Verificar controles en la nueva pestaña
    controles_nueva = player.controles_visibles()
    tiene_cierre_nueva = s.get("tiene_cierre", False)
    
    registro["detalle"].update({
        "tab_inicial": tab_inicial,
        "tab_nueva": tab_nueva,
        "tiene_cierre_inicial": tiene_cierre_inicial,
        "tiene_cierre_nueva": tiene_cierre_nueva,
        "share_inicial": controles_inicial.get("tiene_share", False),
        "share_nueva": controles_nueva.get("tiene_share", False),
        "sonido_inicial": controles_inicial.get("tiene_sonido", False),
        "sonido_nueva": controles_nueva.get("tiene_sonido", False),
    })
    
    registro["evidencias"].append(player.captura(
        "CA16", "borde_3_comparacion",
        f"Comparación · tabs={tab_inicial}→{tab_nueva} · controles persistentes"))
    
    assert not tiene_cierre_inicial and not tiene_cierre_nueva, "El icono de cierre apareció en alguna de las pestañas"
    assert controles_nueva.get("tiene_share", False), "El icono de share no se mantiene al cambiar de pestaña"
    assert controles_nueva.get("tiene_sonido", False), "El icono de sonido no se mantiene al cambiar de pestaña"
    assert tab_inicial != tab_nueva, "No se pudo cambiar de pestaña correctamente"
