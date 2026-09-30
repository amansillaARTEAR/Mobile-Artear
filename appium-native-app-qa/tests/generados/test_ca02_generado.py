# Componente: Navbar
# Ticket: TEST-001
"""Escenarios generados automáticamente a partir de un ticket de Jira, aplicando diseño de casos (positivo/negativo/borde). REVISAR ANTES DE APROBAR EL PR."""

import time


# Escenario: Positivo
# Dado que el usuario está logueado y la app muestra el navbar
# Cuando toca el botón "Perfil" en el navbar
# Entonces se abre la pantalla de perfil del usuario
def test_ca02_positivo(app, registro):
    """POSITIVO: al tocar Perfil en el navbar estando logueado, se abre la pantalla de perfil."""
    # Esperar a que la app cargue completamente
    app.esperar_contenido(timeout=10)
    time.sleep(2)
    
    # Capturar estado inicial
    registro["evidencias"].append(app.captura("CA02", "inicial", "Estado inicial antes de tocar Perfil"))
    
    # Obtener navbar y buscar botón de Perfil
    navbar_items = app.navbar()
    boton_perfil = None
    for item in navbar_items:
        if "perfil" in item["etiqueta"].lower():
            boton_perfil = item
            break
    
    assert boton_perfil is not None, "No se encontró el botón de Perfil en el navbar"
    registro["detalle"].update({"boton_perfil_encontrado": True, "etiqueta_boton": boton_perfil["etiqueta"]})
    
    # Tocar el botón de Perfil
    boton_perfil["el"].click()
    time.sleep(3)
    
    # Capturar pantalla resultante
    registro["evidencias"].append(app.captura("CA02", "perfil_abierto", "Pantalla después de tocar Perfil"))
    
    # Verificar que se abrió la pantalla de perfil
    # TODO revisar: no hay método directo para validar qué pantalla está abierta, se busca indicadores de perfil
    clickeables = app.clickeables()
    textos_visibles = [app.etiqueta(el).lower() for el in clickeables if app.etiqueta(el)]
    tiene_indicadores_perfil = any(texto for texto in textos_visibles if "perfil" in texto or "cuenta" in texto or "configuración" in texto or "ajustes" in texto)
    
    registro["detalle"].update({"pantalla_cambio": True, "indicadores_perfil_visibles": tiene_indicadores_perfil})
    
    # Verificar que no hubo errores
    errores = app.errores_nuevos()
    registro["detalle"].update({"errores": errores})
    
    assert not errores, f"Se produjeron errores al abrir perfil: {errores}"
    assert tiene_indicadores_perfil, "No se detectaron indicadores de la pantalla de perfil"


# Escenario: Negativo
# Dado que el usuario NO está logueado y la app muestra el navbar
# Cuando toca el botón "Perfil" en el navbar
# Entonces se muestra la pantalla de login en su lugar
def test_ca02_negativo(app, registro):
    """NEGATIVO: al tocar Perfil en el navbar sin estar logueado, se muestra pantalla de login."""
    # TODO revisar: se asume que hay forma de cerrar sesión o que el test corre en app sin login previo
    # Si ya hay sesión activa de tests anteriores, este escenario requeriría logout primero
    
    # Esperar a que la app cargue
    app.esperar_contenido(timeout=10)
    time.sleep(2)
    
    # Capturar estado inicial
    registro["evidencias"].append(app.captura("CA02", "inicial_sin_login", "Estado inicial sin login"))
    
    # Obtener navbar y buscar botón de Perfil
    navbar_items = app.navbar()
    boton_perfil = None
    for item in navbar_items:
        if "perfil" in item["etiqueta"].lower():
            boton_perfil = item
            break
    
    assert boton_perfil is not None, "No se encontró el botón de Perfil en el navbar"
    registro["detalle"].update({"boton_perfil_encontrado": True})
    
    # Tocar el botón de Perfil
    boton_perfil["el"].click()
    time.sleep(3)
    
    # Capturar pantalla resultante
    registro["evidencias"].append(app.captura("CA02", "login_mostrado", "Pantalla después de tocar Perfil sin login"))
    
    # Verificar que se muestra pantalla de login
    clickeables = app.clickeables()
    textos_visibles = [app.etiqueta(el).lower() for el in clickeables if app.etiqueta(el)]
    tiene_indicadores_login = any(texto for texto in textos_visibles if "login" in texto or "iniciar" in texto or "ingresar" in texto or "correo" in texto or "contraseña" in texto or "email" in texto or "password" in texto)
    
    registro["detalle"].update({"muestra_login": tiene_indicadores_login, "textos_encontrados": [t for t in textos_visibles if any(palabra in t for palabra in ["login", "iniciar", "ingresar", "correo", "contraseña"])]})
    
    # Verificar que no hubo errores
    errores = app.errores_nuevos()
    registro["detalle"].update({"errores": errores})
    
    assert not errores, f"Se produjeron errores al intentar abrir perfil: {errores}"
    assert tiene_indicadores_login, "No se detectó la pantalla de login como se esperaba"
