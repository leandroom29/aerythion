from config.settings import PROCESSED_DIR
from spark.spark_session import get_spark_session


def main():
    spark = get_spark_session("Aerythion-KMeans-Prep")

    input_path = str(PROCESSED_DIR / "air_quality_clean.csv")

    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("inferSchema", True)
        .csv(input_path)
    )

    # Columns used by K-Means
    clustering_features = [
        "CO_GT",
        "NO2_GT",
        "NOx_GT",
        "PT08_S1_CO",
        "PT08_S2_NMHC",
        "PT08_S3_NOx",
        "T",
        "RH",
        "AH"
    ]

    # Drop rows with nulls in these columns
    df_cluster = df.dropna(subset=clustering_features)

    print("Original rows:", df.count())
    print("Rows for clustering:", df_cluster.count())

    # Convert to Pandas to save as CSV
    df_cluster_pandas = df_cluster.toPandas()
    df_cluster_pandas.to_csv(
        PROCESSED_DIR / "air_quality_clustering.csv",
        index=False,
        sep=";"
    )

    spark.stop()
    print("Clustering dataset generated successfully")


if __name__ == "__main__":
    main()