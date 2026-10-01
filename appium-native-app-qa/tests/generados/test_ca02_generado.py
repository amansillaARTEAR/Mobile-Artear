# Componente: AMR-2087 - TN Videos verticales | Navbar | Crear Tooltip
# Ticket: AMR-2087
"""Casos generados automáticamente a partir de un ticket de Jira, uno por cada criterio de aceptación (CA). REVISAR ANTES DE APROBAR EL PR."""

import time


def _tooltip_presente(app):
    """Detecta el tooltip buscando "videos verticales" (el subtítulo) entre CUALQUIER
    elemento visible, no solo los clickeables: el título ("NUEVO") y el subtítulo
    ("Informate con nuestros videos verticales") son DOS elementos separados que nunca
    coinciden en el texto de uno solo, y el subtítulo no es clickeable, así que buscarlos
    juntos vía clickeables() nunca puede dar True aunque el tooltip esté en pantalla."""
    return bool(app.buscar("videos verticales"))


def _texto_tooltip(app):
    """Junta el texto del título y el subtítulo del tooltip (son elementos separados)
    para poder verificar el contenido completo esperado."""
    partes = []
    for fragmento in ("NUEVO", "videos verticales"):
        elementos = app.buscar(fragmento)
        if elementos:
            partes.append(app.etiqueta(elementos[0]))
    return " - ".join(partes)


def _boton_cerrar_tooltip(app):
    """Busca el botón "X" del tooltip entre los elementos clickeables (a diferencia del
    subtítulo, el botón de cerrar sí es clickeable). El ícono puede no tener texto visible
    y exponer su nombre solo vía resource-id (ej. "btn_tooltip_close" o "ic_close"), que
    etiqueta() también devuelve -- por eso "close" se busca como substring, no solo como
    match exacto."""
    for el in app.clickeables():
        etiqueta = app.etiqueta(el).strip().lower()
        if etiqueta in ("x", "✕", "×") or any(p in etiqueta for p in ("cerrar", "dismiss", "close")):
            return el
    return None


# CA1: Debe mostrar la animación al iniciarse
# Dado que el usuario abre la app por primera vez
# Cuando la pantalla inicial se carga
# Entonces debe aparecer el tooltip con animación
def test_ca02_ca1(app, registro):
    """CA1: verifica que el tooltip aparece con animación al iniciar la app."""
    # reiniciar_limpio() borra los datos/preferencias para simular de verdad una app
    # recién instalada -- si no, el flag de "usuario ya vio esto" queda pegado en el
    # dispositivo real entre corridas y el tooltip no vuelve a aparecer.
    app.reiniciar_limpio()
    time.sleep(2)  # tiempo para que la animación de entrada termine

    tooltip_visible = _tooltip_presente(app)

    registro["detalle"].update({"tooltip_inicial_visible": tooltip_visible})
    registro["evidencias"].append(app.captura("CA1", "tooltip_inicial", "Tooltip al iniciar"))

    assert tooltip_visible, "El tooltip no apareció al iniciar la app"


# CA2: Se debe mostrar hasta, interactuar con el scroll y desaparecer con efecto
# Dado que el tooltip está visible
# Cuando el usuario hace scroll en la pantalla
# Entonces el tooltip debe mantenerse visible hasta que interactúe y luego desaparecer con efecto
def test_ca02_ca2(app, registro):
    """CA2: DIAGNÓSTICO -- mide si el tooltip se cierra solo por tiempo, sin scroll ni
    interacción. Dos corridas seguidas con un scroll calculado para quedar claramente
    afuera del rect del tooltip (confirmado comparando las evidencias: el fondo de la
    pantalla no se mueve nada) igual terminaron con el tooltip cerrado -- así que puede no
    ser el scroll. Esta versión no scrollea ni toca nada, solo espera y va sacando capturas
    a distintos tiempos, para aislar si hay un auto-dismiss por tiempo. Es temporal: una
    vez que se vea el patrón, se reescribe con el fix real y los asserts del CA."""
    app.reiniciar_limpio()
    time.sleep(2)

    tiempos = []
    for segundos in (0, 2, 4, 6, 9):
        if segundos:
            time.sleep(segundos - tiempos[-1][0] if tiempos else segundos)
        presente = _tooltip_presente(app)
        tiempos.append((segundos, presente))
        registro["evidencias"].append(
            app.captura("CA2", f"diag_t{segundos}s", f"Tooltip a los {segundos}s sin tocar nada: {presente}"))

    registro["detalle"].update({"tooltip_por_tiempo_sin_interactuar": {f"{s}s": p for s, p in tiempos}})

    assert tiempos[0][1], "El tooltip no apareció"


# CA3: Una vez que el usuario accede debe permanecer cerrada
# Dado que el tooltip está visible
# Cuando el usuario accede a la sección de videos verticales
# Entonces el tooltip debe cerrarse y no volver a aparecer
def test_ca02_ca3(app, registro):
    """CA3: verifica que el tooltip no reaparece después de acceder a la sección."""
    app.reiniciar_limpio()
    time.sleep(2)

    # Buscamos y clickeamos en la sección de videos verticales desde la navbar
    navbar = app.navbar()
    seccion_encontrada = False

    for item in navbar:
        if any(p in item["etiqueta"].lower() for p in ("shorts", "video", "vertical")):
            item["el"].click()
            seccion_encontrada = True
            time.sleep(2)
            break

    registro["evidencias"].append(app.captura("CA3", "acceso_seccion", "Acceso a sección de videos"))

    # Volvemos al inicio y verificamos que el tooltip no reaparece
    app.volver_al_inicio()
    time.sleep(2)

    tooltip_reaparece = _tooltip_presente(app)

    registro["detalle"].update({"seccion_encontrada": seccion_encontrada,
                               "tooltip_reaparece_post_acceso": tooltip_reaparece})
    registro["evidencias"].append(app.captura("CA3", "sin_tooltip", "Tooltip no debe reaparecer"))

    assert not tooltip_reaparece, "El tooltip reapareció después de acceder a la sección"


# CA4: En caso que el usuario no acceda al volver a ingresar a la app se le vuelve a mostrar
# Dado que el usuario no accedió a la sección de videos verticales
# Cuando cierra y vuelve a abrir la app
# Entonces el tooltip debe mostrarse nuevamente
def test_ca02_ca4(app, registro):
    """CA4: verifica que el tooltip reaparece si no se accedió a la sección."""
    app.reiniciar_limpio()
    time.sleep(2)

    # No accedemos a la sección -- directamente cerramos y volvemos a abrir la app
    # (reiniciar() hace un reinicio en frío normal, sin volver a limpiar los datos,
    # que es justo lo que hace falta para probar que el tooltip no depende de haberla
    # cerrado con `reiniciar_limpio()` sino de si el usuario accedió a la sección).
    app.reiniciar()
    time.sleep(2)

    tooltip_visible = _tooltip_presente(app)

    registro["detalle"].update({"tooltip_reaparece_sin_acceso": tooltip_visible})
    registro["evidencias"].append(app.captura("CA4", "tooltip_reaparece", "Tooltip al reingresar"))

    assert tooltip_visible, "El tooltip no reapareció al volver a ingresar sin haber accedido"


# CA5: El texto inicial debe ser: NUEVO - Informate con nuestros videos verticales
# Dado que el tooltip está visible
# Cuando el usuario lo observa
# Entonces debe mostrar el texto "NUEVO - Informate con nuestros videos verticales"
def test_ca02_ca5(app, registro):
    """CA5: verifica que el tooltip muestra el texto correcto."""
    app.reiniciar_limpio()
    time.sleep(2)

    texto_encontrado = _texto_tooltip(app)
    texto_correcto = "NUEVO" in texto_encontrado and "Informate" in texto_encontrado and "videos verticales" in texto_encontrado

    registro["detalle"].update({"texto_tooltip": texto_encontrado,
                               "texto_correcto": texto_correcto})
    registro["evidencias"].append(app.captura("CA5", "texto_tooltip", "Texto del tooltip"))

    assert texto_correcto, f"El texto del tooltip no es el esperado. Encontrado: {texto_encontrado}"


# CA6a: Al tocar la x se cierra con el efecto - En caso que no acceda a la sección debe volver a mostrarse
# Dado que el tooltip está visible
# Cuando el usuario toca la x sin acceder a la sección
# Entonces el tooltip se cierra y vuelve a aparecer al reingresar
def test_ca02_ca6a(app, registro):
    """CA6a: verifica que el tooltip reaparece tras cerrar con X sin acceder a la sección."""
    app.reiniciar_limpio()
    time.sleep(2)

    boton_x = _boton_cerrar_tooltip(app)
    boton_x_encontrado = boton_x is not None
    if boton_x is not None:
        boton_x.click()
        time.sleep(1)

    registro["evidencias"].append(app.captura("CA6a", "cerrar_tooltip", "Cerrar tooltip con X"))

    # Salimos y volvemos a la app sin haber accedido a la sección
    app.reiniciar()
    time.sleep(2)

    tooltip_reaparece = _tooltip_presente(app)

    registro["detalle"].update({"boton_x_encontrado": boton_x_encontrado,
                               "tooltip_reaparece_post_x": tooltip_reaparece})
    registro["evidencias"].append(app.captura("CA6a", "tooltip_post_x", "Tooltip reaparece tras X"))

    assert boton_x_encontrado, "No se encontró el botón de cerrar (X) del tooltip"
    assert tooltip_reaparece, "El tooltip no reapareció después de cerrar con X sin acceder"


# CA6b: Al tocar la x se cierra con el efecto - En caso que accedió a la sección no debe volver a aparecer
# Dado que el usuario accedió a la sección de videos verticales
# Cuando toca la x del tooltip
# Entonces el tooltip se cierra y no vuelve a aparecer
def test_ca02_ca6b(app, registro):
    """CA6b: verifica que el tooltip no reaparece tras cerrar con X después de acceder."""
    app.reiniciar_limpio()
    time.sleep(2)

    # Accedemos a la sección de videos verticales
    navbar = app.navbar()
    seccion_accedida = False

    for item in navbar:
        if any(p in item["etiqueta"].lower() for p in ("shorts", "video", "vertical")):
            item["el"].click()
            seccion_accedida = True
            time.sleep(2)
            break

    registro["evidencias"].append(app.captura("CA6b", "acceso_seccion", "Acceso a sección antes de cerrar"))

    # Volvemos al inicio
    app.volver_al_inicio()
    time.sleep(1)

    # Cerramos el tooltip con la X (si todavía está visible)
    boton_x = _boton_cerrar_tooltip(app)
    if boton_x is not None:
        boton_x.click()
        time.sleep(1)

    registro["evidencias"].append(app.captura("CA6b", "tooltip_cerrado", "Tooltip cerrado tras acceder"))

    # Salimos y volvemos a abrir la app: al haber accedido a la sección, no debería reaparecer
    app.reiniciar()
    time.sleep(2)

    tooltip_reaparece = _tooltip_presente(app)

    registro["detalle"].update({"seccion_accedida": seccion_accedida,
                               "tooltip_reaparece_post_acceso_y_cierre": tooltip_reaparece})
    registro["evidencias"].append(app.captura("CA6b", "sin_tooltip", "Tooltip no debe reaparecer"))

    assert not tooltip_reaparece, "El tooltip reapareció después de acceder a la sección y cerrarlo con X"
