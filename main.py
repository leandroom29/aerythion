from ml.regression import main as run_regression
from ml.clustering import main as run_clustering
from ml.anomaly_detection import main as run_anomaly_detection
from spark.spark_analysis import main as run_spark_analysis
from spark.spark_clustering_prep import main as run_clustering_prep
from api_server import run_api as run_server

import threading
import os


def check_outputs():
    """
    Verifica que los archivos de salida existen antes de lanzar la API
    """
    required_files = [
        "data/output/regression_predictions.csv",
        "data/output/anomaly_detection_results.csv",
        "data/output/clustering_results.csv"
    ]

    for file in required_files:
        if not os.path.exists(file):
            print(f"No se encontró {file}")
            return False

    print("Todos los archivos de salida están presentes.")
    return True

def main():
    try:
        print("=== PIPELINE SMART CITY ===")

        print("Realizando ajustes y configuración incial...")
        print("Cargando dataset y realizando análisis exploratorio con Spark...")
        run_spark_analysis()

        print("Análisis exploratorio con Spark finalizado.")
        print("Preparando dataset para clustering...")
        run_clustering_prep()
        print("Dataset preparado para clustering.")

        print("Ejecutando pipeline de ML...")

        print("============================================")
        print("Realizando modelo de regresión...")
        print("============================================")
        run_regression()

        print("Regresión finalizada.")

        print("============================================")
        print("Realizando modelo de detección de anomalías...")
        print("============================================")
        run_anomaly_detection()

        print("Detección de anomalías finalizada.")

        print("============================================")
        print("Realizando modelo de clustering con dataset preprocesado...")
        print("============================================")
        run_clustering()

        print("Clustering finalizado.")
    
        print("=================================================================")
        print("================================================")
        print("================================\n")
        print("Pipeline finalizado correctamente\n")
        print("================================")
        print("================================================")
        print("=================================================================")

        print("Lanzando servidor Flask para visualización de resultados...")
    
        api_thread = threading.Thread(target=run_server)
        api_thread.start()

        print("Servidor Flask lanzado. Accesos a la API en:")
        print("   http://127.0.0.1:5000/")
        print("   http://127.0.0.1:5000/data")
        print("   http://127.0.0.1:5000/regression")
        print("   http://127.0.0.1:5000/clustering")
        print("   http://127.0.0.1:5000/anomalies")

    
    except Exception as e:
        print("\nERROR EN EL PIPELINE:")
        print(e)

if __name__ == "__main__":
    main()