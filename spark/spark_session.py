"""
spark_session.py
----------------
Este módulo centraliza la creación y configuración de la sesión de Spark
para todo el proyecto de analítica urbana Smart City.

"""

from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "SmartCityAirQuality"):
    """
    Crea y devuelve una sesión de Spark configurada para ejecución local.

    """

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")  # Se usan todos los núcleos disponibles
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    return spark