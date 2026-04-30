import os
import sys
import json
import logging
from datetime import datetime
import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, avg,
    count, current_timestamp, round as spark_round
)
from pyspark.sql.types import (
    StructType, StructField, StringType,
    DoubleType, LongType, TimestampType
)
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
KAFKA_TOPIC    = os.getenv("KAFKA_TOPIC",  "market_data")
PG_HOST        = os.getenv("POSTGRES_HOST",     "localhost")
PG_PORT        = os.getenv("POSTGRES_PORT",     "5432")
PG_DB          = os.getenv("POSTGRES_DB",       "market_db")
PG_USER        = os.getenv("POSTGRES_USER",     "market_user")
PG_PASSWORD    = os.getenv("POSTGRES_PASSWORD", "market_pass")
S3_BUCKET      = os.getenv("S3_BUCKET",         "market-streaming-data-aayus")
AWS_REGION     = os.getenv("AWS_REGION",         "us-east-1")
CHECKPOINT_DIR = "/home/ubuntu/market-streaming-platform/logs/checkpoint"

STOCK_SCHEMA = StructType([
    StructField("symbol",         StringType(),  True),
    StructField("price",          DoubleType(),  True),
    StructField("previous_close", DoubleType(),  True),
    StructField("change_pct",     DoubleType(),  True),
    StructField("volume",         LongType(),    True),
    StructField("market_cap",     LongType(),    True),
    StructField("timestamp",      StringType(),  True),
    StructField("source",         StringType(),  True),
])

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASSWORD
    )

def write_to_s3(rows, epoch_id):
    if not rows:
        return
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        now = datetime.utcnow()
        date_prefix = now.strftime("%Y/%m/%d")
        records = [row.asDict() for row in rows]
        # Convert non-serializable types
        for r in records:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
        key = f"raw/{date_prefix}/epoch_{epoch_id}_{now.strftime('%H%M%S')}.json"
        body = "\n".join(json.dumps(r) for r in records)
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode("utf-8"))
        logger.info(f"[S3] Wrote {len(records)} records to s3://{S3_BUCKET}/{key}")
    except Exception as e:
        logger.error(f"S3 write error: {e}")

def write_to_postgres(df, epoch_id):
    rows = df.collect()
    if not rows:
        return
    # Write raw to S3
    write_to_s3(rows, epoch_id)
    # Write aggregates to Postgres
    conn = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        records = [
            (
                row["symbol"],
                float(row["avg_price"])      if row["avg_price"]      else None,
                float(row["avg_prev_close"]) if row["avg_prev_close"] else None,
                float(row["avg_change_pct"]) if row["avg_change_pct"] else None,
                int(row["total_volume"])      if row["total_volume"]   else None,
                int(row["avg_market_cap"])    if row["avg_market_cap"] else None,
                row["window_start"].isoformat() if row["window_start"] else None,
                "spark_stream",
            )
            for row in rows
        ]
        execute_batch(cur, """
            INSERT INTO stock_metrics
                (symbol, price, previous_close, change_pct,
                 volume, market_cap, event_time, source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, records)
        conn.commit()
        logger.info(f"[Epoch {epoch_id}] Wrote {len(records)} rows to PostgreSQL")
    except Exception as e:
        logger.error(f"PostgreSQL write error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def create_spark_session():
    return (
        SparkSession.builder
        .appName("MarketDataStreaming")
        .master("local[2]")
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.driver.memory", "512m")
        .config("spark.executor.memory", "512m")
        .config("spark.memory.offHeap.enabled", "true")
        .config("spark.memory.offHeap.size", "256m")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR)
        .getOrCreate()
    )

def run_spark_consumer():
    logger.info("Starting Spark Structured Streaming job...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKER)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed_df = (
        raw_df
        .select(
            from_json(col("value").cast("string"), STOCK_SCHEMA).alias("data"),
            col("timestamp").alias("kafka_ts")
        )
        .select("data.*", "kafka_ts")
        .withColumn("event_time", col("timestamp").cast(TimestampType()))
    )

    aggregated_df = (
        parsed_df
        .withWatermark("event_time", "30 seconds")
        .groupBy(window(col("event_time"), "1 minute"), col("symbol"))
        .agg(
            spark_round(avg("price"),          2).alias("avg_price"),
            spark_round(avg("previous_close"), 2).alias("avg_prev_close"),
            spark_round(avg("change_pct"),     4).alias("avg_change_pct"),
            spark_round(avg("volume"),         0).alias("total_volume"),
            spark_round(avg("market_cap"),     0).alias("avg_market_cap"),
            count("*").alias("event_count"),
        )
        .select(
            col("symbol"),
            col("avg_price"),
            col("avg_prev_close"),
            col("avg_change_pct"),
            col("total_volume"),
            col("avg_market_cap"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("event_count"),
        )
    )

    query = (
        aggregated_df.writeStream
        .outputMode("update")
        .foreachBatch(write_to_postgres)
        .option("checkpointLocation", CHECKPOINT_DIR)
        .trigger(processingTime="10 seconds")
        .start()
    )

    logger.info(f"Spark streaming started — Kafka: {KAFKA_TOPIC} → Postgres + S3: {S3_BUCKET}")
    query.awaitTermination()

if __name__ == "__main__":
    run_spark_consumer()
