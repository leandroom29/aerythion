"""
spark_session.py
----------------
This module centralizes the creation and configuration of the Spark
session used throughout Aerythion.

"""

from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "Aerythion"):
    """
    Create and return a Spark session configured for local execution.

    """

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")  # Use all available CPU cores
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    return spark