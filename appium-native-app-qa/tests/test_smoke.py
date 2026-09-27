"""Smoke genérico para cualquier APK.

Valida lo básico que toda build debería cumplir antes de probar funcionalidad:
instalación, arranque, estabilidad, ciclo de vida y navegación inicial.
Los casos propios de cada ticket van en archivos aparte (ver test_ticket_plantilla.py).
"""
import time

import config


def test_01_instala_y_abre(app, registro):
    """SMK-01: el APK se instala y la app abre en primer plano."""
    en_primer_plano = app.esperar_primer_plano()
    con_contenido = app.esperar_contenido(timeout=30)
    time.sleep(3)
    app.marcar_inicio()  # recuerda la pantalla inicial para volver a ella en la exploración
    registro["detalle"].update({"paquete": app.paquete, "actividad_inicial": app.actividad_inicial,
                                "en_primer_plano": en_primer_plano, "muestra_contenido": con_contenido})
    registro["evidencias"].append(app.captura("SMK01", "apertura", "Pantalla inicial"))
    assert en_primer_plano, "La app no quedó en primer plano después de instalarse"
    assert con_contenido, "La pantalla inicial no muestra ningún elemento tocable"


def test_02_estable_al_iniciar(app, registro):
    """SMK-02: la app sigue abierta 15 segundos después de iniciar, sin crash ni ANR."""
    time.sleep(15)
    errores = app.errores_nuevos()
    vivo = app.en_primer_plano()
    registro["detalle"].update({"sigue_abierta": vivo, "crashes_o_anr": errores})
    registro["evidencias"].append(app.captura("SMK02", "estable", "15 s después de iniciar"))
    assert not errores, f"Crash o ANR: {errores}"
    assert vivo, "La app se cerró sola"


def test_03_arranque_en_frio(app, registro):
    """SMK-03: la app arranca en frío dentro del tiempo aceptable."""
    tiempos = [app.reiniciar() for _ in range(2)]
    registro["detalle"].update({"segundos_por_intento": tiempos, "maximo_aceptable": config.ARRANQUE_MAX_S})
    registro["evidencias"].append(app.captura("SMK03", "arranque", f"Arranque en frío: {tiempos} s"))
    assert not app.errores_nuevos(), "Crash o ANR durante el arranque"
    assert max(tiempos) <= config.ARRANQUE_MAX_S, f"Arranque de {max(tiempos)} s (máximo {config.ARRANQUE_MAX_S} s)"


def test_04_segundo_plano_y_regreso(app, registro):
    """SMK-04: la app vuelve bien después de pasar 5 segundos en segundo plano."""
    app.d.background_app(5)
    volvio = app.esperar_primer_plano()
    con_contenido = app.esperar_contenido()
    errores = app.errores_nuevos()
    registro["detalle"].update({"volvio_a_primer_plano": volvio, "muestra_contenido": con_contenido,
                                "crashes_o_anr": errores})
    registro["evidencias"].append(app.captura("SMK04", "regreso", "Después de volver del segundo plano"))
    assert volvio and con_contenido, "La app no se recuperó al volver del segundo plano"
    assert not errores, f"Crash o ANR: {errores}"


def test_05_rotacion(app, registro):
    """SMK-05: girar la pantalla no cierra la app (si la app bloquea la orientación, igual debe seguir viva)."""
    resultados = {}
    for orientacion in ("LANDSCAPE", "PORTRAIT"):
        try:
            app.d.orientation = orientacion
            time.sleep(2)
            resultados[orientacion] = app.d.orientation
        except Exception as e:  # la app puede bloquear la orientación
            resultados[orientacion] = f"no rota ({type(e).__name__})"
        registro["evidencias"].append(app.captura("SMK05", orientacion.lower(), f"Orientación {orientacion.lower()}"))
    errores = app.errores_nuevos()
    registro["detalle"].update({"orientaciones": resultados, "crashes_o_anr": errores})
    assert app.en_primer_plano(), "La app se cerró al rotar"
    assert not errores, f"Crash o ANR: {errores}"


def test_06_exploracion_basica(app, registro):
    """SMK-06: tocar los primeros elementos de la pantalla inicial no produce crashes."""
    if not getattr(app, "firma_inicio", None):
        app.esperar_contenido()
        app.marcar_inicio()
    assert app.volver_al_inicio(), "No se pudo volver a la pantalla inicial antes de explorar"
    grabando = app.grabar()
    visitados = []
    for i in range(config.EXPLORAR_N):
        elementos = app.clickeables()
        if i >= len(elementos):
            break
        etiqueta = app.etiqueta(elementos[i])
        try:
            elementos[i].click()
        except Exception:
            continue  # el elemento cambió o desapareció; se sigue con el próximo
        time.sleep(2)
        errores = app.errores_nuevos()
        registro["evidencias"].append(app.captura("SMK06", f"{i + 1}", f"Después de tocar «{etiqueta}»"))
        sigue_abierta = app.en_primer_plano()
        volvio = app.volver_al_inicio()
        visitados.append({"elemento": etiqueta, "sigue_abierta": sigue_abierta,
                          "volvio_al_inicio": volvio, "crashes_o_anr": errores})
        if not volvio:
            break  # sin volver a la pantalla inicial, los próximos elementos no serían los de inicio
    video = app.detener_grabacion("SMK06_grabacion") if grabando else None
    if video:
        registro["evidencias"].append({"archivo": video, "descripcion": "Grabación de la exploración"})
    registro["detalle"]["recorrido"] = visitados
    fallas = [v for v in visitados if v["crashes_o_anr"] or not v["sigue_abierta"]]
    perdidos = [v["elemento"] for v in visitados if not v["volvio_al_inicio"]]
    assert visitados, "No se encontraron elementos tocables en la pantalla inicial"
    assert not fallas, f"Elementos que cerraron la app o produjeron errores: {fallas}"
    assert not perdidos, f"No se pudo volver al inicio con «Atrás» después de: {perdidos}"
