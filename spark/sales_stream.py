import os

import psycopg2
from psycopg2.extras import execute_values
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, TimestampType
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "sales.orders")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sales")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sales")
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
CHECKPOINT_LOCATION = os.getenv("CHECKPOINT_LOCATION", "/opt/spark-checkpoints/sales")

COLUMNS = ("order_id", "customer_id", "product_id", "quantity",
           "unit_price", "total_amount", "event_timestamp")

# Insertion idempotente : un micro-batch rejoué (redémarrage, checkpoint perdu) ne doit pas échouer sur la clé primaire.
INSERT_SQL = (
    f"INSERT INTO processed_orders ({', '.join(COLUMNS)}) VALUES %s "
    "ON CONFLICT (order_id) DO NOTHING"
)

schema = StructType([
    StructField("order_id", StringType(), False),
    StructField("customer_id", StringType(), False),
    StructField("product_id", StringType(), False),
    StructField("quantity", IntegerType(), False),
    StructField("unit_price", DoubleType(), False),
    StructField("total_amount", DoubleType(), False),
    StructField("timestamp", TimestampType(), False),
])


def insert_rows(rows, chunk_size=500):
    """S'exécute sur le driver, seul processus où psycopg2 est installé."""
    connection = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
    )
    try:
        with connection, connection.cursor() as cursor:
            chunk = []
            for row in rows:
                chunk.append(tuple(row[column] for column in COLUMNS))
                if len(chunk) >= chunk_size:
                    execute_values(cursor, INSERT_SQL, chunk)
                    chunk = []
            if chunk:
                execute_values(cursor, INSERT_SQL, chunk)
    finally:
        connection.close()


def write_to_postgres(batch_df, batch_id):
    output = batch_df.select(*COLUMNS[:-1], col("timestamp").alias("event_timestamp"))
    # toLocalIterator rapatrie une partition à la fois vers le driver au lieu de tout collecter.
    insert_rows(output.toLocalIterator())


def main():
    spark = SparkSession.builder.appName("SalesStreamingPipeline").getOrCreate()

    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    orders = (
        raw.select(from_json(col("value").cast("string"), schema).alias("data"))
        .select("data.*")
        .filter(col("order_id").isNotNull())
        .filter((col("quantity") > 0) & (col("unit_price") > 0))
    )

    query = (
        orders.writeStream
        .foreachBatch(write_to_postgres)
        .outputMode("append")
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
