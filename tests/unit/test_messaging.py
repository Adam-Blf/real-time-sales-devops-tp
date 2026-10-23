from app import messaging


def test_create_kafka_producer_uses_configured_servers(monkeypatch):
    captured = {}

    def fake_kafka_producer(**kwargs):
        captured.update(kwargs)
        return "producer"

    monkeypatch.setattr(messaging, "KafkaProducer", fake_kafka_producer)
    assert messaging.create_kafka_producer() == "producer"
    assert captured["bootstrap_servers"] == messaging.KAFKA_BOOTSTRAP_SERVERS
    assert captured["value_serializer"]({"a": 1}) == b'{"a": 1}'


def test_close_without_producer_is_a_no_op(monkeypatch):
    monkeypatch.setattr(messaging, "_producer", None)
    messaging.close_producer()
    assert messaging._producer is None
