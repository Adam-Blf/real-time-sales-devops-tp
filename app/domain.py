"""Business rules of the sales platform, free of any Kafka/Spark/PostgreSQL dependency."""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

ORDER_ID_PREFIX = "ORD-"
ORDER_ID_HEX_LENGTH = 10

PRODUCTS = [
    {"product_id": "P001", "name": "Laptop Pro", "category": "Computers", "price": 1299.90},
    {"product_id": "P002", "name": "Keyboard", "category": "Accessories", "price": 89.90},
    {"product_id": "P003", "name": "Mouse", "category": "Accessories", "price": 49.90},
    {"product_id": "P004", "name": "Monitor 27", "category": "Screens", "price": 399.90},
]


class Order(BaseModel):
    customer_id: str = Field(min_length=2)
    product_id: str = Field(min_length=2)
    quantity: int = Field(gt=0, le=1000)
    unit_price: float = Field(gt=0, le=100000)


class OrderEvent(Order):
    order_id: str
    total_amount: float
    timestamp: str


def is_known_product(product_id: str) -> bool:
    return any(product["product_id"] == product_id for product in PRODUCTS)


def compute_total_amount(quantity: int, unit_price: float) -> float:
    return round(quantity * unit_price, 2)


def generate_order_id() -> str:
    return f"{ORDER_ID_PREFIX}{uuid.uuid4().hex[:ORDER_ID_HEX_LENGTH].upper()}"


def build_order_event(order: Order) -> dict:
    return {
        "order_id": generate_order_id(),
        "customer_id": order.customer_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "unit_price": order.unit_price,
        "total_amount": compute_total_amount(order.quantity, order.unit_price),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
