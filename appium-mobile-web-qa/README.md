# Suite Appium · TNARC-4366 (Videos verticales)

Valida los 13 criterios de aceptación del ticket en un **dispositivo real**, con un test por CA,
captura de pantalla en cada paso y un `resultados.json` con lo medido.

## 1. Instalación (una sola vez, en Windows)

1. **Python 3.10 o superior**: https://www.python.org (marcá "Add Python to PATH").
2. **Node.js LTS**: https://nodejs.org
3. **Java JDK 17** (por ejemplo Eclipse Temurin). Creá la variable de entorno `JAVA_HOME` apuntando a la carpeta del JDK.
4. **Android SDK**: instalá Android Studio (o solo las "command-line tools") y creá la variable
   `ANDROID_HOME` apuntando a la carpeta del SDK (normalmente `C:\Users\<usuario>\AppData\Local\Android\Sdk`).
   Agregá `%ANDROID_HOME%\platform-tools` al `PATH`.
5. **Appium y el driver de Android**, en una terminal:
   ```
   npm install -g appium
   appium driver install uiautomator2
   appium driver doctor uiautomator2
   ```
   El último comando revisa que todo esté bien configurado. Corregí lo que marque como obligatorio.
6. **Dependencias de Python**, dentro de esta carpeta:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## 2. Antes de cada ejecución (Android)

1. Conectá el celular por USB con la **depuración USB activa** y desbloqueado.
2. Poné el **bloqueo de pantalla automático en 10 minutos o más** (Ajustes → Pantalla → Tiempo de espera).
3. Cerrá la ventana de **inspect** de `chrome://inspect` si la tenés abierta.
4. Verificá el número de serie con `adb devices` y configuralo:
   ```
   $env:ANDROID_UDID = "R5CT70JC25E"
   ```
5. En **otra terminal**, iniciá Appium y dejala abierta:
   ```
   appium --allow-insecure=uiautomator2:chromedriver_autodownload
   ```
   (Con Appium 2 el parámetro es `--allow-insecure chromedriver_autodownload`.)

## 3. Ejecutar

Con el celular conectado y desbloqueado, en la terminal (dentro de esta carpeta):
```
.\correr.ps1                          # suite completa en Android
.\correr.ps1 -Filtro "ca03 or ca07"   # solo algunos casos
```
El script detecta el celular, inicia Appium si no está corriendo, ejecuta las pruebas, cierra Appium y abre el reporte.
No toques el celular mientras corre (unos 5 minutos).

Ejecución manual (equivalente): Appium en una terminal con
`appium.cmd --allow-insecure=uiautomator2:chromedriver_autodownload` y en otra
`.venv\Scripts\Activate.ps1`, `$env:ANDROID_UDID = "R5CT70JC25E"` y `pytest --plataforma android`.

## 4. Resultados

Todo queda dentro de `resultados\`, separado por plataforma:
```
resultados\
├── android\
│   ├── corridas\<fecha-hora>\   reporte.html, resultados.json y evidencias\
│   └── informes\                 informes Word de Android
└── ios\
    ├── corridas\<fecha-hora>\
    └── informes\
```
En `reporte.html` tocá "Show all details" para ver lo medido y las capturas de cada CA.

### Retención: se borra todo a las 48 horas
`limpieza.py` elimina las corridas e informes con más de 48 horas. Se ejecuta:
- automáticamente al iniciar cada `pytest`, y
- cada hora con la tarea programada de Windows (ver abajo), aunque no corras la suite.

Guardá en Jira lo que necesites conservar antes de las 48 horas. Para cambiar el plazo: variable `TN_RETENCION_HORAS`.
Para ver qué se borraría sin borrar nada: `python limpieza.py --simular`.

Crear la tarea programada (una sola vez, en PowerShell):
```
$accion = New-ScheduledTaskAction -Execute "D:\Artear\appium-mobile-web-qa\.venv\Scripts\pythonw.exe" -Argument '"D:\Artear\appium-mobile-web-qa\limpieza.py"' -WorkingDirectory "D:\Artear\appium-mobile-web-qa"
$disparador = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "Artear - limpieza resultados Appium" -Action $accion -Trigger $disparador -Description "Borra resultados de la suite Appium con mas de 48 h" -Force
```
Quitarla: `Unregister-ScheduledTask -TaskName "Artear - limpieza resultados Appium" -Confirm:$false`

## 5. iOS (AWS Device Farm)

Appium con Safari en un iPhone requiere una Mac. Desde Windows se usa un iPhone real de AWS Device Farm:

1. En la consola de AWS Device Farm, crear una **sesión de acceso remoto** con un iPhone
   (Appium versión 3). La sesión dura hasta 150 minutos y se cobra por minuto.
2. Copiar la **URL del endpoint de Appium** que muestra la sesión.
3. En la terminal:
   ```
   $env:APPIUM_URL = "<URL del endpoint de la sesión>"
   .\correr.ps1 -Plataforma ios
   ```

Con un endpoint remoto, la suite quita las capabilities que la granja no admite (`udid`, `platformVersion`).
La granja no permite grabar pantalla desde el test (el CA7 queda sin video propio), pero Device Farm graba
toda la sesión y el video se descarga desde la consola.
Pendiente de confirmar en la primera sesión: que Device Farm permita abrir Safari con `browserName`.

## Configuración

Todo se puede cambiar con variables de entorno (ver `config.py`):
- `TN_URL`: URL del player en DEV.
- `TN_VERSION`: versión que debe estar promovida (por defecto `4743`). El test `test_00_version` falla si no coincide.
- `TN_ETIQUETAS=1`: agrega a cada captura una etiqueta con el caso y los valores medidos.
- `TN_RETENCION_HORAS`: horas que se conservan los resultados (por defecto 48).
