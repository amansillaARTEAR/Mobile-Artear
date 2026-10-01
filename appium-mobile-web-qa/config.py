"""Configuración de la suite. Todo se puede sobrescribir con variables de entorno."""
import json
import os

# Página del player en DEV (sin ?d=: se prueba la versión promovida)
URL = os.getenv(
    "TN_URL",
    "https://artear-tn-dev.cdn.arcpublishing.com/shorts/player/videos/"
    "test-section/2025/12/19/videolab-collection-8/",
)
VERSION_ESPERADA = os.getenv("TN_VERSION", "4743")

# Portada/nota a validar en los tests que no son sobre el player (ej. CA19, brick nota en
# una portada editorial) -- se arma en el workflow a partir del input "portada" (ver
# webmobile.yml) con el dominio/versión del ambiente elegido. Vacío si no se indicó: cada
# test decide su propio default en ese caso (para no romper corridas manuales/viejas).
PORTADA_URL = os.getenv("TN_PORTADA", "")

# Etiqueta amarilla con el caso y los valores medidos dentro de cada captura (TN_ETIQUETAS=1 para activarla)
ETIQUETAS = os.getenv("TN_ETIQUETAS", "0") == "1"

# Servidor Appium (local por defecto; para la nube, la URL del endpoint del proveedor)
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")

ANDROID_CAPS = {
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "browserName": "Chrome",
    "appium:udid": os.getenv("ANDROID_UDID"),          # ej. R5CT70JC25E (ver `adb devices`)
    "appium:chromedriverAutodownload": True,
    "appium:noReset": True,                             # no borrar los datos de Chrome del celular
    "appium:uiautomator2ServerInstallTimeout": 120000,  # la primera instalación en el celular puede tardar
    "appium:adbExecTimeout": 60000,
    "appium:newCommandTimeout": 300,
}

IOS_CAPS = {
    "platformName": "iOS",
    "appium:automationName": "XCUITest",
    "browserName": "Safari",
    "appium:deviceName": os.getenv("IOS_DEVICE", "iPhone"),
    "appium:platformVersion": os.getenv("IOS_VERSION"),
    "appium:udid": os.getenv("IOS_UDID"),
    "appium:nativeWebTap": True,                        # toques web convertidos en toques nativos
    "appium:noReset": True,                             # no borrar los datos de Safari
    "appium:newCommandTimeout": 300,
}

# Capabilities extra del proveedor en la nube (JSON), ej. opciones de BrowserStack o AWS
EXTRA_CAPS = json.loads(os.getenv("EXTRA_CAPS", "{}"))


def caps_para(plataforma: str) -> dict:
    base = ANDROID_CAPS if plataforma == "android" else IOS_CAPS
    caps = {k: v for k, v in {**base, **EXTRA_CAPS}.items() if v not in (None, "")}
    if not APPIUM_URL.startswith(("http://127.0.0.1", "http://localhost")):
        # Granja en la nube (AWS Device Farm): el dispositivo lo define la sesión remota
        # y estas capabilities no están soportadas.
        for clave in ("appium:udid", "appium:platformVersion"):
            caps.pop(clave, None)
    return caps
