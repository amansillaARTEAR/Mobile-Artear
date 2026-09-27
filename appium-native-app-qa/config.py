"""Configuración de la suite de app nativa (Android e iOS). Todo se puede sobrescribir con variables de entorno."""
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CARPETA_APKS = RAIZ / "apks"
CARPETA_IPAS = RAIZ / "ipas"

# "android" (dispositivo físico local) o "ios" (AWS Device Farm)
PLATAFORMA = os.getenv("TN_PLATAFORMA", "android").lower()


def app_a_probar() -> Path:
    """App indicada en TN_APP (o TN_APK/TN_IPA por compatibilidad) o, si no, la más
    reciente de la carpeta correspondiente (apks\\ para Android, ipas\\ para iOS)."""
    variable_especifica = "TN_IPA" if PLATAFORMA == "ios" else "TN_APK"
    ruta_directa = os.getenv("TN_APP") or os.getenv(variable_especifica)
    if ruta_directa:
        return Path(ruta_directa).resolve()
    carpeta, patron = (CARPETA_IPAS, "*.ipa") if PLATAFORMA == "ios" else (CARPETA_APKS, "*.apk")
    apps = sorted(carpeta.glob(patron), key=lambda p: p.stat().st_mtime)
    if not apps:
        raise FileNotFoundError(f"No hay ningún {patron} en {carpeta}. Copiá ahí la app a probar.")
    return apps[-1]


# Alias por compatibilidad con el código existente de la suite (smoke, conftest).
def apk_a_probar() -> Path:
    return app_a_probar()


# Servidor Appium: local por defecto; para AWS Device Farm, la URL de la sesión remota.
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")

# Tiempo máximo aceptable de arranque en frío, en segundos
ARRANQUE_MAX_S = float(os.getenv("TN_ARRANQUE_MAX", "10"))
# Cantidad de elementos de la pantalla inicial que toca la exploración básica
EXPLORAR_N = int(os.getenv("TN_EXPLORAR_N", "5"))

EXTRA_CAPS = json.loads(os.getenv("EXTRA_CAPS", "{}"))


def _caps_android(app: Path) -> dict:
    return {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:app": str(app),                       # Appium instala la app y detecta paquete y actividad
        "appium:udid": os.getenv("ANDROID_UDID"),
        "appium:autoGrantPermissions": True,          # acepta los permisos de la app sin diálogos
        "appium:noReset": False,                      # cada corrida arranca con la app limpia (solo esta app)
        "appium:uiautomator2ServerInstallTimeout": 120000,
        "appium:adbExecTimeout": 60000,
        "appium:androidInstallTimeout": 180000,
        "appium:newCommandTimeout": 300,
    }


def _caps_ios(app: Path) -> dict:
    return {
        "platformName": "iOS",
        "appium:automationName": "XCUITest",
        "appium:app": str(app),                       # .ipa a instalar (AWS Device Farm la reemplaza por su build)
        "appium:deviceName": os.getenv("IOS_DEVICE", "iPhone"),
        "appium:platformVersion": os.getenv("IOS_VERSION"),
        "appium:udid": os.getenv("IOS_UDID"),
        "appium:bundleId": os.getenv("IOS_BUNDLE_ID"),  # opcional: app ya instalada, en vez de instalar el .ipa
        "appium:noReset": False,
        "appium:newCommandTimeout": 300,
    }


def caps(app: Path) -> dict:
    base = _caps_ios(app) if PLATAFORMA == "ios" else _caps_android(app)
    c = {k: v for k, v in {**base, **EXTRA_CAPS}.items() if v not in (None, "")}
    if not APPIUM_URL.startswith(("http://127.0.0.1", "http://localhost")):
        # Granja en la nube (AWS Device Farm): el dispositivo lo define la sesión remota
        # y estas capabilities no están soportadas.
        for clave in ("appium:udid", "appium:platformVersion"):
            c.pop(clave, None)
    return c
