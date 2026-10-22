"""API behaviour with Kafka replaced by an in-memory fake: no external service involved."""

import pytest
from fastapi.testclient import TestClient
from kafka.errors import KafkaTimeoutError

from app import messaging
from app.main import app

VALID_ORDER = {"customer_id": "C100", "product_id": "P001", "quantity": 3, "unit_price": 100}


class FakeFuture:
    def get(self, timeout=None):
        return None


class FakeProducer:
    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, topic, value):
        self.sent.append((topic, value))
        return FakeFuture()

    def flush(self):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def producer(monkeypatch):
    fake = FakeProducer()
    monkeypatch.setattr(messaging, "_producer", None)
    monkeypatch.setattr(messaging, "create_kafka_producer", lambda: fake)
    return fake


@pytest.fixture
def client(producer):
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "service": "sales-api"}


def test_products_lists_catalog(client):
    ids = [product["product_id"] for product in client.get("/api/products").json()]
    assert ids == ["P001", "P002", "P003", "P004"]


def test_valid_order_is_published_and_returned(client, producer):
    response = client.post("/api/orders", json=VALID_ORDER)
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 300.0
    assert producer.sent == [(messaging.KAFKA_TOPIC, body)]


def test_unknown_product_returns_404_and_publishes_nothing(client, producer):
    response = client.post("/api/orders", json={**VALID_ORDER, "product_id": "P999"})
    assert response.status_code == 404
    assert producer.sent == []


@pytest.mark.parametrize("override", [{"quantity": 0}, {"quantity": -1}, {"unit_price": 0}, {"customer_id": ""}])
def test_invalid_payload_returns_422(client, producer, override):
    response = client.post("/api/orders", json={**VALID_ORDER, **override})
    assert response.status_code == 422
    assert producer.sent == []


def test_kafka_failure_returns_503(client, monkeypatch):
    def broken_publish(event):
        raise KafkaTimeoutError("broker down")

    monkeypatch.setattr(messaging, "publish_order_event", broken_publish)
    response = client.post("/api/orders", json=VALID_ORDER)
    assert response.status_code == 503


def test_producer_is_shared_between_orders(client, producer):
    client.post("/api/orders", json=VALID_ORDER)
    client.post("/api/orders", json=VALID_ORDER)
    assert len(producer.sent) == 2
    assert messaging.get_producer() is producer


def test_producer_is_closed_on_shutdown(producer):
    with TestClient(app) as test_client:
        test_client.post("/api/orders", json=VALID_ORDER)
    assert producer.closed
    assert messaging._producer is None
