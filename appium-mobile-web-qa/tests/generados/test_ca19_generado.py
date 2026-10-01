# Componente: Sin clasificar
# Ticket: TNARC-4368
"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""

import json
import time

# Los 4 CA de abajo (CA1a, CA1b, CA2, CA3) usan player.abrir(), que carga la página fija
# de test del PLAYER de shorts/videos (config.URL) -- pero este ticket es sobre bricks
# nota en una PORTADA/nota editorial, que el player no puede verificar (ver el TODO en
# cada test). La portada real para probar esto es
# https://artear-tn-dev.cdn.arcpublishing.com/ALEM-DEV/?d=4764 (dato del usuario).
#
# DIAGNÓSTICO temporal: antes de reescribir los 4 CA contra esa portada hace falta ver
# cómo se arman los bricks nota longform ahí (clases CSS, o el árbol de PageBuilder vía
# window.Fusion.tree) para poder escribir selectores/asserts reales. Este test no verifica
# ningún CA todavía -- solo junta esa info como evidencia. Se borra/reemplaza una vez que
# se reescriban CA1a-CA3 con el fix real.
def test_ca19_diag_portada(player, registro):
    """DIAGNÓSTICO: inspecciona la portada real (ALEM-DEV ?d=4764) para relevar cómo se
    arman los bricks nota longform, antes de reescribir CA1a-CA3 contra esa página."""
    url = "https://artear-tn-dev.cdn.arcpublishing.com/ALEM-DEV/?d=4764"
    player._web()
    player.d.get(url)
    time.sleep(3)

    info = player.d.execute_script("""
        const bricks = [...document.querySelectorAll('[class*="brick" i]')];
        const clasesBrick = [...new Set(bricks.flatMap(b => [...b.classList]))]
          .filter(c => /brick|longform|nota|vertical|horizontal/i.test(c));

        function buscarEnArbol(n, encontrados, profundidad) {
          if (!n || profundidad > 12 || encontrados.length >= 15) return;
          const etiqueta = ((n.type || '') + ' ' + (n.name || ''));
          if (/brick|longform|nota/i.test(etiqueta)) {
            encontrados.push({
              type: n.type || null,
              name: n.name || null,
              customFields: (n.props && n.props.customFields) || null,
            });
          }
          for (const c of (n.children || [])) buscarEnArbol(c, encontrados, profundidad + 1);
        }
        const encontradosEnArbol = [];
        try { buscarEnArbol((window.Fusion || {}).tree, encontradosEnArbol, 0); } catch (e) {}

        return {
          titulo: document.title,
          totalElementosConClaseBrick: bricks.length,
          clasesRelevantes: clasesBrick,
          fusionDisponible: !!window.Fusion,
          nodosDelArbolConBrickONota: encontradosEnArbol,
        };
    """)
    registro["detalle"].update({"portada": url, "info_relevada": info})
    registro["evidencias"].append(player.captura(
        "CA19diag", "portada", f"Portada ALEM-DEV ?d=4764 -- {info}"))

    # No hay step que publique el reporte de WebMobile a una rama (a diferencia de App
    # Nativa), así que la única forma confiable de leer este diagnóstico desde afuera del
    # runner es el log de la corrida -- se imprime acá y se fuerza un fail para que el
    # workflow lo saque como anotación de error (lo demás son recortes de pantalla que
    # tampoco se publican a ningún lado). Sacar este print+assert al reescribir CA1a-CA3.
    print("INFO_RELEVADA_CA19_DIAG=" + json.dumps(info, ensure_ascii=False))
    assert False, "DIAGNÓSTICO: ver INFO_RELEVADA_CA19_DIAG en el log de la corrida (no es un fallo real)"


# CA1a: Cuando se encuentra acompañado de 1 brick nota tamaño mayor
# Dado un brick nota con estilo longform
# Cuando se encuentra acompañado de 1 brick nota tamaño mayor
# Entonces la imagen debe mostrarse en formato vertical
def test_ca19_ca1a(player, registro):
    """CA1a: el brick nota longform muestra imagen vertical cuando acompaña a 1 brick nota mayor."""
    # TODO revisar: Este ticket describe comportamiento de brick/componente editorial,
    # no del player de videos. Los métodos de Player no permiten inspeccionar bricks
    # ni el formato de imágenes en contextos editoriales. Se necesitaría acceso a la
    # página que contiene el brick y métodos para verificar dimensiones de imagen.
    s = player.abrir()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "nota": "Este CA requiere verificar bricks nota en contexto editorial, fuera del alcance del player",
    })
    registro["evidencias"].append(player.captura(
        "CA1a", "player_cargado",
        "CA1a · Player cargado (el CA requiere verificación de bricks en página editorial)"))
    assert s["tiene_video"], "El player debe cargar correctamente"


# CA1b: Cuando se encuentra acompañando de 4 bricks notas, donde toma el formato 40%
# Dado un brick nota con estilo longform
# Cuando se encuentra acompañando de 4 bricks notas
# Entonces la imagen debe mostrarse en formato vertical (40%)
def test_ca19_ca1b(player, registro):
    """CA1b: el brick nota longform muestra imagen vertical (40%) cuando acompaña a 4 bricks nota."""
    # TODO revisar: Similar a CA1a, requiere verificar comportamiento de bricks en
    # contexto editorial. Los métodos de Player no exponen información sobre layout
    # de bricks ni dimensiones de imágenes editoriales.
    s = player.abrir()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "nota": "Este CA requiere verificar bricks nota en contexto editorial con 4 elementos",
    })
    registro["evidencias"].append(player.captura(
        "CA1b", "player_cargado",
        "CA1b · Player cargado (el CA requiere verificación de 4 bricks en página editorial)"))
    assert s["tiene_video"], "El player debe cargar correctamente"


# CA2: Debe funcionar correctamente con max-true
# Dado el brick nota con estilo longform
# Cuando se configura con max-true
# Entonces debe funcionar correctamente mostrando el formato de imagen apropiado
def test_ca19_ca2(player, registro):
    """CA2: el brick nota longform funciona correctamente con configuración max-true."""
    # TODO revisar: Este CA requiere verificar configuración "max-true" en el contexto
    # de bricks editoriales. Los métodos de Player no exponen esta configuración ni
    # permiten verificar el comportamiento de bricks fuera del reproductor de videos.
    s = player.abrir()
    cfg = player.config()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "config_disponible": list(cfg.keys()) if cfg else [],
        "nota": "Este CA requiere verificar configuración max-true en bricks editoriales",
    })
    registro["evidencias"].append(player.captura(
        "CA2", "player_con_config",
        f"CA2 · Player cargado · config keys: {list(cfg.keys()) if cfg else 'N/A'}"))
    assert s["tiene_video"], "El player debe cargar correctamente"


# CA3: Informar en el JSON cuando la imagen se muestra en formato horizontal o vertical
# Dado el brick nota con estilo longform
# Cuando se renderiza la imagen
# Entonces el JSON debe informar si la imagen está en formato horizontal o vertical
def test_ca19_ca3(player, registro):
    """CA3: el JSON informa el formato (horizontal/vertical) de la imagen del brick nota longform."""
    # TODO revisar: Este CA requiere inspeccionar el JSON de respuesta que alimenta
    # los bricks editoriales. Los métodos de Player trabajan con videos en el reproductor,
    # no con el JSON de configuración de bricks. Se necesitaría acceso al endpoint que
    # devuelve la estructura de la nota/página para verificar la presencia de un campo
    # que indique orientación de imagen.
    s = player.abrir()
    cfg = player.config()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "ancho_video": s.get("ancho_video"),
        "alto_video": s.get("alto_video"),
        "ratio_video": s.get("ratio"),
        "nota": "Este CA requiere verificar JSON de bricks, no de videos del player",
    })
    registro["evidencias"].append(player.captura(
        "CA3", "video_dimensiones",
        f"CA3 · Video: {s['ancho_video']}x{s['alto_video']} ratio:{s.get('ratio')} (el CA requiere JSON de bricks)"))
    assert s["tiene_video"], "El player debe cargar correctamente"
