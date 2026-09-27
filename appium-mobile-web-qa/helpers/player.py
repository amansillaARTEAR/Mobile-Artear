"""Acciones y mediciones sobre el player de videos verticales, en dispositivo real vía Appium."""
import base64
import time

from selenium.webdriver.common.by import By

import config

# Estado del slide activo, leído dentro de la página
JS_SNAP = r"""
const f = document.querySelector('.feed'); if (!f) return null;
const a = f.querySelector('.slide.active'); const v = a && a.querySelector('video');
const bar = a && a.querySelector('.progress-bar-fill'); const bx = v && v.getBoundingClientRect();
return {
  tab: (document.querySelector('.tab.active') || {}).innerText || '',
  idx: [...f.children].indexOf(a), total: f.children.length,
  fin: !!a && (a.innerText || '').includes('terminaste'),
  video: location.pathname.split('/').filter(Boolean).pop(),
  reproduciendo: v ? !v.paused : null, muteado: v ? v.muted : null,
  t: v ? v.currentTime : null, d: v ? v.duration : null,
  ancho_video: v ? v.videoWidth : null, alto_video: v ? v.videoHeight : null,
  barra: bar ? parseFloat(bar.style.width) : null,
  ratio: bx && bx.height ? bx.width / bx.height : null,
  tiene_video: !!(a && a.querySelector('video, genoa-player')),
  placeholders: document.querySelectorAll('[class*=placeholder i]:not(.vjs-icon-placeholder),[class*=skeleton i]').length,
  sonando: [...document.querySelectorAll('video')].filter(x => !x.paused).length,
  version: (window.Fusion || {}).deployment || null,
  url: location.href
};
"""

# Campos configurados en PageBuilder para el componente
JS_CONFIG = r"""
function w(n){ if(!n) return null;
  if (n.props && n.props.customFields && n.props.customFields.id_importante !== undefined) return n.props.customFields;
  for (const c of (n.children || [])) { const r = w(c); if (r) return r; } return null; }
return w((window.Fusion || {}).tree);
"""

# Contenido de una colección (orden y fechas)
JS_COLECCION = r"""
const done = arguments[arguments.length - 1]; const id = arguments[0];
const q = encodeURIComponent(JSON.stringify({collectionId: id, from: 0, size: 50}));
fetch(`/pf/api/v3/content/fetch/websked-collection?query=${q}&d=${Fusion.deployment}&_website=tn`)
  .then(r => r.json())
  .then(d => done((d.content_elements || []).map(e => ({
      slug: (e.canonical_url || e.website_url || '').split('/').filter(Boolean).pop(),
      fecha: e.display_date, titulo: (e.headlines || {}).basic }))))
  .catch(e => done({error: String(e)}));
"""

# Controles visibles fuera del reproductor
JS_CONTROLES = r"""
return [...document.querySelectorAll('button,a')]
  .filter(b => !b.closest('.video-js') && b.offsetParent)
  .map(b => b.getAttribute('aria-label') || (b.innerText || '').trim()).filter(Boolean);
"""

# Etiqueta amarilla con el caso y los valores medidos, visible en la captura
JS_ETIQUETA = r"""
let d = document.getElementById('__qa');
if (!d) { d = document.createElement('div'); d.id = '__qa';
  d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483647;background:rgba(255,235,59,.95);' +
    'color:#000;font:bold 11px/1.3 Arial;padding:4px 6px;pointer-events:none;white-space:pre-wrap';
  document.body.appendChild(d); }
d.textContent = 'QA TNARC-4366 · d=' + ((window.Fusion || {}).deployment || '?') + ' · ' + arguments[0];
"""

JS_IR_AL_FINAL = r"""
const v = document.querySelector('.slide.active video'); v.currentTime = Math.max(0, v.duration - 2); return v.duration;
"""


class Player:
    def __init__(self, driver, plataforma, salida):
        self.d = driver
        self.plataforma = plataforma
        self.salida = salida
        self.historial = []
        self._cfg = None
        self._col = {}
        driver.set_script_timeout(30)
        ctx = driver.current_context
        if ctx == "NATIVE_APP":
            ctx = [c for c in driver.contexts if c != "NATIVE_APP"][-1]
            driver.switch_to.context(ctx)
        self.web_ctx = ctx

    # ---------- contextos ----------
    def _web(self):
        if self.d.current_context != "NATIVE_APP":
            return
        ctxs = [c for c in self.d.contexts if c != "NATIVE_APP"]
        destino = self.web_ctx if self.web_ctx in ctxs else ctxs[-1]
        self.d.switch_to.context(destino)
        self.web_ctx = destino

    def _nativo(self):
        if self.d.current_context != "NATIVE_APP":
            self.web_ctx = self.d.current_context
            self.d.switch_to.context("NATIVE_APP")

    # ---------- lectura de estado ----------
    def snap(self):
        self._web()
        s = self.d.execute_script(JS_SNAP)
        if s:
            s["tab"] = (s.get("tab") or "").strip()
            self.historial.append(s)
        return s

    def esperar(self, condicion, timeout=20, intervalo=0.5):
        limite = time.time() + timeout
        s = None
        while time.time() < limite:
            try:
                s = self.snap()
            except Exception:
                s = None
            if s and condicion(s):
                return s
            time.sleep(intervalo)
        return s

    def config(self):
        if self._cfg is None:
            self._web()
            self._cfg = self.d.execute_script(JS_CONFIG)
            assert self._cfg, "No se encontró la configuración del componente en la página"
        return self._cfg

    def coleccion(self, campo):
        if campo not in self._col:
            self._web()
            r = self.d.execute_async_script(JS_COLECCION, self.config()[campo])
            assert not (isinstance(r, dict) and r.get("error")), f"Error al leer la colección: {r}"
            self._col[campo] = r
        return self._col[campo]

    def controles_visibles(self):
        self._web()
        return self.d.execute_script(JS_CONTROLES)

    def url_actual(self):
        self._web()
        return self.d.current_url

    # ---------- acciones ----------
    def abrir(self):
        """Carga el player desde cero y espera a que el primer video esté reproduciéndose."""
        self._web()
        self.d.get(config.URL)
        return self.esperar(lambda s: s["reproduciendo"] and (s["t"] or 0) > 0.5, timeout=30)

    def tocar(self, css, espera=1.5, forzar_nativo=False):
        self._web()
        el = self.d.find_element(By.CSS_SELECTOR, css)
        if self.plataforma == "ios" and not forzar_nativo:
            # En iOS, la barra superior de Safari se muestra/oculta dinámicamente y puede
            # desfasar la coordenada del toque táctil simulado. Disparamos el clic directo
            # sobre el elemento para evitar el desfasaje.
            self.d.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", el)
        else:
            # Toque táctil real (necesario, por ejemplo, para acciones que reproducen audio:
            # Safari solo lo permite si viene de un toque genuino, no de un clic por JavaScript).
            el.click()
        time.sleep(espera)

    def tocar_video(self):
        self.tocar(".slide.active .video-js")
        return self.snap()

    def pestana(self, nombre):
        self._web()
        for el in self.d.find_elements(By.CSS_SELECTOR, ".tab"):
            if el.text.strip() == nombre:
                el.click()
                time.sleep(2.5)
                return self.snap()
        raise AssertionError(f"No se encontró la pestaña «{nombre}»")

    def ir_al_final_del_video(self):
        self._web()
        return self.d.execute_script(JS_IR_AL_FINAL)

    def swipe(self, intenso=False, hacia="siguiente"):
        """Gesto táctil nativo sobre el dispositivo. intenso=True hace un fling rápido."""
        direccion = "up" if hacia == "siguiente" else "down"
        self._nativo()
        try:
            if self.plataforma == "android":
                w = self.d.get_window_size()
                area = {"left": int(w["width"] * 0.25), "top": int(w["height"] * 0.3),
                        "width": int(w["width"] * 0.5), "height": int(w["height"] * 0.4)}
                if intenso:
                    # En UiAutomator2 el fling indica hacia dónde se desplaza el contenido:
                    # "down" = avanzar al siguiente video (el dedo va hacia arriba).
                    sentido = "down" if hacia == "siguiente" else "up"
                    self.d.execute_script("mobile: flingGesture",
                                          {**area, "direction": sentido, "speed": 15000})
                else:
                    self.d.execute_script("mobile: swipeGesture",
                                          {**area, "direction": direccion, "percent": 0.6, "speed": 2500})
            else:
                self.d.execute_script("mobile: swipe",
                                      {"direction": direccion, "velocity": 10000 if intenso else 1500})
        finally:
            self._web()
        time.sleep(2.5)
        return self.snap()

    def cerrar_hoja_compartir(self):
        """Detecta si se abrió la hoja nativa de compartir y la cierra. Devuelve True si estaba abierta."""
        abierta = False
        self._nativo()
        try:
            if self.plataforma == "android":
                abierta = self.d.current_package != "com.android.chrome"
                if abierta:
                    self.d.press_keycode(4)  # Atrás
            else:
                for nombre in ("Close", "Cerrar"):
                    els = self.d.find_elements("accessibility id", nombre)
                    if els:
                        abierta = True
                        els[0].click()
                        break
        finally:
            self._web()
        time.sleep(1.5)
        return abierta

    # ---------- evidencias ----------
    def captura(self, ca, paso, texto):
        """Guarda una captura del dispositivo (con etiqueta del caso si TN_ETIQUETAS=1)."""
        try:
            self._web()
            if config.ETIQUETAS:
                self.d.execute_script(JS_ETIQUETA, f"{ca} · {self.plataforma} · {texto}")
            else:
                self.d.execute_script("const e=document.getElementById('__qa'); if (e) e.remove();")
        except Exception:
            pass
        ruta = self.salida / "evidencias" / f"{ca}_{paso}.png"
        self._nativo()
        try:
            self.d.get_screenshot_as_file(str(ruta))
        finally:
            self._web()
        return {"archivo": ruta.name, "descripcion": texto}

    def grabar(self):
        self._nativo()
        try:
            self.d.start_recording_screen(timeLimit="180", forceRestart=True)
            return True
        except Exception:
            return False
        finally:
            self._web()

    def detener_grabacion(self, nombre):
        self._nativo()
        try:
            datos = self.d.stop_recording_screen()
            ruta = self.salida / "evidencias" / f"{nombre}.mp4"
            ruta.write_bytes(base64.b64decode(datos))
            return ruta.name
        except Exception:
            return None
        finally:
            self._web()
