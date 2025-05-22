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

topic = "sensor-kelembaban-gudang"
gudang_ids = ["G1", "G2", "G3"]

while True:
    for gudang in gudang_ids:
        data = {
            "gudang_id": gudang,
            "kelembaban": round(random.uniform(60.0, 80.0), 1)  # Random humidity between 60-80%
        }
        producer.produce(topic, json.dumps(data), callback=delivery_report)
        producer.flush()
    time.sleep(1)