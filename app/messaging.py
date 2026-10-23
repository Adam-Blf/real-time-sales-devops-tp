"""Publication des événements de commande dans Kafka."""

import json
import os
import threading

from kafka import KafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "sales.orders")
SEND_TIMEOUT_SECONDS = 10

_producer = None
_producer_lock = threading.Lock()


def create_kafka_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        retries=5,
    )


def get_producer() -> KafkaProducer:
    """Renvoie un producteur unique partagé par toutes les requêtes, au lieu d'un par commande."""
    global _producer
    if _producer is None:
        with _producer_lock:
            if _producer is None:
                _producer = create_kafka_producer()
    return _producer


def publish_order_event(event: dict) -> None:
    get_producer().send(KAFKA_TOPIC, value=event).get(timeout=SEND_TIMEOUT_SECONDS)


def close_producer() -> None:
    global _producer
    with _producer_lock:
        if _producer is not None:
            _producer.flush()
            _producer.close()
            _producer = None
