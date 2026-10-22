"""Test A : une commande envoyée à l'API démarrée devient un événement dans le topic Kafka."""

import httpx
import pytest

from tests.support import settings
from tests.support.platform import find_event, topic_consumer
from tests.support.polling import wait_for

ORDER = {"customer_id": "C-INT-A", "product_id": "P002", "quantity": 4, "unit_price": 89.90}


@pytest.fixture
def consumer():
    kafka_consumer = topic_consumer()
    yield kafka_consumer
    kafka_consumer.close()


def test_api_is_up():
    response = httpx.get(f"{settings.API_URL}/api/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_posted_order_is_published_to_kafka(consumer):
    response = httpx.post(f"{settings.API_URL}/api/orders", json=ORDER, timeout=15)
    assert response.status_code == 201
    order_id = response.json()["order_id"]

    event = wait_for(
        lambda: find_event(consumer, order_id),
        timeout=30,
        description=f"event {order_id} in topic {settings.KAFKA_TOPIC}",
    )

    assert event["customer_id"] == ORDER["customer_id"]
    assert event["product_id"] == ORDER["product_id"]
    assert event["quantity"] == ORDER["quantity"]
    assert event["total_amount"] == 359.6


def test_unknown_product_is_not_published():
    response = httpx.post(f"{settings.API_URL}/api/orders", json={**ORDER, "product_id": "P999"}, timeout=15)
    assert response.status_code == 404
