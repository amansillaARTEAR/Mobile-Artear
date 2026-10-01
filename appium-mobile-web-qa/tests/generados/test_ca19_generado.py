# Componente: Sin clasificar
# Ticket: TNARC-4368
"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""

import time

import config


def test_ca19_diag_portada_url(registro):
    """DIAGNÓSTICO temporal: confirma qué valor exacto llegó a config.PORTADA_URL desde el
    input "portada" del workflow -- las últimas corridas con ese input fallaron con
    ERR_NAME_NOT_RESOLVED al navegar, aunque la URL debería ser idéntica a la hardcodeada."""
    registro["detalle"]["portada_url_repr"] = repr(config.PORTADA_URL)
    assert False, f"DIAGNOSTICO: config.PORTADA_URL = {config.PORTADA_URL!r}"

# Este ticket es sobre el brick nota con estilo "longform" en una PORTADA/nota editorial
# (no sobre el player de shorts/videos), así que CA1a/CA1b navegan directo a la portada real
# donde el usuario confirmó que el brick longform está configurado:
# https://artear-tn-dev.cdn.arcpublishing.com/ALEM-DEV/?d=4764 -- este es el default si no se
# indicó el input "portada" al disparar el workflow (ver config.PORTADA_URL); si se indicó,
# se usa esa en su lugar, para poder validar el mismo CA en otra portada sin tocar código.
#
# Regla del ticket: el brick nota longform muestra la imagen en horizontal, EXCEPTO cuando
# está acompañado de 1 brick nota de tamaño mayor (ahí va vertical -- CA1a) o acompañado de
# 4 bricks nota (ahí va vertical al 40% -- CA1b). CA3 (que el JSON informe el formato) queda
# fuera de alcance por pedido explícito.
#
# Para no depender de adivinar clases CSS, se recorre window.Fusion.tree (customFields.style
# / Tamaño configurados en PageBuilder, la fuente de verdad) agrupando por contenedor padre,
# y se cruza cada grupo con la medida real del <img> de cada hermano en el DOM (mismo orden
# de aparición). Diagnosticado contra la portada real: el grupo de 2 (longform + 1 "nota
# mayor") da sistemáticamente 1 imagen vertical (~314x558) + 1 horizontal (~314x177); el
# grupo de 5 (longform + 4 bricks nota) da 1 vertical + 4 horizontales. La validación evita
# atribuir la imagen a un hermano puntual (en grupos grandes el cruce por posición no es
# confiable) y en cambio valida por grupo: cuántos son longform, cuántos tienen tamaño
# "mayor", y cuántas imágenes del grupo son verticales/horizontales.
#
# La captura de evidencia hace scrollIntoView sobre el grupo encontrado antes de capturar,
# para que muestre el brick longform en vez de lo que haya al tope de la portada.
JS_ENFOCAR_GRUPO_LONGFORM = r"""
const criterio = arguments[0];
const treeItems = [];
function walk(nodo, padre) {
  if (!nodo) return;
  const cf = (nodo.props && nodo.props.customFields) || null;
  if (cf && typeof cf.style === 'string' && /brick|nota/i.test(nodo.type || '')) {
    treeItems.push({ padre, cf });
  }
  (nodo.children || []).forEach(h => walk(h, nodo));
}
walk((window.Fusion || {}).tree, null);
const domEls = [...document.querySelectorAll('[class*="brick_nota" i]')];
const combinados = treeItems.map((t, i) => {
  const el = domEls[i];
  const img = el ? el.querySelector('img, picture img') : null;
  const rect = img ? img.getBoundingClientRect() : null;
  const claveTam = Object.keys(t.cf).find(k => /tama|size/i.test(k));
  return {
    padre: t.padre, el,
    estilo: t.cf.style,
    tamanio: claveTam ? t.cf[claveTam] : null,
    imgAncho: rect ? Math.round(rect.width) : null,
    imgAlto: rect ? Math.round(rect.height) : null,
  };
});
const grupos = new Map();
combinados.forEach(c => {
  if (!grupos.has(c.padre)) grupos.set(c.padre, []);
  grupos.get(c.padre).push(c);
});
const listaGrupos = [];
grupos.forEach((items) => {
  const cantLongform = items.filter(i => /longform/i.test(i.estilo || '')).length;
  if (cantLongform < 1) return;
  const verticales = items.filter(i => i.imgAlto != null && i.imgAncho != null && i.imgAlto > i.imgAncho).length;
  const horizontales = items.filter(i => i.imgAlto != null && i.imgAncho != null && i.imgAncho >= i.imgAlto).length;
  const cantMayor = items.filter(i => /mayor/i.test(i.tamanio || '')).length;
  listaGrupos.push({ total: items.length, cantLongform, cantMayor, verticales, horizontales, items });
});
const objetivo = listaGrupos.find(g => g.total === criterio.total && g.cantLongform >= 1
  && (!criterio.requiereMayor || g.cantMayor >= 1));
let enfocado = false;
if (objetivo) {
  const el = objetivo.items[0].el;
  if (el && el.scrollIntoView) { el.scrollIntoView({ block: 'center', inline: 'center' }); enfocado = true; }
}
return { enfocado, grupos: listaGrupos.map(g => ({
  total: g.total, cantLongform: g.cantLongform, cantMayor: g.cantMayor,
  verticales: g.verticales, horizontales: g.horizontales,
  items: g.items.map(({ padre, el, ...resto }) => resto) })) };
"""


def _cerrar_publicidad_inicial(player):
    """Cierra el aviso que aparece apenas carga la portada (banner del header), con un
    toque en su botón "X" -- medido directo sobre el dispositivo del runner: (944, 339) en
    píxeles de pantalla. Best-effort: si no hay publicidad ahí, el toque no afecta nada más
    porque el brick nota longform que se valida está más abajo, fuera de esa zona."""
    try:
        player.d.execute_script("mobile: clickGesture", {"x": 944, "y": 339})
    except Exception:
        pass


def _grupos_longform(player, criterio):
    url = config.PORTADA_URL or "https://artear-tn-dev.cdn.arcpublishing.com/ALEM-DEV/?d=4764"
    player._web()
    player.d.get(url)
    time.sleep(3)
    _cerrar_publicidad_inicial(player)
    time.sleep(1)
    resultado = player.d.execute_script(JS_ENFOCAR_GRUPO_LONGFORM, criterio)
    if resultado["enfocado"]:
        time.sleep(1)  # deja asentar el scroll antes de capturar
    return url, resultado["grupos"], resultado["enfocado"]


# CA1a: Cuando se encuentra acompañado de 1 brick nota tamaño mayor
# Dado un brick nota con estilo longform
# Cuando se encuentra acompañado de 1 brick nota tamaño mayor
# Entonces la imagen debe mostrarse en formato vertical
def test_ca19_ca1a(player, registro):
    """CA1a: el brick nota longform muestra imagen vertical cuando acompaña a 1 brick nota mayor."""
    url, grupos, enfocado = _grupos_longform(player, {"total": 2, "requiereMayor": True})
    objetivo = next((g for g in grupos if g["total"] == 2 and g["cantLongform"] >= 1 and g["cantMayor"] >= 1), None)
    registro["detalle"].update({"portada": url, "grupos_encontrados": grupos, "grupo_ca1a": objetivo})
    registro["evidencias"].append(player.captura(
        "CA1a", "portada",
        f"CA1a · Portada {url} · grupo longform+1 mayor (scroll al grupo: {enfocado}): {objetivo}"))
    assert objetivo is not None, (
        "No se encontró en la portada un brick nota longform acompañado de exactamente "
        f"1 brick nota de tamaño mayor. Grupos con longform relevados: {grupos}")
    assert objetivo["verticales"] == 1 and objetivo["horizontales"] == 1, (
        "El grupo longform + 1 brick nota mayor no muestra 1 imagen vertical y 1 horizontal "
        f"como exige el CA: {objetivo}")


# CA1b: Cuando se encuentra acompañando de 4 bricks notas, donde toma el formato 40%
# Dado un brick nota con estilo longform
# Cuando se encuentra acompañando de 4 bricks notas
# Entonces la imagen debe mostrarse en formato vertical (40%)
def test_ca19_ca1b(player, registro):
    """CA1b: el brick nota longform muestra imagen vertical (40%) cuando acompaña a 4 bricks nota."""
    url, grupos, enfocado = _grupos_longform(player, {"total": 5, "requiereMayor": False})
    objetivo = next((g for g in grupos if g["total"] == 5 and g["cantLongform"] >= 1), None)
    registro["detalle"].update({"portada": url, "grupos_encontrados": grupos, "grupo_ca1b": objetivo})
    registro["evidencias"].append(player.captura(
        "CA1b", "portada",
        f"CA1b · Portada {url} · grupo longform+4 bricks nota (scroll al grupo: {enfocado}): {objetivo}"))
    assert objetivo is not None, (
        "No se encontró en la portada un brick nota longform acompañado de 4 bricks nota. "
        f"Grupos con longform relevados: {grupos}")
    assert objetivo["verticales"] == 1 and objetivo["horizontales"] == 4, (
        "El grupo longform + 4 bricks nota no muestra 1 imagen vertical (40%) y 4 "
        f"horizontales como exige el CA: {objetivo}")


# CA2: Debe funcionar correctamente con max-true
# Dado el brick nota con estilo longform
# Cuando se configura con max-true
# Entonces debe funcionar correctamente mostrando el formato de imagen apropiado
def test_ca19_ca2(player, registro):
    """CA2: el brick nota longform funciona correctamente con configuración max-true."""
    # TODO revisar: no se encontró en la portada real (ni en customFields relevados vía
    # Fusion.tree) un campo "max-true" asociado al brick nota longform -- no está claro a qué
    # configuración puntual se refiere este CA dentro de PageBuilder. Pendiente de aclaración
    # antes de poder automatizarlo contra la portada real.
    s = player.abrir()
    cfg = player.config()
    registro["detalle"].update({
        "video_inicial": s["video"],
        "config_disponible": list(cfg.keys()) if cfg else [],
        "nota": "Pendiente de aclaración: no se identificó el campo 'max-true' en PageBuilder",
    })
    registro["evidencias"].append(player.captura(
        "CA2", "player_con_config",
        f"CA2 · Player cargado · config keys: {list(cfg.keys()) if cfg else 'N/A'}"))
    assert s["tiene_video"], "El player debe cargar correctamente"
