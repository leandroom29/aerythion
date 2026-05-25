from spark.spark_session import get_spark_session


def main():
    spark = get_spark_session("SmartCity-KMeans-Prep")

    input_path = "data/processed/air_quality_clean.csv"

    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("inferSchema", True)
        .csv(input_path)
    )

    # Columnas que usará K-Means
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

    # Eliminar filas con nulos en estas columnas
    df_cluster = df.dropna(subset=clustering_features)

    print("Filas originales:", df.count())
    print("Filas para clustering:", df_cluster.count())

    # Lo convertimos a Pandas para guardar en CSV
    df_cluster_pandas = df_cluster.toPandas()
    df_cluster_pandas.to_csv(
        "data/processed/air_quality_clustering.csv",
        index=False,
        sep=";"
    )

    spark.stop()
    print("Dataset para clustering generado correctamente")


if __name__ == "__main__":
    main()