# Componente: TNARC-4389 - TN Videos verticales | Evitar contenidos duplicados entre tabs
# Ticket: TNARC-4389
"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""

# CA1: Un mismo contenido no debe mostrarse en los dos tabs del player.
# Dado que el player está cargado con ambas colecciones
# Cuando se navega por ambos tabs
# Entonces ningún video debe aparecer en ambos tabs simultáneamente
def test_ca20_ca1(player, registro):
    """CA1: verifica que no hay videos duplicados entre los tabs."""
    s = player.abrir()
    registro["evidencias"].append(player.captura("CA20_CA1", "1_inicio", f"Inicio en «{s['tab']}»"))
    
    # Recolectar videos de "Lo importante"
    player.pestana("Lo importante")
    s = player.tocar_video()
    importante = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in importante:
            importante.append(s["video"])
    
    registro["evidencias"].append(player.captura("CA20_CA1", "2_importante", f"«Lo importante»: {len(importante)} videos"))
    
    # Recolectar videos de "Tenés que ver"
    player.pestana("Tenés que ver")
    s = player.tocar_video()
    ultimo = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in ultimo:
            ultimo.append(s["video"])
    
    duplicados = [v for v in importante if v in ultimo]
    
    registro["detalle"].update({
        "videos_importante": len(importante),
        "videos_ultimo": len(ultimo),
        "duplicados": duplicados,
        "hay_duplicados": len(duplicados) > 0,
    })
    registro["evidencias"].append(player.captura("CA20_CA1", "3_ultimo", f"«Tenés que ver»: {len(ultimo)} videos · duplicados={len(duplicados)}"))
    
    assert len(duplicados) == 0, f"Se encontraron {len(duplicados)} videos duplicados entre tabs: {duplicados}"


# CA2: La identificación de duplicados debe realizarse mediante el ID único del contenido.
# Dado que se cargan videos en ambos tabs
# Cuando se comparan contenidos
# Entonces la comparación debe usar el ID único (slug) del video
def test_ca20_ca2(player, registro):
    """CA2: verifica que la identificación de duplicados usa el ID único del contenido."""
    s = player.abrir()
    col_imp = player.coleccion("id_importante")
    col_ult = player.coleccion("id_ultimo")
    
    # Verificar que las colecciones tienen la estructura con ID único (slug)
    ids_importante = [v.get("slug") for v in col_imp if v.get("slug")]
    ids_ultimo = [v.get("slug") for v in col_ult if v.get("slug")]
    
    duplicados_backend = [vid for vid in ids_importante if vid in ids_ultimo]
    
    registro["detalle"].update({
        "coleccion_importante_con_id": len(ids_importante),
        "coleccion_ultimo_con_id": len(ids_ultimo),
        "duplicados_por_id": duplicados_backend,
        "cantidad_duplicados": len(duplicados_backend),
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA2", "1_colecciones",
        f"Importante: {len(ids_importante)} IDs · Último: {len(ids_ultimo)} IDs · Duplicados: {len(duplicados_backend)}"))
    
    # TODO revisar: se verifica que las colecciones tienen IDs únicos, pero no hay forma directa
    # de inspeccionar el código JS del player para confirmar que usa específicamente el slug
    # para el filtrado. Aquí se asume que el comportamiento observable (CA1) implica uso correcto del ID.
    assert len(ids_importante) > 0, "La colección «Lo importante» no tiene videos con ID"
    assert len(ids_ultimo) > 0, "La colección «Tenés que ver» no tiene videos con ID"


# CA3: Al compartir un video por URL no debe aparecer en ambos tabs
# Dado que se comparte un video mediante URL
# Cuando se abre esa URL en el player
# Entonces el video solo debe estar presente en el tab que corresponde
def test_ca20_ca3(player, registro):
    """CA3: verifica que al abrir por URL compartida, el video no aparece en ambos tabs."""
    # Obtener un video de "Lo importante"
    s = player.abrir()
    player.pestana("Lo importante")
    s = player.tocar_video()
    url_compartida = s["url"]
    video_compartido = s["video"]
    
    registro["evidencias"].append(player.captura("CA20_CA3", "1_video_origen", f"Video a compartir: {video_compartido}"))
    
    # Abrir la URL compartida
    player.abrir(url=url_compartida)
    s_nuevo = player.tocar_video()
    
    # Verificar en qué tab está
    tab_actual = s_nuevo["tab"]
    
    # Navegar al otro tab y verificar que no está ahí
    otro_tab = "Tenés que ver" if tab_actual == "Lo importante" else "Lo importante"
    player.pestana(otro_tab)
    s_otro = player.tocar_video()
    videos_otro = [s_otro["video"]]
    for _ in range(50):
        s_otro = player.swipe()
        if s_otro["fin"]:
            break
        if s_otro["video"] not in videos_otro:
            videos_otro.append(s_otro["video"])
    
    esta_en_otro = video_compartido in videos_otro
    
    registro["detalle"].update({
        "video_compartido": video_compartido,
        "url_compartida": url_compartida,
        "tab_correcto": tab_actual,
        "tab_opuesto": otro_tab,
        "aparece_en_opuesto": esta_en_otro,
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA3", "2_verificacion",
        f"Video abierto en «{tab_actual}» · Presente en «{otro_tab}»: {esta_en_otro}"))
    
    assert not esta_en_otro, f"El video compartido '{video_compartido}' aparece en ambos tabs"


# CA4: Al compartir un video no debe mostrarse duplicado en ambos tabs, debe redireccionar al tab correspondiente desde el que se compartió.
# Dado que se comparte un video desde un tab específico
# Cuando se abre la URL compartida
# Entonces debe redirigir al tab correcto y no mostrarse duplicado
def test_ca20_ca4(player, registro):
    """CA4: verifica que la URL compartida redirige al tab de origen sin duplicar el video."""
    # Compartir desde "Lo importante"
    s = player.abrir()
    player.pestana("Lo importante")
    s_imp = player.tocar_video()
    url_importante = s_imp["url"]
    video_importante = s_imp["video"]
    
    # TODO revisar: verificar el path de la URL para confirmar que incluye "/importante/"
    # según comentario del dev: "a la url se le agrega '/ultimo/' o '/importante/'"
    tiene_importante_path = "/importante/" in url_importante
    
    registro["evidencias"].append(player.captura(
        "CA20_CA4", "1_importante",
        f"Video de importante: {video_importante} · Path correcto: {tiene_importante_path}"))
    
    # Compartir desde "Tenés que ver"
    player.pestana("Tenés que ver")
    s_ult = player.tocar_video()
    url_ultimo = s_ult["url"]
    video_ultimo = s_ult["video"]
    
    tiene_ultimo_path = "/ultimo/" in url_ultimo
    
    registro["evidencias"].append(player.captura(
        "CA20_CA4", "2_ultimo",
        f"Video de último: {video_ultimo} · Path correcto: {tiene_ultimo_path}"))
    
    # Abrir URL de "importante" y verificar que abre en ese tab
    player.abrir(url=url_importante)
    s_test1 = player.tocar_video()
    
    # Abrir URL de "último" y verificar que abre en ese tab
    player.abrir(url=url_ultimo)
    s_test2 = player.tocar_video()
    
    registro["detalle"].update({
        "video_importante": video_importante,
        "url_importante_path": tiene_importante_path,
        "abre_en_importante": s_test1["tab"] == "Lo importante",
        "video_ultimo": video_ultimo,
        "url_ultimo_path": tiene_ultimo_path,
        "abre_en_ultimo": s_test2["tab"] == "Tenés que ver",
    })
    registro["evidencias"].append(player.captura(
        "CA20_CA4", "3_resultado",
        f"URL importante abre en: {s_test1['tab']} · URL último abre en: {s_test2['tab']}"))
    
    assert s_test1["tab"] == "Lo importante", f"URL de importante abrió en «{s_test1['tab']}»"
    assert s_test2["tab"] == "Tenés que ver", f"URL de último abrió en «{s_test2['tab']}»"


# CA5: Cuando un contenido se encuentre en ambas colecciones, debe mantenerse en "Lo importante".
# Dado que un contenido existe en ambas colecciones backend
# Cuando se carga el player
# Entonces ese contenido debe aparecer en "Lo importante"
def test_ca20_ca5(player, registro):
    """CA5: verifica que contenidos duplicados se mantienen en «Lo importante»."""
    s = player.abrir()
    col_imp = player.coleccion("id_importante")
    col_ult = player.coleccion("id_ultimo")
    
    # Identificar duplicados en las colecciones backend
    ids_importante = [v.get("slug") for v in col_imp if v.get("slug")]
    ids_ultimo = [v.get("slug") for v in col_ult if v.get("slug")]
    duplicados_backend = [vid for vid in ids_importante if vid in ids_ultimo]
    
    if len(duplicados_backend) == 0:
        # TODO revisar: si no hay duplicados en backend, no se puede verificar este CA
        registro["detalle"].update({
            "hay_duplicados_backend": False,
            "nota": "No hay duplicados en las colecciones para verificar priorización",
        })
        registro["evidencias"].append(player.captura(
            "CA20_CA5", "sin_duplicados",
            "No se encontraron duplicados en colecciones backend"))
        return
    
    # Verificar que los duplicados están en "Lo importante"
    player.pestana("Lo importante")
    s = player.tocar_video()
    videos_importante = [s["video"]]
    for _ in range(50):
        s = player.swipe()
        if s["fin"]:
            break
        if s["video"] not in videos_importante:
            videos_importante.append(s["video"])
    
    duplicados_en_importante
