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
        self.cerrar_dialogo_permisos()  # por si la app lo pide ya al primer arranque de la sesión

    # ---------- estado ----------
    def en_primer_plano(self) -> bool:
        return self.d.query_app_state(self.paquete) == EN_PRIMER_PLANO

    def esperar_primer_plano(self, timeout=20) -> bool:
        limite = time.time() + timeout
        while time.time() < limite:
            if self.en_primer_plano():
                self.cerrar_dialogo_permisos()
                return True
            time.sleep(0.5)
        return False

    def cerrar_dialogo_permisos(self, permitir=True) -> bool:
        """Si hay un diálogo nativo de Android pidiendo un permiso (notificaciones, ubicación,
        etc.), lo resuelve tocando "Permitir" (o "No permitir" si permitir=False) y devuelve
        True. Si no hay ninguno, no hace nada y devuelve False.

        Este diálogo lo dibuja el sistema (no la app que se está probando), por eso
        terminate_app/activate_app NO lo cierran solos, y si queda sin resolver se queda
        pegado en pantalla -- incluso se ve por encima del launcher si la app se cierra con el
        diálogo todavía abierto -- tapando cualquier elemento que un test busque después.

        NO filtramos por @package: según el fabricante/ROM el diálogo lo puede dibujar
        com.android.permissioncontroller, un paquete propio del fabricante, o directamente
        "android" -- filtrar por uno de esos nombres puede no matchear en otro dispositivo.
        El texto del botón es la parte estable."""
        # Contempla el dispositivo en español ("Permitir"/"No permitir") y por si algún día
        # corre con el idioma del sistema en inglés ("Allow"/"Don't allow") -- sin distinguir
        # mayúsculas/minúsculas, porque algunos fabricantes lo muestran en versalitas.
        # Igualdad exacta (no contains): "permitir" es substring de "no permitir", así que un
        # contains() con permitir=True terminaría matcheando también el botón "No permitir".
        textos = ["permitir", "allow"] if permitir else ["no permitir", "don't allow", "deny"]
        condicion = " or ".join(
            f"translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
            f"'abcdefghijklmnopqrstuvwxyzáéíóú')={t!r}"
            for t in textos)
        try:
            botones = self.d.find_elements(AppiumBy.XPATH, f"//*[@clickable='true' and ({condicion})]")
        except WebDriverException:
            return False
        if not botones:
            return False
        try:
            botones[0].click()
            time.sleep(1)
        except WebDriverException:
            return False
        return True

    def esperar_contenido(self, timeout=20) -> bool:
        """Espera a que la pantalla tenga al menos un elemento tocable. Si en el medio aparece
        el diálogo de permisos (puede pedirse con un pequeño delay tras el arranque), lo cierra
        para no quedarse esperando contenido que el diálogo está tapando."""
        limite = time.time() + timeout
        while time.time() < limite:
            self.cerrar_dialogo_permisos()
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
        """Elementos tocables visibles de la app, con texto o descripción.

        El diálogo de permisos de Android (ver cerrar_dialogo_permisos) puede aparecer con
        cierto delay después del arranque, en cualquier momento de un test -- no solo justo
        al reiniciar. Como clickeables() es el método que prácticamente todo lo demás usa
        para "mirar la pantalla" (navbar, topbar, buscar, los tests generados), resolverlo
        acá antes de leer la pantalla es lo que lo cubre de verdad, en vez de solo en el
        momento del reinicio."""
        self.cerrar_dialogo_permisos()
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

    def scroll(self, direccion="down", porcentaje=0.6) -> bool:
        """Desliza la pantalla con un gesto nativo (no depende de qué elemento haya debajo,
        a diferencia de arrastrar un elemento puntual). direccion="down" revela contenido
        más abajo (el dedo sube en pantalla); "up" al revés. Usa la extensión
        "mobile: swipeGesture" del driver (como "mobile: clearApp" en reiniciar_limpio(),
        no requiere --allow-insecure); si el driver no la soporta (ej. iOS todavía sin este
        caso de uso) no hace nada y devuelve False."""
        size = self.d.get_window_size()
        try:
            self.d.execute_script("mobile: swipeGesture", {
                "left": int(size["width"] * 0.1), "top": int(size["height"] * 0.2),
                "width": int(size["width"] * 0.8), "height": int(size["height"] * 0.6),
                "direction": direccion, "percent": porcentaje,
            })
            return True
        except WebDriverException:
            return False

    # ---------- búsqueda por texto y zonas de pantalla ----------
    def buscar(self, texto) -> list:
        """Elementos visibles cuyo texto o descripción de accesibilidad contiene `texto`.

        A diferencia de lo que decía el comentario de clickeables(), buscar() NO pasaba por
        ahí -- arma su propio XPath directo contra el driver. Eso significa que el diálogo
        de permisos de Android podía quedar tapando la pantalla y buscar() nunca lo
        resolvía, haciendo fallar cualquier detección basada en buscar() (ej. el tooltip de
        AMR-2087) aunque el elemento buscado sí estuviera ahí abajo del diálogo."""
        self.cerrar_dialogo_permisos()
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
