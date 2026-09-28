# Componente: Sin clasificar
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

# Escenario: Positivo
# Dado que estoy en el player con la pestaña "Lo importante"
# Cuando navego entre varios videos y cambio a "Lo último"
# Entonces al regresar a "Lo importante" debo ver el último video que estaba visualizando
def test_ca18_positivo(player, registro):
    """POSITIVO: cada feed conserva el último video visualizado al cambiar de pestaña."""
    s = player.abrir()
    assert s["tab"] == "Lo importante", f"La pestaña inicial es «{s['tab']}»"
    
    registro["evidencias"].append(player.captura(
        "CA18", "1_inicio_importante", f"Inicio en «Lo importante»: {s['video']}"))
    
    # Avanzar algunos videos en "Lo importante"
    videos_importante = [s["video"]]
    for _ in range(3):
        s = player.swipe()
        videos_importante.append(s["video"])
    
    ultimo_importante = s["video"]
    idx_importante = s["idx"]
    registro["evidencias"].append(player.captura(
        "CA18", "2_ultimo_importante", f"Último video en «Lo importante» antes de cambiar: {ultimo_importante} (idx={idx_importante})"))
    
    # Cambiar a "Lo último"
    s = player.pestana("Lo último")
    assert s["tab"] == "Lo último", f"No se cambió correctamente a «Lo último», tab={s['tab']}"
    video_inicial_ultimo = s["video"]
    registro["evidencias"].append(player.captura(
        "CA18", "3_inicio_ultimo", f"Primera reproducción en «Lo último»: {video_inicial_ultimo}"))
    
    # Avanzar algunos videos en "Lo último"
    videos_ultimo = [s["video"]]
    for _ in range(2):
        s = player.swipe()
        videos_ultimo.append(s["video"])
    
    ultimo_ultimo = s["video"]
    idx_ultimo = s["idx"]
    registro["evidencias"].append(player.captura(
        "CA18", "4_ultimo_ultimo", f"Último video en «Lo último» antes de volver: {ultimo_ultimo} (idx={idx_ultimo})"))
    
    # Regresar a "Lo importante"
    s = player.pestana("Lo importante")
    assert s["tab"] == "Lo importante", f"No se volvió correctamente a «Lo importante», tab={s['tab']}"
    video_retorno_importante = s["video"]
    idx_retorno_importante = s["idx"]
    registro["evidencias"].append(player.captura(
        "CA18", "5_retorno_importante", f"Video al regresar a «Lo importante»: {video_retorno_importante} (idx={idx_retorno_importante})"))
    
    # Volver a "Lo último"
    s = player.pestana("Lo último")
    video_retorno_ultimo = s["video"]
    idx_retorno_ultimo = s["idx"]
    registro["evidencias"].append(player.captura(
        "CA18", "6_retorno_ultimo", f"Video al regresar a «Lo último»: {video_retorno_ultimo} (idx={idx_retorno_ultimo})"))
    
    registro["detalle"].update({
        "ultimo_importante": ultimo_importante,
        "idx_importante": idx_importante,
        "video_retorno_importante": video_retorno_importante,
        "idx_retorno_importante": idx_retorno_importante,
        "conserva_importante": video_retorno_importante == ultimo_importante,
        "ultimo_ultimo": ultimo_ultimo,
        "idx_ultimo": idx_ultimo,
        "video_retorno_ultimo": video_retorno_ultimo,
        "idx_retorno_ultimo": idx_retorno_ultimo,
        "conserva_ultimo": video_retorno_ultimo == ultimo_ultimo,
    })
    
    assert video_retorno_importante == ultimo_importante, \
        f"«Lo importante» no conservó el último video: esperado={ultimo_importante}, actual={video_retorno_importante}"
    assert video_retorno_ultimo == ultimo_ultimo, \
        f"«Lo último» no conservó el último video: esperado={ultimo_ultimo}, actual={video_retorno_ultimo}"


# Escenario: Negativo
# Dado que estoy visualizando un video en "Lo importante"
# Cuando cambio a "Lo último" sin haber navegado previamente en esa pestaña
# Entonces "Lo último" debe iniciar desde el primer video de su colección (no desde una posición arbitraria)
def test_ca18_negativo(player, registro):
    """NEGATIVO: al cambiar a una pestaña sin historial previo, debe iniciar desde el primer video."""
    s = player.abrir()
    assert s["tab"] == "Lo importante", f"La pestaña inicial es «{s['tab']}»"
    
    # Avanzar varios videos en "Lo importante"
    for _ in range(5):
        s = player.swipe()
    
    registro["evidencias"].append(player.captura(
        "CA18", "1_avanzado_importante", f"Después de avanzar en «Lo importante»: {s['video']} (idx={s['idx']})"))
    
    # Cambiar a "Lo último" (primera vez)
    s = player.pestana("Lo último")
    idx_inicial_ultimo = s["idx"]
    video_inicial_ultimo = s["video"]
    
    col_ultimo = player.coleccion("id_ultimo")
    primer_video_col = col_ultimo[0]["slug"] if col_ultimo else None
    
    registro["detalle"].update({
        "idx_inicial_ultimo": idx_inicial_ultimo,
        "video_inicial_ultimo": video_inicial_ultimo,
        "primer_video_coleccion": primer_video_col,
        "inicia_desde_primero": idx_inicial_ultimo == 1,
    })
    
    registro["evidencias"].append(player.captura(
        "CA18", "2_primer_acceso_ultimo", f"Primera vez en «Lo último»: {video_inicial_ultimo} (idx={idx_inicial_ultimo})"))
    
    assert idx_inicial_ultimo == 1, \
        f"«Lo último» no inició desde el primer video al acceder por primera vez: idx={idx_inicial_ultimo}"
    # TODO revisar: el criterio asume que idx=1 es el primer video; verificar si la colección "Lo último" 
    # efectivamente devuelve como primer elemento el video más reciente según el ticket


# Escenario: Borde
# Dado que estoy en "Lo importante" y he navegado hasta el final del feed
# Cuando cambio a "Lo último" y luego regreso a "Lo importante"
# Entonces debo ver la pantalla de fin (último estado visualizado), no el primer video
def test_ca18_borde(player, registro):
    """BORDE: si el último estado de un feed es la pantalla de fin, debe conservarse al regresar."""
    s = player.abrir()
    assert s["tab"] == "Lo importante", f"La pestaña inicial es «{s['tab']}»"
    
    registro["evidencias"].append(player.captura(
        "CA18", "1_inicio", f"Inicio en «Lo importante»: {s['video']}"))
    
    # Navegar hasta el final de "Lo importante"
    for _ in range(100):
        s = player.swipe()
        if s["fin"]:
            break
    
    assert s["fin"], "No se llegó al final de «Lo importante»"
    ultimo_video_importante = s["video"]
    registro["evidencias"].append(player.captura(
        "CA18", "2_fin_importante", f"Fin de «Lo importante»: {ultimo_video_importante}"))
    
    # Cambiar a "Lo último"
    s = player.pestana("Lo último")
    registro["evidencias"].append(player.captura(
        "CA18", "3_cambio_ultimo", f"Cambio a «Lo último»: {s['video']}"))
    
    # Regresar a "Lo importante"
    s = player.pestana("Lo importante")
    fin_conservado = s["fin"]
    video_retorno = s["video"]
    
    registro["detalle"].update({
        "ultimo_video_importante": ultimo_video_importante,
        "video_retorno": video_retorno,
        "fin_conservado": fin_conservado,
    })
    
    registro["evidencias"].append(player.captura(
        "CA18", "4_retorno_importante", f"Retorno a «Lo importante»: video={video_retorno}, fin={fin_conservado}"))
    
    assert fin_conservado, \
        "Al regresar a «Lo importante», no se conservó el estado de fin del feed"
    assert video_retorno == ultimo_video_importante, \
        f"El video mostrado al regresar no coincide con el último visualizado: esperado={ultimo_video_importante}, actual={video_retorno}"
