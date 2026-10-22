"""End-to-end scenario: API -> Kafka -> PySpark -> PostgreSQL."""

from decimal import Decimal

import httpx
import pytest

from tests.support import settings
from tests.support.platform import fetch_processed_order
from tests.support.polling import wait_for

ORDER = {"customer_id": "C100", "product_id": "P001", "quantity": 3, "unit_price": 100}


@pytest.fixture(scope="module")
def platform_ready():
    """Given the infrastructure is started."""
    wait_for(
        lambda: httpx.get(f"{settings.API_URL}/api/health", timeout=5).status_code == 200,
        timeout=60,
        description="sales API health",
    )


def test_order_flows_from_api_to_postgres(platform_ready):
    # When an order is sent to the API
    response = httpx.post(f"{settings.API_URL}/api/orders", json=ORDER, timeout=15)
    assert response.status_code == 201
    event = response.json()
    assert event["total_amount"] == 300

    # Then it is published, consumed, processed and stored with the expected values
    row = wait_for(
        lambda: fetch_processed_order(event["order_id"]),
        timeout=settings.PIPELINE_TIMEOUT_SECONDS,
        interval=settings.POLL_INTERVAL_SECONDS,
        description=f"order {event['order_id']} in processed_orders",
    )
    assert row == {
        "order_id": event["order_id"],
        "customer_id": "C100",
        "product_id": "P001",
        "quantity": 3,
        "unit_price": Decimal("100.00"),
        "total_amount": Decimal("300.00"),
    }
