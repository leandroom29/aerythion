# Smart City Air Quality

Sistema de análisis, predicción y detección de anomalías en calidad del aire urbano utilizando tecnologías Big Data e Inteligencia Artificial.

El proyecto combina procesamiento distribuido con Apache Spark, modelos de Machine Learning y una API REST desarrollada con Flask para el análisis de datos ambientales urbanos.

---

# Objetivo del proyecto

El objetivo principal del sistema es analizar datos procedentes de sensores ambientales urbanos para:

- Detectar anomalías en sensores de calidad del aire
- Predecir niveles de contaminación atmosférica
- Identificar patrones ambientales mediante clustering
- Exponer resultados mediante una API REST

---

# Tecnologías utilizadas

## Big Data

- Apache Spark
- PySpark

## Machine Learning

- scikit-learn
- Pandas
- NumPy

## API REST

- Flask

## Preprocesamiento

- RapidMiner Studio

---

# Arquitectura del proyecto

```text
smart_city_air_quality/
│
├── api_server.py
├── main.py
│
├── data/
│   ├── raw/
│   │   └── AirQualityUCI.csv
│   │
│   ├── processed/
│   │   ├── air_quality_clean.csv
│   │   └── air_quality_clustering.csv
│   │
│   └── output/
│       ├── regression_predictions.csv
│       ├── anomaly_detection_results.csv
│       └── clustering_results.csv
│
├── ml/
│   ├── regression.py
│   ├── anomaly_detection.py
│   ├── clustering.py
│   └── evaluation.py
│
└── spark/
    ├── spark_session.py
    ├── spark_analysis.py
    └── spark_clustering_prep.py
```

---

# Dataset utilizado

## Air Quality UCI Dataset

Dataset oficial del repositorio UCI Machine Learning Repository.

Contiene:

- Concentraciones de gases contaminantes
- Variables meteorológicas
- Mediciones horarias de sensores ambientales

Variables principales:

- CO_GT
- NO2_GT
- NOx_GT
- PT08_S1_CO
- PT08_S2_NMHC
- PT08_S3_NOx
- T
- RH
- AH

---

# Funcionalidades implementadas

## Análisis exploratorio con Spark

- Carga distribuida del dataset
- Estadísticas descriptivas
- Análisis temporal
- Procesamiento Big Data

---

## Preparación de datos

- Limpieza de datos
- Eliminación de valores inválidos
- Normalización de variables
- Preparación para modelos ML

---

## Modelo de regresión

Modelo utilizado:

- RandomForestRegressor

Objetivo:

- Predicción de niveles de CO

Métricas evaluadas:

- RMSE
- MAE
- R²

---

## Detección de anomalías

Modelo utilizado:

- Isolation Forest

Objetivo:

- Detectar lecturas anómalas
- Identificar fallos de sensores
- Detectar eventos extremos

---

## Clustering ambiental

Modelo utilizado:

- K-Means

Objetivo:

- Identificar patrones ambientales urbanos
- Agrupar estados de calidad del aire

---

## API REST

Endpoints disponibles:

| Endpoint | Descripción |
|---|---|
| `/` | Estado de la API |
| `/data` | Dataset procesado |
| `/regression` | Resultados del modelo de regresión |
| `/clustering` | Resultados de clustering |
| `/anomalies` | Resultados de anomalías |

---

# Requisitos

## Python

```text
Python 3.13.9
```

## Apache Spark

```text
Spark 3.x
```

---

# Instalación

## 1. Clonar repositorio

```bash
git clone https://github.com/usuario/smart_city_air_quality.git
```

```bash
cd smart_city_air_quality
```

---

## 2. Crear entorno virtual

### Windows

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

### Linux / Ubuntu

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Dependencias principales

## requirements.txt

```text
pandas
numpy
scikit-learn
flask
pyspark
matplotlib
seaborn
jupyter
pyyaml
```

---

# Ejecución del proyecto

Todo el sistema se ejecuta desde el archivo principal:

```bash
python main.py
```

El pipeline ejecutará automáticamente:

1. Análisis exploratorio con Spark
2. Preparación del dataset
3. Modelo de regresión
4. Detección de anomalías
5. Clustering K-Means
6. Lanzamiento de la API Flask

---

# Resultados generados

Los resultados se almacenan en:

```text
data/output/
```

Archivos generados:

| Archivo | Descripción |
|---|---|
| regression_predictions.csv | Predicciones del modelo |
| anomaly_detection_results.csv | Resultados de anomalías |
| clustering_results.csv | Resultados de clustering |

---

# Uso de la API

Una vez iniciado el sistema:

## Inicio API

```text
http://127.0.0.1:5000/
```

## Endpoints

### Datos procesados

```text
http://127.0.0.1:5000/data
```

### Resultados de regresión

```text
http://127.0.0.1:5000/regression
```

### Resultados de clustering

```text
http://127.0.0.1:5000/clustering
```

### Resultados de anomalías

```text
http://127.0.0.1:5000/anomalies
```

---

# Flujo general del sistema

```text
Dataset CSV
     ↓
RapidMiner
     ↓
Apache Spark
     ↓
Machine Learning
     ↓
Resultados CSV
     ↓
API Flask
```

---

# Escalabilidad futura

La arquitectura puede evolucionar fácilmente hacia:

- Apache Kafka
- Hadoop HDFS
- MongoDB
- Docker
- Kubernetes
- Streaming en tiempo real
- Dashboards Power BI

---

# Posibles mejoras futuras

- Integración con sensores IoT reales
- Visualización avanzada de datos
- Deep Learning con LSTM
- Despliegue cloud
- Dockerización del sistema
- Persistencia NoSQL

---

# Autor

Proyecto desarrollado por:

```text
Leandro Orellana Martos
```

Trabajo Final de Máster — Especialización en Inteligencia Artificial y Big Data.

---

# Licencia

Proyecto académico y educativo.