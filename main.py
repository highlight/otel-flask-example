from flask import Flask, request, jsonify
from functools import wraps
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from datetime import datetime, timedelta
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import Span
from typing import List, Any

import os
import requests

from o11y import create_logger, create_tracer, get_meter

service_name = "flask-backend"
# Initialize observability tools
logger = create_logger(service_name, os.getenv("ENVIRONMENT"), local_debug=False)
tracer = create_tracer(service_name, os.getenv("ENVIRONMENT"), local_debug=False)
meter = get_meter(service_name, os.getenv("ENVIRONMENT"), local_debug=False)

histogram = meter.create_histogram("request_duration_histogram")
gauge = meter.create_gauge("request_duration_gauge")
counter = meter.create_counter("request_count")

logger.info("Starting the application")

app = Flask(__name__)

# Your custom decorator
def around_wrapper(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        counter.add(1)
        start_time: datetime = datetime.now()
        logger.info("Before view function")
        result = fn(*args, **kwargs)
        end_time: datetime = datetime.now()
        time_delta: timedelta = end_time - start_time
        histogram.record(time_delta.total_seconds())
        gauge.set(time_delta.total_seconds())
        logger.info("After view function")
        return result
    return wrapped

FlaskInstrumentor().instrument_app(app, excluded_urls="")

RequestsInstrumentor().instrument()

@app.route("/", methods=["GET"])
@around_wrapper
def health():
    logger.info("Endpoint called")
    response = requests.get("http://httpbin.org/headers")
    logger.info(f"Dummy request's headers: {response.json()}")
    return jsonify({"response": "hi", "status_code": 200})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)