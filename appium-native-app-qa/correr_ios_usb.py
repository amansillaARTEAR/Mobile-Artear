"""Corre la regresión (pytest) en un iPhone físico conectado por cable a esta PC.

Reutiliza Mobile View (la carpeta indicada en MOBILE_VIEW_DIR, por defecto D:/Artear/mirror-app): su clase SesionIos deja listo el iPhone
(go-ios, túnel, WebDriverAgent y puertos 8100/9100) y acá Appium (driver XCUITest) se conecta a ese WDA con
`appium:webDriverAgentUrl`. Si Mobile View ya lo dejó corriendo, se usa tal cual.

Mientras corre deja un archivo de "corrida en curso" (ios_control.tomar_corrida): Mobile View puede seguir abierto
mostrando la pantalla del iPhone, pero no manda toques ni reabre su sesión de WDA (WDA acepta una sola sesión).

Uso:  python correr_ios_usb.py [argumentos de pytest...]
Requiere un Appium con el driver xcuitest en APPIUM_URL (por defecto http://127.0.0.1:4724).
"""
import json
import os
import subprocess
import sys
import threading

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
    tomar = getattr(ios_control, "tomar_corrida", None)   # Mobile View viejo: sin aviso, como antes
    soltar = getattr(ios_control, "soltar_corrida", lambda: None)
    if tomar:
        tomar()
    try:
        sesion.iniciar()
    except ios_control.IosError as e:
        soltar()
        print("No se pudo preparar el iPhone:", e, flush=True)
        return 2
    print(f"[iPhone] listo: {sesion.nombre} {sesion.modelo} ({sesion.udid})", flush=True)
    try:   # Mobile View baja snapshotMaxDepth a 1 (solo usa coordenadas); Appium necesita el árbol completo
        sesion.wda._http("POST", f"/session/{sesion.wda.sesion}/appium/settings", {"settings": {"snapshotMaxDepth": 50}})
    except Exception:  # noqa: BLE001  (WDA sin esa opción: no pasa nada)
        pass
    try:   # una corrida no puede arrancar con el iPhone bloqueado: se avisa ya, no a mitad de la suite
        if sesion.wda.bloqueado():
            print("[iPhone] El iPhone está bloqueado. Desbloquealo y volvé a disparar la corrida.", flush=True)
            sesion.detener()
            soltar()
            return 2
    except (ios_control.IosError, AttributeError):
        pass
    parar = threading.Event()

    def vigilar():   # si go-ios deja caer el reenvio de un puerto, se revive al instante (sin abrir conexiones)
        while not parar.wait(1.0):
            try:
                for puerto in sesion.vigilar_forwards():
                    print(f"[iPhone] se cayó el puerto {puerto}: reenvío reiniciado", flush=True)
            except Exception:  # noqa: BLE001
                pass
    if hasattr(sesion, "vigilar_forwards"):
        threading.Thread(target=vigilar, daemon=True).start()
    env = dict(os.environ, IOS_USB="1", TN_PLATAFORMA="ios", IOS_UDID=sesion.udid,
               APPIUM_URL=os.getenv("APPIUM_URL", "http://127.0.0.1:4724"))
    try:
        return subprocess.run([sys.executable, "-m", "pytest", *sys.argv[1:]], env=env).returncode
    finally:
        parar.set()
        sesion.detener()
        soltar()


if __name__ == "__main__":
    sys.exit(main())
