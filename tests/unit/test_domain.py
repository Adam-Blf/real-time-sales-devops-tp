import re
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain import (
    Order,
    build_order_event,
    compute_total_amount,
    generate_order_id,
    is_known_product,
)


def make_order(**overrides) -> Order:
    fields = {"customer_id": "C001", "product_id": "P001", "quantity": 2, "unit_price": 50.0}
    fields.update(overrides)
    return Order(**fields)


# Total amount

@pytest.mark.parametrize(
    "quantity, unit_price, expected",
    [(2, 50.0, 100.0), (3, 100, 300.0), (1, 49.90, 49.90), (3, 0.1, 0.3), (7, 19.99, 139.93)],
)
def test_total_amount_is_quantity_times_price(quantity, unit_price, expected):
    assert compute_total_amount(quantity, unit_price) == expected


def test_total_amount_is_rounded_to_cents():
    assert compute_total_amount(3, 33.333) == 100.0


# Quantity

def test_positive_quantity_is_accepted():
    assert make_order(quantity=1).quantity == 1


def test_quantity_upper_bound_is_inclusive():
    assert make_order(quantity=1000).quantity == 1000


@pytest.mark.parametrize("quantity", [0, -1, -50, 1001])
def test_out_of_range_quantity_is_rejected(quantity):
    with pytest.raises(ValidationError):
        make_order(quantity=quantity)


def test_non_numeric_quantity_is_rejected():
    with pytest.raises(ValidationError):
        make_order(quantity="two")


# Unit price

@pytest.mark.parametrize("unit_price", [0.01, 49.90, 100000])
def test_positive_price_is_accepted(unit_price):
    assert make_order(unit_price=unit_price).unit_price == unit_price


@pytest.mark.parametrize("unit_price", [0, -10.0, 100000.01, "free"])
def test_invalid_price_is_rejected(unit_price):
    with pytest.raises(ValidationError):
        make_order(unit_price=unit_price)


# Customer and product identifiers

@pytest.mark.parametrize("field", ["customer_id", "product_id"])
@pytest.mark.parametrize("value", ["", "C"])
def test_identifier_shorter_than_two_chars_is_rejected(field, value):
    with pytest.raises(ValidationError):
        make_order(**{field: value})


@pytest.mark.parametrize("field", ["customer_id", "product_id"])
def test_missing_identifier_is_rejected(field):
    fields = {"customer_id": "C001", "product_id": "P001", "quantity": 1, "unit_price": 1.0}
    del fields[field]
    with pytest.raises(ValidationError):
        Order(**fields)


@pytest.mark.parametrize("product_id, known", [("P001", True), ("P004", True), ("P999", False)])
def test_product_catalog_lookup(product_id, known):
    assert is_known_product(product_id) is known


# Order identifier

def test_order_id_format():
    assert re.fullmatch(r"ORD-[0-9A-F]{10}", generate_order_id())


def test_order_ids_are_unique():
    assert len({generate_order_id() for _ in range(1000)}) == 1000


# Event construction

def test_event_contains_every_expected_field():
    event = build_order_event(make_order())
    assert set(event) == {
        "order_id", "customer_id", "product_id", "quantity",
        "unit_price", "total_amount", "timestamp",
    }


def test_event_copies_order_values_and_computes_total():
    event = build_order_event(make_order(customer_id="C100", quantity=3, unit_price=100))
    assert event["customer_id"] == "C100"
    assert event["product_id"] == "P001"
    assert event["quantity"] == 3
    assert event["unit_price"] == 100
    assert event["total_amount"] == 300.0
    assert event["order_id"].startswith("ORD-")


def test_event_timestamp_is_timezone_aware_iso8601():
    timestamp = datetime.fromisoformat(build_order_event(make_order())["timestamp"])
    assert timestamp.utcoffset() is not None
