"""Borra los resultados, reportes e informes con más de 48 horas (configurable).

Solo actúa dentro de la carpeta `resultados` de este proyecto:
  resultados/android/corridas/<fecha-hora>/   reporte.html, resultados.json, evidencias
  resultados/android/informes/                informes Word de Android
  resultados/ios/corridas/<fecha-hora>/
  resultados/ios/informes/

Uso:
  python limpieza.py            borra lo vencido
  python limpieza.py --simular  solo muestra qué borraría
Variable opcional: TN_RETENCION_HORAS (por defecto 48).
"""
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent / "resultados"
HORAS = float(os.getenv("TN_RETENCION_HORAS", "48"))


def _antiguedad_horas(ruta: Path) -> float:
    """Horas desde que se creó la corrida (por el nombre fecha-hora) o desde la última modificación."""
    try:
        creado = datetime.strptime(ruta.name, "%Y%m%d-%H%M%S").timestamp()
    except ValueError:
        creado = ruta.stat().st_mtime
    return (time.time() - creado) / 3600


def limpiar(simular: bool = False, horas: float = HORAS) -> list:
    borrados = []
    if not RAIZ.is_dir():
        return borrados
    candidatos = []
    for plataforma in RAIZ.iterdir():                    # android, ios
        if not plataforma.is_dir():
            continue
        for sub in plataforma.iterdir():
            if sub.is_dir() and sub.name in ("corridas", "informes"):
                candidatos.extend(sub.iterdir())         # cada corrida o informe
            else:
                candidatos.append(sub)                   # estructura anterior
    for item in candidatos:
            try:
                if _antiguedad_horas(item) < horas:
                    continue
                if not simular:
                    shutil.rmtree(item) if item.is_dir() else item.unlink()
                borrados.append(str(item.relative_to(RAIZ)))
            except OSError as e:             # archivo abierto (ej. informe en Word): se reintenta en la próxima
                print(f"No se pudo borrar {item}: {e}")
    return borrados


if __name__ == "__main__":
    simular = "--simular" in sys.argv
    items = limpiar(simular=simular)
    accion = "Se borrarían" if simular else "Borrados"
    print(f"{accion} ({len(items)}), más de {HORAS:g} h:" if items else f"Nada con más de {HORAS:g} h.")
    for i in items:
        print("  -", i)
