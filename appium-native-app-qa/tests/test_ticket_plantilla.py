"""Plantilla para los casos de un ticket puntual.

1. Copiá este archivo como test_<ticket>.py (ej. test_tnarc4400.py).
2. Buscá los identificadores de los elementos con Appium Inspector
   (https://github.com/appium/appium-inspector) conectado a tu celular:
   lo ideal es usar accessibility id (content-desc) o resource-id.
3. Escribí un test por criterio de aceptación, con captura en cada paso.
4. Sacá la línea `pytestmark` para que se ejecute.
"""
import pytest
from appium.webdriver.common.appiumby import AppiumBy

pytestmark = pytest.mark.skip(reason="Plantilla: completar con los casos del ticket")


def test_ca01_ejemplo(app, registro):
    """CA1: <texto del criterio de aceptación>."""
    app.volver_al_inicio()
    # Ejemplos de cómo encontrar y tocar elementos:
    # app.d.find_element(AppiumBy.ACCESSIBILITY_ID, "Buscar").click()
    # app.d.find_element(AppiumBy.ID, f"{app.paquete}:id/menu_videos").click()
    # app.d.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Últimas")').click()
    registro["evidencias"].append(app.captura("CA01", "1_inicio", "Pantalla de partida"))
    # registro["detalle"]["dato_medido"] = ...
    assert True
