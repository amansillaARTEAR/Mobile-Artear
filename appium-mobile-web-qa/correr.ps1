<#
  Corre la suite con un solo comando.
    .\correr.ps1                        suite completa en Android
    .\correr.ps1 -Filtro "ca03 or ca07" solo algunos casos
    .\correr.ps1 -Plataforma ios        iOS (requiere APPIUM_URL de la granja en la nube)
  Detecta el celular conectado, inicia Appium si hace falta, corre pytest,
  cierra Appium al terminar y abre el reporte.
#>
param(
    [ValidateSet("android", "ios")][string]$Plataforma = "android",
    [string]$Filtro = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-Appium {
    try { $c = [Net.Sockets.TcpClient]::new(); $c.Connect("127.0.0.1", 4723); $c.Close(); return $true }
    catch { return $false }
}

# 1. Appium instalado con npm: su carpeta tiene que estar en el PATH
$npmBin = Join-Path $env:APPDATA "npm"
if ($env:Path -notlike "*$npmBin*") { $env:Path += ";$npmBin" }

# 2. Celular Android conectado por USB
if ($Plataforma -eq "android" -and -not $env:ANDROID_UDID) {
    $linea = adb devices | Select-String "`tdevice$" | Select-Object -First 1
    if (-not $linea) {
        Write-Host "No hay ningún Android conectado. Revisá el cable y la depuración USB (adb devices)." -ForegroundColor Red
        exit 1
    }
    $env:ANDROID_UDID = ($linea.ToString() -split "`t")[0]
}
if ($Plataforma -eq "ios" -and -not $env:APPIUM_URL) {
    Write-Host "Para iOS configurá APPIUM_URL con el endpoint de la granja en la nube (ver README)." -ForegroundColor Red
    exit 1
}

# 3. Appium local (solo si no se usa un endpoint remoto y no está corriendo ya)
$appium = $null
if (-not $env:APPIUM_URL -and -not (Test-Appium)) {
    Write-Host "Iniciando Appium..." -ForegroundColor Cyan
    $appium = Start-Process appium.cmd -PassThru -WindowStyle Minimized `
        -ArgumentList "--allow-insecure=uiautomator2:chromedriver_autodownload", "--log", "appium.log"
    $limite = (Get-Date).AddSeconds(40)
    while (-not (Test-Appium)) {
        if ((Get-Date) -gt $limite) { Write-Host "Appium no arrancó. Revisá appium.log" -ForegroundColor Red; exit 1 }
        Start-Sleep -Seconds 1
    }
}

# 4. Pruebas
$pyArgs = @("-m", "pytest", "--plataforma", $Plataforma)
if ($Filtro) { $pyArgs += @("-k", $Filtro) }
Write-Host "Dispositivo: $env:ANDROID_UDID  |  Plataforma: $Plataforma  |  No toques el celular hasta que termine." -ForegroundColor Cyan
try {
    & .\.venv\Scripts\python.exe @pyArgs
    $codigo = $LASTEXITCODE
}
finally {
    if ($appium) { taskkill /PID $appium.Id /T /F | Out-Null }   # cierra Appium y sus procesos
}

# 5. Abrir el reporte de la corrida
$ultima = Get-ChildItem "resultados\$Plataforma\corridas" -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
if ($ultima -and (Test-Path (Join-Path $ultima.FullName "reporte.html"))) {
    Start-Process (Join-Path $ultima.FullName "reporte.html")
}
exit $codigo
