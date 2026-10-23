"""Points d'accès de la plateforme démarrée, surchargeables pour que les mêmes tests tournent sur le poste et dans Jenkins."""

import os

API_URL = os.getenv("API_URL", "http://localhost:8000")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "sales.orders")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sales")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sales")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sales")

PIPELINE_TIMEOUT_SECONDS = float(os.getenv("PIPELINE_TIMEOUT_SECONDS", "120"))
POLL_INTERVAL_SECONDS = 1.0
