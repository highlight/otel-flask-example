import logging
import os
from dotenv import load_dotenv
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics import Counter, Histogram, UpDownCounter
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_ENDPOINT","https://otel.highlight.io:4317")

# read from .env
load_dotenv()

print("OTEL Endpoint is: ", EXPORTER_OTLP_ENDPOINT)
HIGHLIGHT_PROJECT_ID = os.getenv("HIGHLIGHT_PROJECT_ID", "EMPTY")
print("HIGHLIGHT_PROJECT_ID is: ", HIGHLIGHT_PROJECT_ID)

import sys

def create_logger(service_name: str, environment: Optional[str] = "production", local_debug: bool = False) -> logging.Logger:
    if environment is None:
        environment = "production"
    commit = os.getenv("RENDER_GIT_COMMIT", "unknown")
    resource = Resource.create(
        {
            "service.name": service_name,
            "highlight.project_id": HIGHLIGHT_PROJECT_ID,
            "environment": environment,
            "commit": commit
        }
    )

    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    exporter = OTLPLogExporter(endpoint=EXPORTER_OTLP_ENDPOINT, insecure=True) if not local_debug else ConsoleLogExporter()

    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)

    handler = LoggingHandler(level=logging.DEBUG, logger_provider=logger_provider)
    logger.addHandler(handler)

    # Add console handler for stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    if commit:
        formatter = logging.Formatter('commit: ' + commit + ' - %(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def create_tracer(
        service_name: str, 
        environment: Optional[str] = "production", 
        local_debug: bool = False
        ) -> trace.Tracer:
    if environment is None:
        environment = "production"
    commit = os.getenv("RENDER_GIT_COMMIT", "unknown")
    provider = TracerProvider(resource=Resource.create(
        {
            "service.name": service_name,
            "highlight.project_id": HIGHLIGHT_PROJECT_ID,
            "environment": environment,
            "commit": commit
        }
    ))
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=EXPORTER_OTLP_ENDPOINT, insecure=True)) if not local_debug else BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(service_name)

    return tracer

def get_meter(service_name: str, environment: Optional[str] = "production", local_debug: bool = False) -> metrics.Meter:
    if environment is None:
        environment = "production"
    commit = os.getenv("RENDER_GIT_COMMIT", "unknown")


    preferred_temporality: dict[type, AggregationTemporality] = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.DELTA,
            Histogram: AggregationTemporality.DELTA,
    }

    readers = [PeriodicExportingMetricReader(exporter=OTLPMetricExporter(endpoint=EXPORTER_OTLP_ENDPOINT, insecure=True, preferred_temporality=preferred_temporality))]
    if local_debug:
        readers.append(PeriodicExportingMetricReader(exporter=ConsoleMetricExporter(
            preferred_temporality=preferred_temporality
        ), export_interval_millis=1000))

    provider = MeterProvider(resource=Resource.create(
        {
            "service.name": service_name,
            "highlight.project_id": HIGHLIGHT_PROJECT_ID,
            "environment": environment,
            "commit": commit
        }
    ), metric_readers=readers)
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(service_name)
    return meter