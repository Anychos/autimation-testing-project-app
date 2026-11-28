import os

os.environ.setdefault("POSTGRES_PASSWORD", "unused-test-db-password")
os.environ.setdefault("RABBITMQ_PASSWORD", "unused-test-broker-password")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "unused-test-service-token")
