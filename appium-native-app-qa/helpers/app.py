"""Acciones y chequeos genéricos sobre la app bajo prueba."""
import base64
import re
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException

EN_PRIMER_PLANO = 4  # estado que devuelve query_app_state cuando la app está visible


class App:
    def __init__(self, driver, salida):
        self.d = driver
        self.salida = salida
        try:
            self.paquete = driver.current_package          # Android
        except WebDriverException:
            caps = driver.capabilities
            self.paquete = caps.get("bundleId") or caps.get("CFBundleIdentifier") or ""  # iOS
        try:
            self.actividad_inicial = driver.current_activity  # no existe en iOS
        except WebDriverException:
            self.actividad_inicial = None
        self._logcat()  # descarta el log previo al inicio (no-op en iOS, no hay logcat)

    # ---------- estado ----------
    def en_primer_plano(self) -> bool:
        return self.d.query_app_state(self.paquete) == EN_PRIMER_PLANO

    def esperar_primer_plano(self, timeout=20) -> bool:
        limite = time.time() + timeout
        while time.time() < limite:
            if self.en_primer_plano():
                return True
            time.sleep(0.5)
        return False

    def esperar_contenido(self, timeout=20) -> bool:
        """Espera a que la pantalla tenga al menos un elemento tocable."""
        limite = time.time() + timeout
        while time.time() < limite:
            if self.clickeables():
                return True
            time.sleep(0.5)
        return False

    # ---------- errores ----------
    def _logcat(self):
        try:
            return self.d.get_log("logcat")
        except WebDriverException:
            return []

    def errores_nuevos(self) -> list:
        """Crashes (FATAL EXCEPTION) y ANR de la app desde la última consulta."""
        lineas = [e.get("message", "") for e in self._logcat()]
        errores = []
        for i, linea in enumerate(lineas):
            if "FATAL EXCEPTION" in linea:
                bloque = " | ".join(lineas[i:i + 6])
                if self.paquete in bloque:
                    errores.append(bloque[:600])
            elif re.search(rf"ANR in {re.escape(self.paquete)}", linea):
                errores.append(linea[:600])
        return errores

    # ---------- acciones ----------
    def clickeables(self, maximo=None) -> list:
        """Elementos tocables visibles de la app, con texto o descripción."""
        try:
            els = self.d.find_elements(AppiumBy.XPATH, "//*[@clickable='true' and @displayed='true']")
        except WebDriverException:
            return []
        utiles = [e for e in els if self.etiqueta(e)]
        return utiles[:maximo] if maximo else utiles

    @staticmethod
    def etiqueta(el) -> str:
        for attr in ("text", "content-desc", "resource-id"):
            try:
                v = (el.get_attribute(attr) or "").strip()
            except WebDriverException:
                v = ""
            if v and v.lower() not in ("null", "none"):
                return v.split("/")[-1] if attr == "resource-id" else v
        return ""

    def volver_a_la_app(self):
        if not self.en_primer_plano():
            self.d.activate_app(self.paquete)
            self.esperar_primer_plano()

    # La pantalla inicial se reconoce por sus elementos tocables (sirve también para apps
    # de una sola actividad, donde todas las pantallas comparten la misma Activity).
    def firma(self) -> set:
        return {self.etiqueta(e) for e in self.clickeables()}

    def marcar_inicio(self):
        self.firma_inicio = self.firma()

    def en_inicio(self) -> bool:
        base = getattr(self, "firma_inicio", set())
        if not base:
            try:
                return self.d.current_activity == self.actividad_inicial
            except WebDriverException:            # iOS no tiene actividades
                return False
        return len(self.firma() & base) >= 0.7 * len(base)

    def volver_al_inicio(self, max_atras=4) -> bool:
        self.volver_a_la_app()
        for _ in range(max_atras):
            if self.en_inicio():
                return True
            try:
                self.d.back()                      # botón atrás por software (Android)
            except WebDriverException:
                break                               # iOS no tiene botón atrás de hardware/software genérico
            time.sleep(1.5)
            self.volver_a_la_app()
        return self.en_inicio()

    def reiniciar(self) -> float:
        """Cierra la app y la abre en frío. Devuelve los segundos hasta que muestra contenido."""
        self.d.terminate_app(self.paquete)
        time.sleep(1)
        inicio = time.time()
        self.d.activate_app(self.paquete)
        self.esperar_primer_plano()
        self.esperar_contenido(timeout=30)
        return round(time.time() - inicio, 2)

    def reiniciar_limpio(self) -> float:
        """Como reiniciar(), pero antes borra los datos/preferencias de la app (equivalente a
        `pm clear`), para simular de verdad una app recién instalada (onboarding, tooltips de
        "primera vez", banners que dependen de un flag persistido, etc). El driver corre en el
        mismo dispositivo físico entre corridas, así que sin este borrado un flag de "usuario ya
        vio esto" queda pegado para siempre y esos escenarios dejan de poder probarse.
        Usa la extensión "mobile: clearApp" del driver (no requiere --allow-insecure); en drivers
        que no la soportan (ej. iOS todavía sin este caso de uso) hace un reinicio normal."""
        try:
            self.d.execute_script("mobile: clearApp", {"appId": self.paquete})
        except WebDriverException:
            pass  # driver sin soporte para limpiar datos: seguimos con un reinicio normal
        return self.reiniciar()

    # ---------- búsqueda por texto y zonas de pantalla ----------
    def buscar(self, texto) -> list:
        """Elementos visibles cuyo texto o descripción de accesibilidad contiene `texto`."""
        xp = (f"//*[@displayed='true' and (contains(@text,{texto!r}) or contains(@content-desc,{texto!r}))]")
        try:
            return self.d.find_elements(AppiumBy.XPATH, xp)
        except WebDriverException:
            return []

    def _zona(self, desde, hasta) -> list:
        """Elementos tocables con etiqueta cuya posición vertical está entre `desde` y `hasta` (0 a 1)."""
        alto = self.d.get_window_size()["height"]
        items = []
        for e in self.clickeables():
            r = e.rect
            centro = (r["y"] + r["height"] / 2) / alto
            if desde <= centro <= hasta:
                items.append({"etiqueta": self.etiqueta(e), "x": r["x"],
                              "seleccionado": (e.get_attribute("selected") or "false") == "true", "el": e})
        return sorted(items, key=lambda i: i["x"])

    def navbar(self) -> list:
        """Botones de la barra de navegación inferior, de izquierda a derecha."""
        return self._zona(0.85, 1.0)

    def topbar(self) -> list:
        """Elementos tocables de la barra superior."""
        return self._zona(0.0, 0.12)

    # ---------- evidencias ----------
    def captura(self, caso, paso, descripcion):
        ruta = self.salida / "evidencias" / f"{caso}_{paso}.png"
        self.d.get_screenshot_as_file(str(ruta))
        return {"archivo": ruta.name, "descripcion": descripcion}

    def grabar(self) -> bool:
        try:
            self.d.start_recording_screen(timeLimit="180", forceRestart=True)
            return True
        except WebDriverException:
            return False

    def detener_grabacion(self, nombre):
        try:
            ruta = self.salida / "evidencias" / f"{nombre}.mp4"
            ruta.write_bytes(base64.b64decode(self.d.stop_recording_screen()))
            return ruta.name
        except WebDriverException:
            return None
