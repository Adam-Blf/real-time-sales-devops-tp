from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from kafka.errors import KafkaError

from app import messaging
from app.domain import PRODUCTS, Order, OrderEvent, build_order_event, is_known_product

__all__ = ["app", "Order", "OrderEvent", "build_order_event"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    messaging.close_producer()


app = FastAPI(
    title="Real-Time Sales API",
    version="1.0.0",
    description="API pédagogique de génération d'événements de ventes.",
    lifespan=lifespan,
)


@app.get("/api/health")
def health():
    return {"status": "UP", "service": "sales-api"}


@app.get("/api/products")
def products():
    return PRODUCTS


@app.post("/api/orders", response_model=OrderEvent, status_code=201)
def create_order(order: Order):
    if not is_known_product(order.product_id):
        raise HTTPException(status_code=404, detail="Unknown product")

    event = build_order_event(order)
    try:
        messaging.publish_order_event(event)
    except KafkaError as error:
        raise HTTPException(status_code=503, detail="Event bus unavailable") from error

    return event
