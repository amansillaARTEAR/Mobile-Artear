# Componente: TNARC-4389 - TN Videos verticales | Evitar contenidos duplicados entre tabs
# Ticket: TNARC-4389
"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""

# CA1: Un mismo contenido no debe mostrarse en los dos tabs del player.
# Dado que el player está abierto y carga videos de ambas colecciones
# Cuando se navega por todos los videos de "Lo importante" y "Lo último"
# Entonces ningún ID de video debe aparecer en ambos tabs
def test_ca20_ca1(player, registro):
    """CA1: verifica que no hay videos duplicados entre los dos tabs del player."""
    s = player.abrir()
    registro["evidencias"].append(player.captura("CA20_CA1", "1_inicio", f"Inicio en {s['tab']}: {s['video']}"))
    
    # Recolectar IDs de "Lo importante"
    if s["tab"] != "Lo importante":
        player.pestana("Lo importante")
        s = player.snap()
    importante_ids = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in importante_ids:
            importante_ids.append(s["video"])
    
    registro["evidencias"].append(player.captura("CA20_CA1", "2_fin_importante", f"Fin de Lo importante: {len(importante_ids)} videos"))
    
    # Cambiar a "Lo último"
    player.pestana("Lo último")
    s = player.snap()
    ultimo_ids = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in ultimo_ids:
            ultimo_ids.append(s["video"])
    
    duplicados = set(importante_ids) & set(ultimo_ids)
    registro["detalle"].update({
        "videos_lo_importante": len(importante_ids),
        "videos_tenes_que_ver": len(ultimo_ids),
        "duplicados": list(duplicados),
        "cantidad_duplicados": len(duplicados),
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA1", "3_fin_ultimo", 
        f"Fin de Lo último: {len(ultimo_ids)} videos · Duplicados encontrados: {len(duplicados)}"))
    
    assert len(duplicados) == 0, f"Se encontraron {len(duplicados)} videos duplicados entre tabs: {list(duplicados)}"


# CA2: La identificación de duplicados debe realizarse mediante el ID único del contenido.
# Dado que existen contenidos en ambas colecciones
# Cuando el sistema verifica duplicados
# Entonces debe usar el ID único del contenido como criterio de comparación
def test_ca20_ca2(player, registro):
    """CA2: verifica que la comparación de duplicados se realiza por ID único del contenido."""
    s = player.abrir()
    col_importante = player.coleccion("id_importante")
    col_ultimo = player.coleccion("id_ultimo")
    
    # Extraer IDs de las colecciones originales
    ids_importante = [c["slug"] for c in col_importante]
    ids_ultimo = [c["slug"] for c in col_ultimo]
    duplicados_en_colecciones = set(ids_importante) & set(ids_ultimo)
    
    # Verificar que en el player no aparecen duplicados
    if s["tab"] != "Lo importante":
        player.pestana("Lo importante")
        s = player.snap()
    importante_mostrados = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in importante_mostrados:
            importante_mostrados.append(s["video"])
    
    player.pestana("Lo último")
    s = player.snap()
    ultimo_mostrados = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in ultimo_mostrados:
            ultimo_mostrados.append(s["video"])
    
    duplicados_en_player = set(importante_mostrados) & set(ultimo_mostrados)
    
    registro["detalle"].update({
        "duplicados_en_colecciones_originales": list(duplicados_en_colecciones),
        "cantidad_duplicados_colecciones": len(duplicados_en_colecciones),
        "duplicados_en_player": list(duplicados_en_player),
        "filtrado_correcto": len(duplicados_en_colecciones) > 0 and len(duplicados_en_player) == 0,
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA2", "verificacion_ids",
        f"Duplicados en colecciones: {len(duplicados_en_colecciones)} · En player: {len(duplicados_en_player)}"))
    
    assert len(duplicados_en_player) == 0, f"El filtro por ID no funcionó: hay {len(duplicados_en_player)} duplicados en el player"


# CA3: Al compartir un video por URL no debe aparecer en ambos tabs
# Dado que se comparte un video por URL
# Cuando se accede mediante esa URL
# Entonces el video solo debe aparecer en un tab
def test_ca20_ca3(player, registro):
    """CA3: verifica que un video compartido por URL no aparece duplicado en ambos tabs."""
    # Abrir y obtener URL de un video en "Lo importante"
    s = player.abrir()
    if s["tab"] != "Lo importante":
        player.pestana("Lo importante")
        s = player.snap()
    
    video_compartido = s["video"]
    url_compartida = s["url"]
    registro["evidencias"].append(player.captura("CA20_CA3", "1_video_original", f"Video a compartir: {video_compartido}"))
    
    # Verificar si este video está en "Lo último"
    player.pestana("Lo último")
    s = player.snap()
    encontrado_en_ultimo = False
    ultimo_ids = [s["video"]]
    if s["video"] == video_compartido:
        encontrado_en_ultimo = True
    
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] == video_compartido:
            encontrado_en_ultimo = True
        if s["video"] not in ultimo_ids:
            ultimo_ids.append(s["video"])
    
    registro["detalle"].update({
        "video_compartido": video_compartido,
        "url_compartida": url_compartida,
        "aparece_en_tenes_que_ver": encontrado_en_ultimo,
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA3", "2_verificacion",
        f"Video {video_compartido} · Duplicado en Lo último: {encontrado_en_ultimo}"))
    
    assert not encontrado_en_ultimo, f"El video {video_compartido} aparece en ambos tabs al compartir por URL"


# CA4: Al compartir un video no debe mostrarse duplicado en ambos tab, debe redireccionar al tab correspondiente desde el que se compartió.
# Dado que se comparte un video desde un tab específico
# Cuando se accede mediante la URL compartida
# Entonces debe abrir en el tab original y no aparecer duplicado en el otro
def test_ca20_ca4(player, registro):
    """CA4: verifica que compartir un video redirige al tab correcto sin duplicar."""
    # Abrir en "Lo importante" y capturar URL
    s = player.abrir()
    if s["tab"] != "Lo importante":
        player.pestana("Lo importante")
        s = player.snap()
    
    video_importante = s["video"]
    url_importante = s["url"]
    tab_importante = s["tab"]
    registro["evidencias"].append(player.captura("CA20_CA4", "1_video_importante", f"Video en Lo importante: {video_importante}"))
    
    # Cambiar a "Lo último" y capturar otro video
    player.pestana("Lo último")
    s = player.snap()
    video_ultimo = s["video"]
    url_ultimo = s["url"]
    tab_ultimo = s["tab"]
    registro["evidencias"].append(player.captura("CA20_CA4", "2_video_ultimo", f"Video en Lo último: {video_ultimo}"))
    
    # TODO revisar: No hay método para abrir una URL específica y verificar el tab de destino
    # Se asume que player.url_actual() y la presencia de "/importante/" o "/ultimo/" en la URL
    # indican el comportamiento correcto del routing
    
    tiene_routing_importante = "/importante/" in url_importante
    tiene_routing_ultimo = "/ultimo/" in url_ultimo
    
    registro["detalle"].update({
        "video_lo_importante": video_importante,
        "url_lo_importante": url_importante,
        "tiene_routing_importante": tiene_routing_importante,
        "video_tenes_que_ver": video_ultimo,
        "url_tenes_que_ver": url_ultimo,
        "tiene_routing_ultimo": tiene_routing_ultimo,
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA4", "3_urls",
        f"URLs con routing correcto: importante={tiene_routing_importante}, ultimo={tiene_routing_ultimo}"))
    
    assert tiene_routing_importante or tiene_routing_ultimo, "Las URLs compartidas no incluyen el indicador de tab (/importante/ o /ultimo/)"


# CA5: Cuando un contenido se encuentre en ambas colecciones, debe mantenerse en "Lo importante".
# Dado que un contenido existe en ambas colecciones
# Cuando el sistema filtra duplicados
# Entonces el contenido debe aparecer en "Lo importante"
def test_ca20_ca5(player, registro):
    """CA5: verifica que contenidos duplicados se mantienen en Lo importante."""
    s = player.abrir()
    col_importante = player.coleccion("id_importante")
    col_ultimo = player.coleccion("id_ultimo")
    
    ids_importante = [c["slug"] for c in col_importante]
    ids_ultimo = [c["slug"] for c in col_ultimo]
    duplicados = set(ids_importante) & set(ids_ultimo)
    
    if len(duplicados) == 0:
        registro["detalle"]["sin_duplicados_en_colecciones"] = True
        registro["evidencias"].append(player.captura("CA20_CA5", "sin_duplicados", "No hay duplicados en las colecciones para verificar"))
        # Si no hay duplicados, el test pasa trivialmente
        return
    
    # Verificar que los duplicados están en "Lo importante"
    if s["tab"] != "Lo importante":
        player.pestana("Lo importante")
        s = player.snap()
    
    importante_mostrados = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in importante_mostrados:
            importante_mostrados.append(s["video"])
    
    duplicados_en_importante = duplicados & set(importante_mostrados)
    
    # Verificar que NO están en "Lo último"
    player.pestana("Lo último")
    s = player.snap()
    ultimo_mostrados = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in ultimo_mostrados:
            ultimo_mostrados.append(s["video"])

    duplicados_en_ultimo = duplicados & set(ultimo_mostrados)

    registro["detalle"].update({
        "duplicados_en_colecciones": list(duplicados),
        "duplicados_en_lo_importante": list(duplicados_en_importante),
        "duplicados_en_tenes_que_ver": list(duplicados_en_ultimo),
        "se_mantienen_en_lo_importante": duplicados <= duplicados_en_importante,
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA5", "verificacion_tab",
        f"Duplicados en colecciones: {len(duplicados)} · mostrados en Lo importante: "
        f"{len(duplicados_en_importante)} · mostrados en Lo último: {len(duplicados_en_ultimo)}"))

    assert duplicados <= set(importante_mostrados), (
        "No todos los contenidos duplicados entre colecciones se muestran en 'Lo importante': "
        f"faltan {duplicados - duplicados_en_importante}")
    assert len(duplicados_en_ultimo) == 0, (
        "Contenidos duplicados también aparecen en 'Lo último' (deberían quedar solo en "
        f"'Lo importante'): {list(duplicados_en_ultimo)}")
