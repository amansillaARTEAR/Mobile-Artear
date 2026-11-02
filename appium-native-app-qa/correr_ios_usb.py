"""Corre la regresión (pytest) en un iPhone físico conectado por cable a esta PC.

Reutiliza Mobile View (la carpeta indicada en MOBILE_VIEW_DIR, por defecto D:/Artear/mirror-app): su clase SesionIos deja listo el iPhone
(go-ios, túnel, WebDriverAgent y puertos 8100/9100) y acá Appium (driver XCUITest) se conecta a ese WDA con
`appium:webDriverAgentUrl`. Si Mobile View ya lo dejó corriendo, se usa tal cual.

Uso:  python correr_ios_usb.py [argumentos de pytest...]
Requiere un Appium con el driver xcuitest en APPIUM_URL (por defecto http://127.0.0.1:4724).
"""
import json
import os
import subprocess
import sys

MOBILE_VIEW = os.getenv("MOBILE_VIEW_DIR", r"D:\Artear\mirror-app")


def main():
    sys.path.insert(0, MOBILE_VIEW)
    try:
        import ios_control
    except ImportError as e:
        print(f"No pude cargar Mobile View desde {MOBILE_VIEW}: {e}", flush=True)
        return 2
    try:
        cfg = json.load(open(os.path.join(MOBILE_VIEW, "config.json"), encoding="utf-8"))
    except OSError:
        cfg = {}
    sesion = ios_control.SesionIos(cfg, avisar=lambda t: print("[iPhone]", t, flush=True))
    try:
        sesion.iniciar()
    except ios_control.IosError as e:
        print("No se pudo preparar el iPhone:", e, flush=True)
        return 2
    print(f"[iPhone] listo: {sesion.nombre} {sesion.modelo} ({sesion.udid})", flush=True)
    env = dict(os.environ, IOS_USB="1", TN_PLATAFORMA="ios", IOS_UDID=sesion.udid,
               APPIUM_URL=os.getenv("APPIUM_URL", "http://127.0.0.1:4724"))
    try:
        return subprocess.run([sys.executable, "-m", "pytest", *sys.argv[1:]], env=env).returncode
    finally:
        sesion.detener()


if __name__ == "__main__":
    sys.exit(main())
