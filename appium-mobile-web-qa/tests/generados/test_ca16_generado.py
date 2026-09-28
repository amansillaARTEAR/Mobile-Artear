# Componente: Videos Verticales
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR.

Corregido a mano tras la revisión del PR: la versión generada por Claude usaba
s.get("tiene_cierre", ...) -- que no existe en lo que devuelve player.abrir(), por lo
que el assert siempre pasaba sin verificar nada -- y controles.get("tiene_share", ...)
sobre una lista (player.controles_visibles() no es un diccionario), lo que tiraba
AttributeError. Se reemplazó por player.iconos_visibles(), agregado a Player
específicamente para poder verificar estos íconos puntuales."""

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

    # TODO revisar: Player no expone métodos para verificar topbar/navbar específicos.
    # Se usa iconos_visibles() (compartir/sonido/cierre) como mejor aproximación disponible.
    iconos = player.iconos_visibles()
    registro["detalle"].update({
        "tiene_cierre": iconos["tiene_cierre"],
        "tiene_share": iconos["tiene_share"],
        "tiene_sonido": iconos["tiene_sonido"],
        "video_inicial": s["video"],
        "tab_inicial": s.get("tab", ""),
    })

    registro["evidencias"].append(player.captura(
        "CA16", "2_controles",
        f"Íconos · share={iconos['tiene_share']} · sonido={iconos['tiene_sonido']} · cierre={iconos['tiene_cierre']}"))

    assert not iconos["tiene_cierre"], "El reproductor muestra ícono de cierre cuando debería ser portada (no modal)"
    assert iconos["tiene_share"], "No se muestra el ícono de compartir"
    assert iconos["tiene_sonido"], "No se muestra el ícono de sonido/volumen"
    assert s["tiene_video"] and s["reproduciendo"], "El reproductor no está reproduciendo un video"


# Escenario: Negativo
# Dado que el usuario está en el reproductor como portada
# Cuando intenta cerrar el reproductor buscando el icono de cierre
# Entonces no debe encontrar dicho icono porque no es un modal

def test_ca16_negativo(player, registro):
    """NEGATIVO: CA16 - El reproductor NO muestra icono de cierre al ser portada en lugar de modal."""
    player.abrir()

    iconos = player.iconos_visibles()

    registro["detalle"].update({
        "tiene_cierre": iconos["tiene_cierre"],
        "tipo_apertura": "portada_esperada",
    })

    registro["evidencias"].append(player.captura(
        "CA16", "negativo_sin_cierre",
        f"CA16 Negativo · Sin ícono de cierre · tiene_cierre={iconos['tiene_cierre']}"))

    assert not iconos["tiene_cierre"], "ERROR: El reproductor muestra ícono de cierre cuando debería ser una portada sin posibilidad de cierre"


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

    iconos_inicial = player.iconos_visibles()

    # Cambiar de pestaña
    if tab_inicial == "Lo importante":
        s = player.pestana("Tenés que ver")
    else:
        s = player.pestana("Lo importante")

    tab_nueva = s.get("tab", "")

    registro["evidencias"].append(player.captura(
        "CA16", "borde_2_tab_cambiada",
        f"Después de cambiar a: {tab_nueva}"))

    iconos_nueva = player.iconos_visibles()

    registro["detalle"].update({
        "tab_inicial": tab_inicial,
        "tab_nueva": tab_nueva,
        "tiene_cierre_inicial": iconos_inicial["tiene_cierre"],
        "tiene_cierre_nueva": iconos_nueva["tiene_cierre"],
        "share_inicial": iconos_inicial["tiene_share"],
        "share_nueva": iconos_nueva["tiene_share"],
        "sonido_inicial": iconos_inicial["tiene_sonido"],
        "sonido_nueva": iconos_nueva["tiene_sonido"],
    })

    registro["evidencias"].append(player.captura(
        "CA16", "borde_3_comparacion",
        f"Comparación · tabs={tab_inicial}→{tab_nueva} · controles persistentes"))

    assert not iconos_inicial["tiene_cierre"] and not iconos_nueva["tiene_cierre"], "El ícono de cierre apareció en alguna de las pestañas"
    assert iconos_nueva["tiene_share"], "El ícono de compartir no se mantiene al cambiar de pestaña"
    assert iconos_nueva["tiene_sonido"], "El ícono de sonido no se mantiene al cambiar de pestaña"
    assert tab_inicial != tab_nueva, "No se pudo cambiar de pestaña correctamente"
