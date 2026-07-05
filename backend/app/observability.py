import logging
import os

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pythonjsonlogger import jsonlogger



def setup_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def setup_tracing(app):
    enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    if enabled:
        FastAPIInstrumentor.instrument_app(app)
