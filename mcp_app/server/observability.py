# mcp_app/server/observability.py
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(service_name: str = "mcp-demo") -> "logger":
    """
    Configure Loguru and route stdlib logging through it.
    """
    level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=level, force=True)

    return logger.bind(service=service_name)


def get_logger(service_name: Optional[str] = None) -> "logger":
    """
    Return a bound Loguru logger for consistent context.
    """
    return logger.bind(service=service_name) if service_name else logger


def setup_tracing(service_name: str = "mcp-demo") -> None:
    """
    Configure OpenTelemetry tracing and export spans via OTLP/HTTP.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "mcp") -> trace.Tracer:
    """
    Return an OpenTelemetry tracer.
    """
    return trace.get_tracer(name)
