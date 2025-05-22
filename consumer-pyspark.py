from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, FloatType

# Initialize Spark Session with Kafka package
spark = SparkSession.builder \
    .appName("LogistikStream") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

# Schema for temperature and humidity data
suhu_schema = StructType([
    StructField("gudang_id", StringType(), True),
    StructField("suhu", FloatType(), True)
])
kelembapan_schema = StructType([
    StructField("gudang_id", StringType(), True),
    StructField("kelembapan", FloatType(), True)
])

# Read streams from Kafka
suhu_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:29092") \
    .option("subscribe", "sensor-suhu-gudang") \
    .load()

kelembapan_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:29092") \
    .option("subscribe", "sensor-kelembaban-gudang") \
    .load()

# Parse JSON data
suhu_parsed = suhu_df.select(from_json(col("value").cast("string"), suhu_schema).alias("data")).select("data.*")
kelembapan_parsed = kelembapan_df.select(from_json(col("value").cast("string"), kelembapan_schema).alias("data")).select("data.*")

# Add timestamp for windowing
suhu_with_time = suhu_parsed.withColumn("timestamp", current_timestamp())
kelembapan_with_time = kelembapan_parsed.withColumn("timestamp", current_timestamp())

# Filter for high temperature (>80°C)
peringatan_suhu = suhu_with_time.filter(col("suhu") > 80.0)

# Filter for high humidity (>70%)
peringatan_kelembapan = kelembapan_with_time.filter(col("kelembapan") > 70.0)

# Print high temperature alerts
query_suhu = peringatan_suhu \
    .selectExpr("gudang_id", "suhu", "'[Peringatan Suhu Tinggi]' AS status") \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

# Print high humidity alerts
query_kelembapan = peringatan_kelembapan \
    .selectExpr("gudang_id", "kelembapan", "'[Peringatan Kelembapan Tinggi]' AS status") \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

# Join streams based on gudang_id and time window (10 seconds)
joined_df = suhu_with_time.join(
    kelembapan_with_time,
    (suhu_with_time.gudang_id == kelembapan_with_time.gudang_id) &
    (suhu_with_time.timestamp.between(kelembapan_with_time.timestamp - 10, kelembapan_with_time.timestamp + 10)),
    "inner"
)

# Filter for critical conditions: temperature >80°C and humidity >70%
kondisi_kritis = joined_df.filter((col("suhu") > 80.0) & (col("kelembapan") > 70.0))

# Print critical alerts
query_kritis = kondisi_kritis \
    .select(
        suhu_with_time.gudang_id,
        suhu_with_time.suhu,
        kelembapan_with_time.kelembapan,
        suhu_with_time.timestamp
    ) \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

# Wait for any termination
spark.streams.awaitAnyTermination()