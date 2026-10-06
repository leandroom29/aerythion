"""
spark_analysis.py
-----------------
Big Data exploratory analysis of the AirQualityUCI dataset
using Apache Spark.

This module demonstrates the use of Spark as a Big Data
technology in this project.
"""

from pyspark.sql.functions import col

from config.settings import RAW_DATA_PATH
from spark.spark_session import get_spark_session


def main():

    # Initialize the Spark session
    spark = get_spark_session("Aerythion-Spark-Analysis")

    # Load the original, unprocessed dataset
    input_path = str(RAW_DATA_PATH)

    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("inferSchema", True)
        .csv(input_path)
    )

    print("=== EXPLORATORY ANALYSIS WITH SPARK ===")

    # Basic information
    print("\nTotal number of records:")
    print(df.count())

    print("\nDataset schema:")
    df.printSchema()

    # Rename columns so Spark can process their original punctuation safely.
    df = df \
        .withColumnRenamed("CO(GT)", "CO_GT") \
        .withColumnRenamed("NO2(GT)", "NO2_GT") \
        .withColumnRenamed("NOx(GT)", "NOx_GT") \
        .withColumnRenamed("PT08.S1(CO)", "PT08_S1_CO")

    # Descriptive statistics for key variables
    print("\nDescriptive statistics:")
    df.select(
        col("`CO_GT`"),
        col("`NO2_GT`"),
        col("`NOx_GT`"),
        col("`PT08_S1_CO`"),
        col("`T`"),
        col("`RH`"),
        col("`AH`")
    ).describe().show()

    # Basic time-based analysis
    print("\nNumber of records by date:")

    df.groupBy("Date").count().orderBy("Date").show(5)

    # Stop Spark
    spark.stop()

    print("\nSpark analysis completed successfully")


if __name__ == "__main__":
    main()