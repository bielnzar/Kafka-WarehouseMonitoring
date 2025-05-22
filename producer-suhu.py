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
            "suhu": round(random.uniform(70.0, 90.0), 1)  # Random temperature between 70-90°C
        }
        producer.produce(topic, json.dumps(data), callback=delivery_report)
        producer.flush()
    time.sleep(1)