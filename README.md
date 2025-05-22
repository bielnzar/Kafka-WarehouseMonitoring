# Sistem Monitoring Gudang

Penjelaskan langkah-langkah pembuatan dan penggunaan sistem monitoring gudang menggunakan Apache Kafka dan PySpark untuk memantau suhu dan kelembapan di tiga gudang (G1, G2, G3). Sistem ini menghasilkan peringatan untuk suhu >80°C, kelembapan >70%, dan kondisi kritis (suhu >80°C dan kelembapan >70% secara bersamaan).

## Prerequest

Sebelum memulai, pastikan memiliki:

- **Docker Desktop** terinstal untuk menjalankan Kafka, Zookeeper, dan Kafka UI.
- **Python 3.11** (direkomendasikan, karena Python 3.13 mungkin bermasalah dengan Spark 3.5.0).
- **Java 8 atau 11** untuk PySpark.
- **winutils.exe** untuk Hadoop di Windows.
- Koneksi internet untuk mengunduh dependensi.

## 1 : Setup Environment

### 1.1 Instalasi Dependensi Python

1. Instal library Python yang dibutuhkan:
   ```bash
   pip install confluent-kafka pyspark
   ```
2. Verifikasi instalasi:
   ```bash
   pip show confluent-kafka
   pip show pyspark
   ```
   Pastikan PySpark versi 3.5.0 dan `confluent-kafka` versi terbaru (misalnya, 2.5.0).

### 1.2 Setup Hadoop untuk Windows

PySpark membutuhkan `winutils.exe` untuk berjalan di Windows.

1. Unduh `winutils.exe` untuk Hadoop 3.3.0 dari [repositori GitHub winutils](https://github.com/cdarlint/winutils) (file di `hadoop-3.3.0/bin/winutils.exe`).
2. Buat folder `C:\hadoop\bin` dan salin `winutils.exe` ke dalamnya.
3. Atur variabel lingkungan:
   - Buka **System Properties** > **Environment Variables**.
   - Tambahkan **System Variable**:
     - Nama: `HADOOP_HOME`
     - Nilai: `C:\hadoop`
   - Tambahkan `C:\hadoop\bin` ke variabel **Path**.
4. Verifikasi:
   ```bash
   winutils.exe
   ```
   Akan terlihat informasi penggunaan jika berhasil.
5. Berikan izin ke direktori sementara:
   ```bash
   mkdir \tmp\hive
   winutils.exe chmod -R 777 \tmp\hive
   ```

### 1.3 Setup Java

PySpark membutuhkan Java 8 atau 11.

1. Cek versi Java:
   ```bash
   java -version
   ```
   Pastikan output menunjukkan Java 8 (misalnya, `1.8.0_351`) atau Java 11 (misalnya, `11.0.17`).
2. Jika belum terinstal, unduh JDK 8 atau 11 dari [Oracle](https://www.oracle.com/java/technologies/javase-downloads.html) atau [AdoptOpenJDK](https://adoptium.net/).
3. Atur variabel lingkungan:
   - Tambahkan **System Variable**:
     - Nama: `JAVA_HOME`
     - Nilai: Lokasi JDK (misalnya, `C:\Program Files\Java\jdk1.8.0_351`).
   - Tambahkan `%JAVA_HOME%\bin` ke variabel **Path**.
4. Verifikasi:
   ```bash
   echo %JAVA_HOME%
   java -version
   ```

## 2 : Konfigurasi Docker untuk Kafka

Kafka digunakan untuk mengelola stream data suhu dan kelembapan. Kami akan menggunakan Docker untuk menjalankan Kafka, Zookeeper, dan Kafka UI.

1. **Buat File `docker-compose.yml`**:

   - Simpan kode berikut di folder proyek (misalnya, `D:\AiTieS\KULIAH\Semester_4\Big Data\Tugas\5\Kafka-WarehouseMonitoring`):

     ```yaml
     version: "3"

     services:
       zookeeper:
         image: confluentinc/cp-zookeeper:7.4.0
         container_name: zookeeper
         ports:
           - "2181:2181"
         environment:
           ZOOKEEPER_CLIENT_PORT: 2181
           ZOOKEEPER_TICK_TIME: 2000

       kafka:
         image: confluentinc/cp-kafka:7.4.0
         container_name: kafka
         depends_on:
           - zookeeper
         ports:
           - "9092:9092"
           - "29092:29092"
         environment:
           KAFKA_BROKER_ID: 1
           KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
           KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
           KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
           KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
           KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
           KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
           KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
           KAFKA_NUM_PARTITIONS: 3
           KAFKA_DELETE_TOPIC_ENABLE: "true"

       kafka-ui:
         image: provectuslabs/kafka-ui:latest
         container_name: kafka-ui
         depends_on:
           - kafka
         ports:
           - "8080:8080"
         environment:
           KAFKA_CLUSTERS_0_NAME: local
           KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
           KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
     ```

2. **Jalankan Docker Compose**:
   - Di terminal, navigasi ke folder proyek dan jalankan:
     ```bash
     docker-compose up -d
     ```
3. **Verifikasi**:
   - Cek status kontainer:
     ```bash
     docker-compose ps
     ```
     Pastikan `zookeeper`, `kafka`, dan `kafka-ui` dalam status "Up".
   - Buka `http://localhost:8080` untuk mengakses Kafka UI dan pastikan cluster terdeteksi.

## 3 : Buat Kafka Producer

Kami membuat dua producer untuk mengirim data suhu dan kelembapan ke topik Kafka.

### 3.1 Producer Suhu

1. **Buat File `producer-suhu.py`**:

   - Simpan kode berikut:

     ```python
     from confluent_kafka import Producer
     import json
     import time
     import random

     conf = {'bootstrap.servers': 'localhost:29092'}
     producer = Producer(conf)

     def delivery_report(err, msg):
         if err is not None:
             print(f"Message delivery failed: {err}")
         else:
             print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

     topic = "sensor-suhu-gudang"
     gudang_ids = ["G1", "G2", "G3"]

     while True:
         for gudang in gudang_ids:
             data = {
                 "gudang_id": gudang,
                 "suhu": round(random.uniform(70.0, 90.0), 1)  # Suhu acak 70-90°C
             }
             producer.produce(topic, json.dumps(data), callback=delivery_report)
             producer.flush()
         time.sleep(1)
     ```

### 3.2 Producer Kelembapan

1. **Buat File `producer-kelembapan.py`**:

   - Simpan kode berikut:

     ```python
     from confluent_kafka import Producer
     import json
     import time
     import random

     conf = {'bootstrap.servers': 'localhost:29092'}
     producer = Producer(conf)

     def delivery_report(err, msg):
         if err is not None:
             print(f"Message delivery failed: {err}")
         else:
             print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

     topic = "sensor-kelembapan-gudang"
     gudang_ids = ["G1", "G2", "G3"]

     while True:
         for gudang in gudang_ids:
             data = {
                 "gudang_id": gudang,
                 "kelembapan": round(random.uniform(60.0, 80.0), 1)  # Kelembapan acak 60-80%
             }
             producer.produce(topic, json.dumps(data), callback=delivery_report)
             producer.flush()
         time.sleep(1)
     ```

2. **Jalankan Producer**:
   - Buka dua terminal terpisah dan jalankan:
     ```bash
     python producer-suhu.py
     python producer-kelembapan.py
     ```
   - Pastikan output menunjukkan pengiriman berhasil, misalnya:
     ```
     Message delivered to sensor-suhu-gudang [0]
     Message delivered to sensor-kelembapan-gudang [0]
     ```

## 4 : Buat PySpark Consumer

Consumer akan membaca stream dari Kafka, menyaring data, dan menghasilkan peringatan.

1. **Buat File `consumer-pyspark.py`**:

   - Simpan kode berikut:

     ```python
     from pyspark.sql import SparkSession
     from pyspark.sql.functions import col, from_json, current_timestamp, lit
     from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType

     # Inisialisasi Spark Session
     spark = SparkSession.builder \
         .appName("LogistikStream") \
         .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
         .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem") \
         .getOrCreate()

     # Skema untuk data suhu dan kelembapan
     suhu_schema = StructType([
         StructField("gudang_id", StringType(), True),
         StructField("suhu", FloatType(), True)
     ])
     kelembapan_schema = StructType([
         StructField("gudang_id", StringType(), True),
         StructField("kelembapan", FloatType(), True)
     ])

     try:
         # Baca stream dari Kafka
         suhu_df = spark.readStream \
             .format("kafka") \
             .option("kafka.bootstrap.servers", "localhost:29092") \
             .option("subscribe", "sensor-suhu-gudang") \
             .option("startingOffsets", "earliest") \
             .load()

         kelembapan_df = spark.readStream \
             .format("kafka") \
             .option("kafka.bootstrap.servers", "localhost:29092") \
             .option("subscribe", "sensor-kelembapan-gudang") \
             .option("startingOffsets", "earliest") \
             .load()

         # Parsing data JSON
         suhu_parsed = suhu_df.select(from_json(col("value").cast("string"), suhu_schema).alias("data")).select("data.*")
         kelembapan_parsed = kelembapan_df.select(from_json(col("value").cast("string"), kelembapan_schema).alias("data")).select("data.*")

         # Tambah timestamp untuk windowing
         suhu_with_time = suhu_parsed.withColumn("timestamp", current_timestamp())
         kelembapan_with_time = kelembapan_parsed.withColumn("timestamp", current_timestamp())

         # Filter suhu tinggi (>80°C)
         peringatan_suhu = suhu_with_time.filter(col("suhu") > 80.0)

         # Filter kelembapan tinggi (>70%)
         peringatan_kelembapan = kelembapan_with_time.filter(col("kelembapan") > 70.0)

         # Tampilkan peringatan suhu tinggi
         query_suhu = peringatan_suhu \
             .selectExpr("gudang_id", "suhu", "'[Peringatan Suhu Tinggi]' AS status") \
             .writeStream \
             .outputMode("append") \
             .format("console") \
             .option("truncate", False) \
             .start()

         # Tampilkan peringatan kelembapan tinggi
         query_kelembapan = peringatan_kelembapan \
             .selectExpr("gudang_id", "kelembapan", "'[Peringatan Kelembapan Tinggi]' AS status") \
             .writeStream \
             .outputMode("append") \
             .format("console") \
             .option("truncate", False) \
             .start()

         # Gabungkan stream berdasarkan gudang_id dan jendela waktu 10 detik
         joined_df = suhu_with_time.join(
             kelembapan_with_time,
             (suhu_with_time.gudang_id == kelembapan_with_time.gudang_id) &
             (suhu_with_time.timestamp.between(kelembapan_with_time.timestamp - 10, kelembapan_with_time.timestamp + 10)),
             "inner"
         )

         # Filter kondisi kritis: suhu >80°C dan kelembapan >70%
         kondisi_kritis = joined_df.filter((col("suhu") > 80.0) & (col("kelembapan") > 70.0))

         # Buat kolom status untuk kondisi kritis
         kondisi_kritis_with_status = kondisi_kritis.select(
             suhu_with_time.gudang_id,
             suhu_with_time.suhu,
             kelembapan_with_time.kelembapan,
             suhu_with_time.timestamp,
             lit("[PERINGATAN KRITIS] Status: Bahaya tinggi! Barang berisiko rusak").alias("status")
         )

         # Tampilkan peringatan kritis
         query_kritis = kondisi_kritis_with_status \
             .writeStream \
             .outputMode("append") \
             .format("console") \
             .option("truncate", False) \
             .start()

         # Tunggu terminasi
         spark.streams.awaitAnyTermination()

     except Exception as e:
         print(f"Error menjalankan aplikasi Spark: {e}")
     finally:
         spark.stop()
     ```

2. **Jalankan Consumer**:
   - Buka terminal baru dan jalankan:
     ```bash
     python consumer-pyspark.py
     ```

## 5 : Validasi Sistem

Untuk memastikan sistem berfungsi sesuai tugas, lakukan validasi berikut:

1. **Cek Docker dan Kafka**:

   - Verifikasi kontainer aktif:
     ```bash
     docker-compose ps
     ```
   - Buka `http://localhost:8080` untuk memastikan Kafka UI menampilkan cluster dan topik (`sensor-suhu-gudang`, `sensor-kelembapan-gudang`).

2. **Cek Producer**:

   - Pastikan producer mengirim data:
     ```
     Message delivered to sensor-suhu-gudang [0]
     Message delivered to sensor-kelembapan-gudang [0]
     ```
   - Di Kafka UI, periksa pesan di topik untuk memastikan format data benar (misalnya, `{"gudang_id": "G1", "suhu": 82}`).

3. **Cek Consumer**:

   - Pastikan consumer menampilkan peringatan.

4. **Validasi Persyaratan Tugas**:
   - Topik Kafka dibuat otomatis (`KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`).
   - Producer mengirim data setiap detik untuk G1, G2, G3 dalam format yang benar.
   - Consumer menyaring suhu >80°C dan kelembapan >70%, serta menggabungkan stream untuk kondisi kritis dalam jendela waktu 10 detik.

## 6: Troubleshooting

Jika terjadi masalah, coba langkah berikut:

- **Error HADOOP_HOME**:
  - Pastikan `winutils.exe` ada di `C:\hadoop\bin`.
  - Verifikasi variabel `HADOOP_HOME` dengan:
    ```bash
    echo %HADOOP_HOME%
    ```
- **Zookeeper Tidak Berjalan**:
  - Cek log:
    ```bash
    docker-compose logs zookeeper
    ```
  - Pastikan port 2181 tidak digunakan:
    ```bash
    netstat -an | findstr 2181
    ```
  - Tambahkan batasan sumber daya di `docker-compose.yml`:
    ```yaml
    zookeeper:
      deploy:
        resources:
          limits:
            cpus: "0.5"
            memory: 512M
    kafka:
      deploy:
        resources:
          limits:
            cpus: "1.0"
            memory: 1G
    ```
- **Koneksi Kafka Gagal**:
  - Ganti `localhost:29092` dengan `127.0.0.1:29092` atau `host.docker.internal:29092` di producer dan consumer.
  - Buka port 29092 di firewall:
    ```bash
    netsh advfirewall firewall add rule name="Kafka 29092" dir=in action=allow protocol=TCP localport=29092
    ```

## 7 : Kesimpulan

Sistem monitoring gudang ini berhasil dibuat dan dijalankan dengan:

- **Docker** untuk menjalankan Kafka, Zookeeper, dan Kafka UI.
- **Kafka Producer** untuk mengirim data suhu dan kelembapan.
- **PySpark Consumer** untuk memproses stream dan menghasilkan peringatan.
  Semua persyaratan tugas terpenuhi, termasuk filtering data dan pembuatan peringatan kritis. Dokumentasi berupa screenshot dan log disertakan untuk validasi.

## Dokumentasi

[image1](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/1.png)
[image2](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/2.png)
[image3](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/3.png)
[image4](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/4.png)
[image5](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/5.png)
[image6](https://github.com/bielnzar/Kafka-WarehouseMonitoring/blob/main/images/6.png)
