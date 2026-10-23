"""Clients utilisés par les tests d'intégration et E2E pour parler aux vrais services Docker."""

import json
import uuid

import psycopg2
from kafka import KafkaConsumer, KafkaProducer

from tests.support import settings


def postgres_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        connect_timeout=5,
    )


def fetch_processed_order(order_id: str):
    with postgres_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT order_id, customer_id, product_id, quantity, unit_price, total_amount "
            "FROM processed_orders WHERE order_id = %s",
            (order_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    keys = ("order_id", "customer_id", "product_id", "quantity", "unit_price", "total_amount")
    return dict(zip(keys, row))


def topic_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"tests-{uuid.uuid4().hex}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
        consumer_timeout_ms=1000,
    )


def topic_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def find_event(consumer: KafkaConsumer, order_id: str):
    for message in consumer:
        if message.value.get("order_id") == order_id:
            return message.value
    return None
