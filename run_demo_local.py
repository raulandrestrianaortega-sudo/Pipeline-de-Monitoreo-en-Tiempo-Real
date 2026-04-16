#!/usr/bin/env python3
"""
Demo Local – Simulación sin Kafka
===================================
Ejecuta el pipeline completo en modo simulación local:
  • Genera lecturas de los 3 tipos de sensores
  • Aplica lógica de detección de anomalías
  • Guarda estadísticas en CSV y SQLite
  • No requiere Kafka ni Spark instalados

Ideal para demostrar el flujo de datos sin infraestructura.

Uso:
  pip install kafka-python
  python run_demo_local.py
"""

import csv
import os
import random
import sqlite3
import time
import math
from collections import defaultdict
from datetime import datetime, timezone

OUTPUT_DIR = "./output"
CSV_ESTADISTICAS = f"{OUTPUT_DIR}/estadisticas.csv"
CSV_ALERTAS = f"{OUTPUT_DIR}/alertas.csv"
SQLITE_DB = f"{OUTPUT_DIR}/monitoreo.db"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SENSORES = {
    "temperatura": {
        "ids": ["TEMP_A1", "TEMP_A2", "TEMP_B1", "TEMP_B2", "TEMP_C1", "TEMP_C2"],
        "lineas": ["LINEA_A", "LINEA_A", "LINEA_B", "LINEA_B", "LINEA_C", "LINEA_C"],
        "media": 72.0, "desv": 8.0, "unidad": "°C",
        "max_alerta": 90.0, "max_critico": 100.0, "min_alerta": 50.0,
    },
    "presion": {
        "ids": ["PRES_A1", "PRES_A2", "PRES_B1", "PRES_B2", "PRES_C1", "PRES_C2"],
        "lineas": ["LINEA_A", "LINEA_A", "LINEA_B", "LINEA_B", "LINEA_C", "LINEA_C"],
        "media": 6.0, "desv": 1.0, "unidad": "bar",
        "max_alerta": 9.0, "max_critico": 10.5, "min_alerta": 3.0,
    },
    "vibracion": {
        "ids": ["VIB_A1", "VIB_A2", "VIB_B1", "VIB_B2", "VIB_C1", "VIB_C2"],
        "lineas": ["LINEA_A", "LINEA_A", "LINEA_B", "LINEA_B", "LINEA_C", "LINEA_C"],
        "media": 2.5, "desv": 0.8, "unidad": "mm/s",
        "max_alerta": 5.5, "max_critico": 7.0, "min_alerta": 0.1,
    },
}

buffer: defaultdict = defaultdict(list)  # sensor_id -> [valores últimos 60s]
ciclo = defaultdict(int)


def init_db():
    conn = sqlite3.connect(SQLITE_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS estadisticas_ventana (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        window_start TEXT, window_end TEXT,
        sensor_id TEXT, linea TEXT, tipo_sensor TEXT, unidad TEXT,
        promedio REAL, minimo REAL, maximo REAL, desviacion_std REAL, total_lecturas INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, sensor_id TEXT, linea TEXT, tipo_sensor TEXT,
        valor REAL, unidad TEXT, nivel TEXT, mensaje TEXT
    )""")
    conn.commit()
    conn.close()


def generar_valor(tipo: str, sid: str) -> float:
    cfg = SENSORES[tipo]
    ciclo[sid] += 1
    if tipo == "vibracion":
        base = cfg["media"] + 1.5 * math.sin(ciclo[sid] * 0.1)
    else:
        base = cfg["media"]
    valor = base + random.gauss(0, cfg["desv"] * 0.3)
    if random.random() < 0.05:
        spikes = [cfg["max_alerta"] * 1.05, cfg["max_critico"] * 1.02, cfg["min_alerta"] * 0.85]
        valor = random.choice(spikes)
    return round(valor, 3)


def evaluar(tipo: str, valor: float, cfg: dict):
    if valor >= cfg["max_critico"]:
        return "CRITICO", f"Valor crítico {valor} >= {cfg['max_critico']}"
    if valor >= cfg["max_alerta"]:
        return "ALTO", f"Valor alto {valor} >= {cfg['max_alerta']}"
    if valor <= cfg["min_alerta"]:
        return "BAJO", f"Valor bajo {valor} <= {cfg['min_alerta']}"
    return None, ""


def guardar_alerta(ts, sid, linea, tipo, valor, unidad, nivel, msg):
    existe = os.path.isfile(CSV_ALERTAS)
    with open(CSV_ALERTAS, "a", newline="") as f:
        w = csv.writer(f)
        if not existe:
            w.writerow(["timestamp","sensor_id","linea","tipo_sensor","valor","unidad","nivel","mensaje"])
        w.writerow([ts, sid, linea, tipo, valor, unidad, nivel, msg])
    conn = sqlite3.connect(SQLITE_DB)
    conn.execute("INSERT INTO alertas (timestamp,sensor_id,linea,tipo_sensor,valor,unidad,nivel,mensaje) VALUES(?,?,?,?,?,?,?,?)",
                 (ts, sid, linea, tipo, valor, unidad, nivel, msg))
    conn.commit(); conn.close()


def guardar_estadisticas(ws, we, sid, linea, tipo, unidad, valores):
    import statistics
    prom = round(statistics.mean(valores), 3)
    mn   = round(min(valores), 3)
    mx   = round(max(valores), 3)
    std  = round(statistics.stdev(valores), 3) if len(valores) > 1 else 0.0
    n    = len(valores)

    existe = os.path.isfile(CSV_ESTADISTICAS)
    with open(CSV_ESTADISTICAS, "a", newline="") as f:
        w = csv.writer(f)
        if not existe:
            w.writerow(["window_start","window_end","sensor_id","linea","tipo_sensor","unidad","promedio","minimo","maximo","desviacion_std","total_lecturas"])
        w.writerow([ws, we, sid, linea, tipo, unidad, prom, mn, mx, std, n])

    conn = sqlite3.connect(SQLITE_DB)
    conn.execute("""INSERT INTO estadisticas_ventana
        (window_start,window_end,sensor_id,linea,tipo_sensor,unidad,promedio,minimo,maximo,desviacion_std,total_lecturas)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (ws, we, sid, linea, tipo, unidad, prom, mn, mx, std, n))
    conn.commit(); conn.close()

    print(f"\n  📊  VENTANA {ws[11:19]}→{we[11:19]}  {sid:10s} | prom={prom:7.3f}  min={mn:7.3f}  max={mx:7.3f}  std={std:.3f}  n={n}")


def main():
    print("🏭  DEMO LOCAL – Pipeline de Monitoreo Industrial")
    print("=" * 60)
    print("  Sin Kafka/Spark – Simulación directa en Python")
    print(f"  Salida en: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)
    init_db()

    segundo = 0
    ventana_inicio = datetime.now(timezone.utc)

    try:
        while True:
            segundo += 1
            ts = datetime.now(timezone.utc).isoformat()

            for tipo, cfg in SENSORES.items():
                for sid, linea in zip(cfg["ids"], cfg["lineas"]):
                    valor = generar_valor(tipo, sid)
                    buffer[sid].append(valor)

                    nivel, msg = evaluar(tipo, valor, cfg)
                    if nivel:
                        icono = {"CRITICO": "🔴", "ALTO": "🟠", "BAJO": "🔵"}[nivel]
                        print(f"  {icono} [{nivel:7s}] {sid:10s} ({linea}) {valor:7.3f} {cfg['unidad']}  {msg}")
                        guardar_alerta(ts, sid, linea, tipo, valor, cfg["unidad"], nivel, msg)

            # Cada 60 segundos: calcular ventana
            if segundo % 60 == 0:
                ventana_fin = datetime.now(timezone.utc)
                ws = ventana_inicio.isoformat()
                we = ventana_fin.isoformat()
                print(f"\n{'─'*60}")
                print(f"  ⏱️  PROCESANDO VENTANA #{segundo//60}")
                for tipo, cfg in SENSORES.items():
                    for sid, linea in zip(cfg["ids"], cfg["lineas"]):
                        if buffer[sid]:
                            guardar_estadisticas(ws, we, sid, linea, tipo, cfg["unidad"], buffer[sid])
                            buffer[sid].clear()
                ventana_inicio = ventana_fin
                print(f"{'─'*60}\n")
            elif segundo % 10 == 0:
                print(f"  ⏳  t={segundo}s  (próxima ventana en {60 - segundo % 60}s)")

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n🛑 Demo detenida en t={segundo}s")
        print(f"📁  Revisa los archivos en: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
