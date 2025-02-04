from flask import Flask, request, jsonify
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from datetime import datetime, timedelta
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

import os
import requests

from o11y import create_logger, create_tracer, get_meter

service_name = "backend"
# Initialize observability tools
logger = create_logger(service_name, os.getenv("ENVIRONMENT"), local_debug=False)
tracer = create_tracer(service_name, os.getenv("ENVIRONMENT"), local_debug=False)
meter = get_meter(service_name, os.getenv("ENVIRONMENT"), local_debug=False)

histogram = meter.create_histogram("request_duration_histogram")
gauge = meter.create_gauge("request_duration_gauge")
counter = meter.create_counter("request_count")

logger.info("Starting the application")

app = Flask(__name__)

RequestsInstrumentor().instrument()

@app.before_request
def trace_middleware():
    traceparent = TraceContextTextMapPropagator().extract({
        "traceparent": request.headers.get("traceparent")
    })
    request.start_time = datetime.now()
    request.traceparent = traceparent

@app.after_request
def after_request(response):
    with tracer.start_as_current_span(f"{request.method} {request.path}", context=request.traceparent):
        counter.add(1)
        end_time = datetime.now()
        time_delta: timedelta = end_time - request.start_time
        histogram.record(time_delta.total_seconds())
        gauge.set(time_delta.total_seconds())
    return response

@app.route("/", methods=["GET"])
def health():
    logger.info("Endpoint called")
    response = requests.get("http://httpbin.org/headers")
    logger.info(f"Dummy request's headers: {response.json()}")
    return jsonify({"response": "hi", "status_code": 200})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)