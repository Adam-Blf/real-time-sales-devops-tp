"""Test B : un événement écrit directement dans Kafka est traité par Spark puis stocké dans PostgreSQL."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from tests.support import settings
from tests.support.platform import fetch_processed_order, topic_producer
from tests.support.polling import wait_for


def make_event(**overrides) -> dict:
    event = {
        "order_id": f"ORD-INTB{uuid.uuid4().hex[:6].upper()}",
        "customer_id": "C-INT-B",
        "product_id": "P003",
        "quantity": 2,
        "unit_price": 49.90,
        "total_amount": 99.80,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    event.update(overrides)
    return event


def publish(*events):
    producer = topic_producer()
    try:
        for event in events:
            producer.send(settings.KAFKA_TOPIC, value=event)
        producer.flush()
    finally:
        producer.close()


def test_event_is_processed_into_processed_orders():
    event = make_event()
    publish(event)

    row = wait_for(
        lambda: fetch_processed_order(event["order_id"]),
        timeout=settings.PIPELINE_TIMEOUT_SECONDS,
        interval=settings.POLL_INTERVAL_SECONDS,
        description=f"row {event['order_id']} in processed_orders",
    )

    assert row["customer_id"] == "C-INT-B"
    assert row["quantity"] == 2
    assert row["unit_price"] == Decimal("49.90")
    assert row["total_amount"] == Decimal("99.80")


def test_invalid_event_is_filtered_out_by_spark():
    invalid = make_event(quantity=0, total_amount=0)
    marker = make_event()
    # Même partition : une fois le marqueur stocké, Spark a forcément déjà traité l'événement invalide.
    publish(invalid, marker)

    wait_for(
        lambda: fetch_processed_order(marker["order_id"]),
        timeout=settings.PIPELINE_TIMEOUT_SECONDS,
        interval=settings.POLL_INTERVAL_SECONDS,
        description=f"marker row {marker['order_id']}",
    )
    assert fetch_processed_order(invalid["order_id"]) is None
