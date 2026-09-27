<#
  Corre la suite de app nativa con un solo comando.

    .\correr.ps1                                     Android, APK más reciente de apks\, celular local
    .\correr.ps1 -Apk "C:\Descargas\app-qa.apk"      Android, un APK puntual
    .\correr.ps1 -Filtro "test_01 or test_02"        solo algunos casos
    .\correr.ps1 -Plataforma ios                      iOS vía AWS Device Farm (ver abajo)

  Android: detecta el celular por USB, inicia Appium local si hace falta, instala la app,
  corre las pruebas, cierra Appium y abre el reporte.

  iOS (AWS Device Farm): no usa celular ni Appium local. Necesita, antes de correr:
    $env:APPIUM_URL = "https://<endpoint-de-la-sesion-de-device-farm>/wd/hub"
    (opcional) $env:IOS_DEVICE, $env:IOS_VERSION si el proveedor los pide
  y un .ipa en la carpeta ipas\ (o -App "C:\ruta\app.ipa").
#>
param(
    [string]$Apk = "",
    [string]$App = "",
    [ValidateSet("android", "ios")]
    [string]$Plataforma = "android",
    [string]$Filtro = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-Appium {
    try { $c = [Net.Sockets.TcpClient]::new(); $c.Connect("127.0.0.1", 4723); $c.Close(); return $true }
    catch { return $false }
}

$npmBin = Join-Path $env:APPDATA "npm"
if ($env:Path -notlike "*$npmBin*") { $env:Path += ";$npmBin" }

$env:TN_PLATAFORMA = $Plataforma

# App a probar (Android: .apk / iOS: .ipa). -App admite cualquiera de las dos plataformas;
# -Apk queda como alias por compatibilidad cuando se prueba Android.
$rutaApp = if ($App) { $App } elseif ($Apk) { $Apk } else { "" }
if ($rutaApp) {
    if (-not (Test-Path $rutaApp)) { Write-Host "No existe la app: $rutaApp" -ForegroundColor Red; exit 1 }
    $env:TN_APP = (Resolve-Path $rutaApp).Path
} else {
    Remove-Item Env:TN_APP -ErrorAction SilentlyContinue
    $carpeta = if ($Plataforma -eq "ios") { "ipas\*.ipa" } else { "apks\*.apk" }
    $ultimo = Get-ChildItem $carpeta -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $ultimo) {
        $carpetaNombre = if ($Plataforma -eq "ios") { "ipas\" } else { "apks\" }
        Write-Host "Copiá la app a probar en la carpeta $carpetaNombre o usá -App <ruta>." -ForegroundColor Red
        exit 1
    }
    Write-Host "App: $($ultimo.Name)" -ForegroundColor Cyan
}

$appium = $null

if ($Plataforma -eq "android") {
    # Celular conectado
    if (-not $env:ANDROID_UDID) {
        $linea = adb devices | Select-String "`tdevice$" | Select-Object -First 1
        if (-not $linea) {
            Write-Host "No hay ningún Android conectado. Revisá el cable y la depuración USB (adb devices)." -ForegroundColor Red
            exit 1
        }
        $env:ANDROID_UDID = ($linea.ToString() -split "`t")[0]
    }
    # Appium local si no está corriendo
    if (-not $env:APPIUM_URL -and -not (Test-Appium)) {
        Write-Host "Iniciando Appium..." -ForegroundColor Cyan
        $appium = Start-Process appium.cmd -PassThru -WindowStyle Minimized -ArgumentList "--log", "appium.log"
        $limite = (Get-Date).AddSeconds(40)
        while (-not (Test-Appium)) {
            if ((Get-Date) -gt $limite) { Write-Host "Appium no arrancó. Revisá appium.log" -ForegroundColor Red; exit 1 }
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "Dispositivo: $env:ANDROID_UDID  |  No toques el celular hasta que termine." -ForegroundColor Cyan
} else {
    # iOS: la sesión corre en AWS Device Farm, no hay celular ni Appium local
    if (-not $env:APPIUM_URL) {
        Write-Host "Falta `$env:APPIUM_URL con el endpoint de la sesión de AWS Device Farm." -ForegroundColor Red
        exit 1
    }
    Write-Host "iOS vía AWS Device Farm: $($env:APPIUM_URL)" -ForegroundColor Cyan
}

$pyArgs = @("-m", "pytest")
if ($Filtro) { $pyArgs += @("-k", $Filtro) }
try {
    & .\.venv\Scripts\python.exe @pyArgs
    $codigo = $LASTEXITCODE
}
finally {
    if ($appium) { taskkill /PID $appium.Id /T /F | Out-Null }
}

$ultima = Get-ChildItem "resultados\$Plataforma\corridas" -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
if ($ultima -and (Test-Path (Join-Path $ultima.FullName "reporte.html"))) {
    Start-Process (Join-Path $ultima.FullName "reporte.html")
}
exit $codigo
