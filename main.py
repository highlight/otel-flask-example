from flask import Flask, request, jsonify
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

def request_hook(span: Span, request: Any):
    if span and span.is_recording():
        user_id = request.headers.get("user.id", "unknown")
        span.set_attribute("user.id", user_id)

def response_hook(span: Span, status: str, response_headers: List):
    if span and span.is_recording():
        span.set_attribute("custom_user_attribute_from_response_hook", "some-value")
        for header, value in response_headers:
            span.set_attribute(f"http.response.header.{header.lower().replace('-', '_')}", value)
    
FlaskInstrumentor().instrument_app(app, excluded_urls="", request_hook=request_hook, response_hook=response_hook)

RequestsInstrumentor().instrument()

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
    app.run(host="0.0.0.0", port=8000, debug=True)