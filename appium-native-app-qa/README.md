# Suite Appium · Apps Android (APK)

Pruebas automatizadas de apps nativas Android sobre un **dispositivo real**. Es un proyecto aparte de la
suite web (`appium-mobile-web-qa`), con su propio entorno y resultados. Usa el mismo Appium y el mismo driver
ya instalados en la PC.

## 1. Instalación (una sola vez)

En la terminal, dentro de esta carpeta:
```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Appium, el driver UiAutomator2, Java y el SDK de Android ya quedaron instalados con la suite web.

## 2. Ejecutar

1. Copiá el APK en la carpeta `apks\` (si hay varios, se usa el más reciente).
2. Conectá el celular por USB, desbloqueado y con el tiempo de pantalla en 10 minutos o más.
3. En la terminal:
```
.\correr.ps1                                  # smoke completo con el APK más reciente
.\correr.ps1 -Apk "C:\Descargas\app-qa.apk"   # un APK puntual
.\correr.ps1 -Filtro "test_01 or test_02"     # solo algunos casos
```
El script detecta el celular, inicia Appium si hace falta, **instala el APK**, ejecuta las pruebas,
cierra Appium y abre el reporte. No toques el celular mientras corre.

La primera vez el celular puede pedir permiso para instalar el APK: aceptalo. En cada corrida la app
arranca limpia (se borran solo los datos de esta app, no de otras).

## 3. Qué prueba el smoke (`tests/test_smoke.py`)

| Caso | Qué valida |
|---|---|
| SMK-01 | El APK se instala y la app abre en primer plano con contenido |
| SMK-02 | Sigue abierta 15 s después de iniciar, sin crash ni ANR |
| SMK-03 | Arranque en frío (2 intentos) dentro de `TN_ARRANQUE_MAX` segundos (10 por defecto) |
| SMK-04 | Vuelve bien después de 5 s en segundo plano |
| SMK-05 | Rotar la pantalla no cierra la app |
| SMK-06 | Tocar los primeros elementos de la pantalla inicial no produce crashes (con grabación) |

Los crashes y ANR se detectan en el logcat del celular, filtrando por el paquete de la app.

## 4. Casos de un ticket

Copiá `tests/test_ticket_plantilla.py` como `tests/test_<ticket>.py` y completalo. Para encontrar los
identificadores de los elementos usá **Appium Inspector** (https://github.com/appium/appium-inspector)
conectado a `http://127.0.0.1:4723` con las mismas capabilities de `config.py`.

## 5. Resultados

Todo queda dentro de `resultados\`:
```
resultados\
└── android\
    ├── corridas\<fecha-hora>\   reporte.html, resultados.json y evidencias\
    └── informes\                 informes Word
```
En `reporte.html` arriba se ve el APK, el paquete, el dispositivo y el sistema; tocá "Show all details" para
ver lo medido y las capturas de cada caso.

### Retención: se borra todo a las 48 horas
`limpieza.py` elimina las corridas e informes con más de 48 horas al iniciar cada corrida.
Para que también se limpie cada hora aunque no corras la suite, creá la tarea programada (una sola vez):
```
$accion = New-ScheduledTaskAction -Execute "D:\Artear\appium-native-app-qa\.venv\Scripts\pythonw.exe" -Argument '"D:\Artear\appium-native-app-qa\limpieza.py"' -WorkingDirectory "D:\Artear\appium-native-app-qa"
$disparador = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "Artear - limpieza resultados APK" -Action $accion -Trigger $disparador -Description "Borra resultados de la suite APK con mas de 48 h" -Force
```
Para ver qué se borraría: `python limpieza.py --simular`. Plazo configurable con `TN_RETENCION_HORAS`.

## Configuración (variables de entorno)
- `TN_APK`: ruta de un APK puntual (lo setea `correr.ps1 -Apk`).
- `TN_ARRANQUE_MAX`: segundos máximos aceptables de arranque en frío (10).
- `TN_EXPLORAR_N`: cantidad de elementos que toca la exploración básica (5).
- `TN_RETENCION_HORAS`: horas que se conservan los resultados (48).
- `APPIUM_URL` y `EXTRA_CAPS`: para correr en una granja en la nube (AWS Device Farm).
