# 🏭 Pipeline de Monitoreo en Tiempo Real

Sistema completo de monitoreo industrial con Kafka + Spark Streaming que simula sensores de temperatura, presión y vibración en 3 líneas de producción.

---

## 📐 Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                        PRODUCTORES KAFKA                          │
│                                                                    │
│  producer_temperatura.py ──► topic: temperatura                   │
│  producer_presion.py     ──► topic: presion      ──► Spark        │
│  producer_vibracion.py   ──► topic: vibracion        Processor   │
└──────────────────────────────────────────────────────────────────┘
                                                        │
                                    ┌───────────────────┤
                                    ▼                   ▼
                              estadisticas.csv      alertas.csv
                              monitoreo.db (SQLite)
```

### Componentes

| Servicio | Descripción |
|---|---|
| `zookeeper` | Coordinación de Kafka |
| `kafka` | Broker de mensajería |
| `kafka-init` | Crea los topics al inicio |
| `producer-temperatura` | Simula 6 sensores de temperatura (°C) |
| `producer-presion` | Simula 6 sensores de presión (bar) |
| `producer-vibracion` | Simula 6 sensores de vibración (mm/s) |
| `spark-processor` | Procesa streams con ventana tumbling de 1 min |
| `alert-monitor` | Detección de anomalías por evento en tiempo real |

---

## 🚀 Inicio Rápido (Docker)

### Prerequisitos
- Docker Desktop instalado y corriendo
- Docker Compose v2+
- 4 GB de RAM disponible

### Levantar todo el sistema con un solo comando

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd pipeline_monitoreo

# 2. Crear carpeta de salida
mkdir -p output

# 3. Levantar todos los servicios
docker-compose up --build
```

> ⏳ La primera vez tarda ~3–5 minutos en descargar las imágenes de Kafka y Spark.

### Ver logs por servicio

```bash
# Ver todos los logs
docker-compose logs -f

# Ver solo un servicio
docker-compose logs -f producer-temperatura
docker-compose logs -f spark-processor
docker-compose logs -f alert-monitor
```

### Detener el sistema

```bash
docker-compose down
```

---

## 🖥️ Demo Local (sin Docker)

Si no tienes Docker, puedes correr la simulación directamente en Python:

```bash
# 1. Instalar dependencia mínima
pip install kafka-python

# 2. Ejecutar demo local
python run_demo_local.py
```

Esto simula el pipeline completo sin necesidad de Kafka ni Spark. Los resultados se guardan en `./output/`.

---

## 📦 Entregables

### ENTREGABLE 01 – Productores Kafka

| Script | Topic | Sensores | Rango Normal |
|---|---|---|---|
| `producers/producer_temperatura.py` | `temperatura` | TEMP_A1..C2 | 60–85 °C |
| `producers/producer_presion.py` | `presion` | PRES_A1..C2 | 4–8 bar |
| `producers/producer_vibracion.py` | `vibracion` | VIB_A1..C2 | 0.5–4.5 mm/s |

Cada productor:
- Envía lecturas **cada 1 segundo** por sensor
- Genera **deriva lenta** y **ruido gaussiano** para datos realistas
- Inyecta anomalías con **5% de probabilidad**
- Incluye reintentos automáticos de conexión a Kafka

### ENTREGABLE 02 – Processor Spark

`processor/spark_processor.py`

- Lee los 3 topics simultáneamente con `spark.readStream`
- Parsea JSON con schema definido
- Aplica **ventana tumbling de 1 minuto** con watermark de 2 minutos
- Calcula por sensor y ventana:
  - `promedio`, `minimo`, `maximo`, `desviacion_std`, `total_lecturas`
- Escribe resultados cada 30 segundos

### ENTREGABLE 03 – Sistema de Alertas

`alerts/alert_consumer.py`

Umbrales de detección:

| Sensor | ALTO | CRÍTICO | BAJO |
|---|---|---|---|
| Temperatura | ≥ 90 °C | ≥ 100 °C | ≤ 50 °C |
| Presión | ≥ 9 bar | ≥ 10.5 bar | ≤ 3 bar |
| Vibración | ≥ 5.5 mm/s | ≥ 7.0 mm/s | ≤ 0.1 mm/s |

Iconos en consola:
- 🔴 **CRÍTICO** – requiere acción inmediata
- 🟠 **ALTO** – monitorear de cerca
- 🔵 **BAJO** – posible falla de sensor

### ENTREGABLE 04 – Persistencia

Archivos generados en `./output/`:

| Archivo | Contenido |
|---|---|
| `estadisticas.csv` | Estadísticas por ventana de tiempo |
| `alertas.csv` | Alertas generadas por el monitor de eventos |
| `alertas_spark.csv` | Alertas generadas por Spark |
| `monitoreo.db` | Base de datos SQLite con ambas tablas |

**Esquema `estadisticas_ventana`:**
```
window_start, window_end, sensor_id, linea, tipo_sensor, unidad,
promedio, minimo, maximo, desviacion_std, total_lecturas
```

**Esquema `alertas`:**
```
timestamp, sensor_id, linea, tipo_sensor, valor, unidad, nivel, mensaje
```

### ENTREGABLE 05 – README + docker-compose

- `README.md` ← este archivo
- `docker-compose.yml` ← orquestación completa
- `Dockerfile.producer` ← imagen para productores y alertas
- `Dockerfile.spark` ← imagen para Spark

### ENTREGABLE 06 – Demo en Clase

Ver sección **Guía para la Demo** más abajo.

---

## 📊 Consultar Estadísticas

Durante o después de la demo, puedes consultar los datos guardados:

```bash
# Resumen general
python persistence/query_stats.py

# Solo estadísticas de ventana
python persistence/query_stats.py --stats

# Solo alertas (últimas 30)
python persistence/query_stats.py --alertas --top 30
```

---

## 🎬 Guía para la Demo (5 minutos)

### Paso 1 – Mostrar arquitectura (30 seg)
Mostrar el diagrama de arquitectura y explicar los 3 tipos de sensores.

### Paso 2 – Levantar el sistema (1 min)
```bash
docker-compose up --build
```
Mostrar los logs de los productores enviando datos.

### Paso 3 – Mostrar datos fluyendo (1 min)
```bash
docker-compose logs -f producer-temperatura
```
Señalar los iconos 📊 (normal) vs 🚨 (anomalía).

### Paso 4 – Mostrar alertas (1 min)
```bash
docker-compose logs -f alert-monitor
```
Esperar o forzar una anomalía explicando los umbrales.

### Paso 5 – Mostrar persistencia (1 min)
```bash
python persistence/query_stats.py
cat output/alertas.csv
```

### Paso 6 – Mostrar Spark (30 seg)
```bash
docker-compose logs -f spark-processor
```
Explicar las ventanas tumbling de 1 minuto.

---

## 🏗️ Estructura del Proyecto

```
pipeline_monitoreo/
├── docker-compose.yml          # Orquestación completa
├── Dockerfile.producer         # Imagen para productores y alertas
├── Dockerfile.spark            # Imagen para Spark processor
├── requirements-producer.txt   # Dependencias Python productores
├── requirements-spark.txt      # Dependencias Spark
├── run_demo_local.py           # Demo sin Docker
│
├── config/
│   └── settings.py             # Umbrales y configuración centralizada
│
├── producers/
│   ├── producer_temperatura.py # Sensor temperatura (°C)
│   ├── producer_presion.py     # Sensor presión (bar)
│   └── producer_vibracion.py  # Sensor vibración (mm/s)
│
├── processor/
│   └── spark_processor.py      # PySpark streaming + ventanas
│
├── alerts/
│   └── alert_consumer.py       # Monitor de alertas en tiempo real
│
├── persistence/
│   └── query_stats.py          # Consulta de datos guardados
│
└── output/                     # Generado al correr el sistema
    ├── estadisticas.csv
    ├── alertas.csv
    ├── alertas_spark.csv
    └── monitoreo.db
```

---

## ⚙️ Configuración Avanzada

Editar `config/settings.py` para ajustar:

```python
PROB_ANOMALIA = 0.05        # Probabilidad de anomalía (0.0 – 1.0)
INTERVALO_ENVIO_SEGUNDOS = 1.0  # Frecuencia de envío
VENTANA_MINUTOS = 1         # Tamaño de ventana tumbling
```

---

## 👥 Integrantes del Grupo

| Nombre | Rol |
|---|---|
| Integrante 1 | Productores Kafka |
| Integrante 2 | Spark Processor |
| Integrante 3 | Sistema de Alertas |
| Integrante 4 | Persistencia + README |

---

## 📚 Tecnologías Utilizadas

- **Apache Kafka** 7.4.0 (Confluent) – mensajería distribuida
- **Apache Spark** 3.4.0 – procesamiento de streams
- **PySpark** – API Python para Spark
- **kafka-python** – cliente Kafka para los productores
- **SQLite** – base de datos de persistencia
- **Docker Compose** – orquestación de servicios
