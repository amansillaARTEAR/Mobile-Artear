# Componente: Videos Verticales
# Ticket: TNARC-4366
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR.

Corregido a mano tras la corrida real (falló 3/3 en Android e iOS): mismo bug ya visto en
test_ca17_generado.py -- player.esperar(N) se usaba para "esperar N segundos", pero
esperar(condicion, ...) espera una FUNCIÓN de condición y llama condicion(snap); pasarle un
int tira TypeError: 'int' object is not callable. Reemplazado por time.sleep(N) en negativo y
borde (se agrega el import). Además, en positivo, player.ir_al_final_del_video() devuelve la
DURACIÓN del video (un float), no un snap -- no tiene claves como un dict, así que s["d"]/s["t"]
tiraban TypeError: 'float' object is not subscriptable. Se reescribió para no tratarlo como
snap y esperar el avance automático con player.esperar(lambda snap: ...) en vez de un sleep fijo.

Segunda corrida (ya con los fixes de arriba): positivo y negativo pasaron, pero borde falló
por separado -- assert s["fin"] con fin=False todavía a los 3s de time.sleep tras saltar al
final del último video (o no le alcanzaba el tiempo, o hacía falta más margen). Cambiado ese
sleep fijo también por player.esperar(lambda snap: snap["fin"], timeout=15)."""

import time

# Escenario: Positivo
# Dado que el player está abierto y reproduce el primer video
# Cuando el video llega al final
# Entonces debe comenzar automáticamente la reproducción del siguiente video
def test_ca18_positivo(player, registro):
    """POSITIVO: al finalizar un video, debe comenzar automáticamente la reproducción del siguiente."""
    s = player.abrir()
    video_inicial = s["video"]
    idx_inicial = s["idx"]
    registro["evidencias"].append(player.captura(
        "CA18", "1_inicio", f"Video inicial reproduciéndose: {video_inicial}"))

    # Avanzar hasta el final del video actual. OJO: ir_al_final_del_video() devuelve la
    # duración del video (float), no un snap -- no se puede indexar como diccionario.
    duracion_inicial = player.ir_al_final_del_video()
    registro["detalle"].update({
        "video_inicial": video_inicial,
        "duracion_inicial": duracion_inicial,
    })

    # Esperar (con polling real, no un sleep fijo) a que el índice avance -- señal de que el
    # siguiente video arrancó automáticamente.
    s = player.esperar(lambda snap: snap["idx"] != idx_inicial, timeout=15)
    video_siguiente = s["video"] if s else None

    registro["detalle"].update({
        "video_siguiente": video_siguiente,
        "reproduciendo_siguiente": s["reproduciendo"] if s else None,
        "tiempo_siguiente": s["t"] if s else None,
        "idx_inicial": idx_inicial,
        "idx_siguiente": s["idx"] if s else None,
    })
    registro["evidencias"].append(player.captura(
        "CA18", "2_siguiente",
        f"Siguiente video reproduciéndose: {video_siguiente} · t={s['t'] if s else '?'}s · reproduciendo={s['reproduciendo'] if s else '?'}"))

    assert s is not None, "El siguiente video no arrancó dentro del timeout (15s) tras finalizar el anterior"
    assert video_siguiente != video_inicial, f"El video no cambió después de finalizar (sigue siendo {video_inicial})"
    assert s["reproduciendo"], "El siguiente video no se reproduce automáticamente"
    assert s["idx"] == idx_inicial + 1, f"El índice debería ser {idx_inicial + 1} pero es {s['idx']}"
    assert s["t"] >= 0 and s["t"] < 5, f"El siguiente video debería estar al inicio (t={s['t']}s)"


# Escenario: Negativo
# Dado que el player está reproduciendo un video
# Cuando el usuario hace pausa manualmente antes de que finalice
# Entonces el siguiente video NO debe comenzar automáticamente
def test_ca18_negativo(player, registro):
    """NEGATIVO: si el usuario pausa manualmente, el siguiente video NO debe comenzar automáticamente."""
    s = player.abrir()
    video_inicial = s["video"]
    registro["evidencias"].append(player.captura(
        "CA18", "1_reproduciendo", f"Video inicial: {video_inicial}"))
    
    # Pausar el video manualmente
    player.tocar_video()
    time.sleep(1)
    s = player.snap()
    
    registro["detalle"].update({
        "video_inicial": video_inicial,
        "pausado": not s["reproduciendo"],
        "tiempo_al_pausar": s["t"],
    })
    registro["evidencias"].append(player.captura(
        "CA18", "2_pausado", f"Video pausado: {video_inicial} · t={s['t']}s"))
    
    # Avanzar hasta el final del video pausado (ir_al_final_del_video() devuelve la duración
    # -- un float -- no un snap; no hace falta guardarlo, solo dejar que avance el tiempo)
    player.ir_al_final_del_video()
    time.sleep(3)
    s = player.snap()
    video_actual = s["video"]
    
    registro["detalle"].update({
        "video_tras_espera": video_actual,
        "reproduciendo_tras_espera": s["reproduciendo"],
        "idx_tras_espera": s["idx"],
    })
    registro["evidencias"].append(player.captura(
        "CA18", "3_tras_espera", 
        f"Después de esperar: {video_actual} · reproduciendo={s['reproduciendo']} · idx={s['idx']}"))
    
    assert video_actual == video_inicial, f"El video cambió a {video_actual} cuando debería mantenerse en {video_inicial}"
    assert not s["reproduciendo"], "El video está reproduciéndose cuando debería estar pausado"
    assert s["idx"] == 0, f"El índice cambió a {s['idx']} cuando debería mantenerse en 0"


# Escenario: Borde
# Dado que el player está en el último video disponible del feed
# Cuando ese video llega al final
# Entonces debe mostrar la pantalla de fin sin intentar reproducir un siguiente video
def test_ca18_borde(player, registro):
    """BORDE: al finalizar el último video disponible, debe mostrar la pantalla de fin sin reproducir otro."""
    s = player.abrir()
    registro["evidencias"].append(player.captura(
        "CA18", "1_inicio", f"Inicio: {s['video']} · total={s['total']}"))
    
    # Navegar hasta el último video del feed
    ultimo_video = None
    for i in range(s["total"]):
        if s["fin"]:
            break
        ultimo_video = s["video"]
        idx_ultimo = s["idx"]
        s = player.swipe()
    
    registro["detalle"].update({
        "total_videos": s["total"],
        "ultimo_video": ultimo_video,
        "idx_ultimo": idx_ultimo,
        "llego_al_fin": s["fin"],
    })
    
    if not s["fin"]:
        # Si no llegamos al fin con swipe, ir al final del último video
        registro["evidencias"].append(player.captura(
            "CA18", "2_ultimo_video", f"Último video: {ultimo_video} · idx={idx_ultimo}"))
        
        player.ir_al_final_del_video()
        # Esperar (con polling real, hasta 15s) a que aparezca la pantalla de fin, en vez de un
        # sleep fijo de 3s que resultó insuficiente en la corrida real (assert s["fin"] falló
        # con fin=False todavía a los 3s tras saltar al final del video).
        s = player.esperar(lambda snap: snap["fin"], timeout=15) or player.snap()

        registro["detalle"].update({
            "video_tras_finalizar": s["video"],
            "reproduciendo_tras_finalizar": s["reproduciendo"],
            "fin_tras_finalizar": s["fin"],
            "idx_tras_finalizar": s["idx"],
        })
    
    registro["evidencias"].append(player.captura(
        "CA18", "3_pantalla_fin", 
        f"Pantalla de fin · video={s['video']} · fin={s['fin']} · idx={s['idx']}"))
    
    assert s["fin"], "No se mostró la pantalla de fin después del último video"
    assert s["video"] == ultimo_video, f"El video cambió de {ultimo_video} a {s['video']} después de finalizar el último"
