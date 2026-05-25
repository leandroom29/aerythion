"""
spark_analysis.py
-----------------
Análisis exploratorio Big Data del dataset AirQualityUCI
mediante Apache Spark.

Este módulo se utiliza para justificar el uso de Spark como
tecnología Big Data en el proyecto.
"""

from pyspark.sql.functions import col

from spark.spark_session import get_spark_session


def main():

    # Inicializar sesión Spark
    spark = get_spark_session("SmartCity-Spark-Analysis")

    # Cargar dataset original (sin preprocesar)
    input_path = "data/raw/AirQualityUCI.csv"

    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("inferSchema", True)
        .csv(input_path)
    )

    print("=== ANÁLISIS EXPLORATORIO CON SPARK ===")

    # Información básica
    print("\nNúmero total de registros:")
    print(df.count())

    print("\nEsquema del dataset:")
    df.printSchema()

    # Ajustes de nombres de columnas para facilitar análisis con Spark (da errores con los nombres originales)
    df = df \
        .withColumnRenamed("CO(GT)", "CO_GT") \
        .withColumnRenamed("NO2(GT)", "NO2_GT") \
        .withColumnRenamed("NOx(GT)", "NOx_GT") \
        .withColumnRenamed("PT08.S1(CO)", "PT08_S1_CO")

    # Estadísticas descriptivas de variables clave
    print("\nEstadísticas descriptivas:")
    df.select(
        col("`CO_GT`"),
        col("`NO2_GT`"),
        col("`NOx_GT`"),
        col("`PT08_S1_CO`"),
        col("`T`"),
        col("`RH`"),
        col("`AH`")
    ).describe().show()

    # Análisis temporal básico
    print("\nNúmero de registros por fecha:")

    df.groupBy("Date").count().orderBy("Date").show(5)

    # Finalizar Spark
    spark.stop()

    print("\nAnálisis con Spark finalizado correctamente")


if __name__ == "__main__":
    main()