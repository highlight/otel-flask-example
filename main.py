from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
from starlette.responses import Response
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from datetime import datetime, timedelta
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

import os
import requests
import uvicorn

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

app = FastAPI(debug=True)

RequestsInstrumentor().instrument()

@app.middleware("http")
async def trace_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    traceparent = TraceContextTextMapPropagator().extract({
        "traceparent": request.headers.get("traceparent")
    })
    with tracer.start_as_current_span(f"{request.method} {request.url.path}", context=traceparent):
        counter.add(1)
        start_time = datetime.now()
        response = await call_next(request)
        end_time = datetime.now()
        time_delta: timedelta = end_time - start_time
        histogram.record(time_delta.total_seconds())
        gauge.set(time_delta.total_seconds())
        return response

@app.get("/")
async def health():
    logger.info("Endpoint called")
    response = requests.get("http://httpbin.org/headers")
    logger.info(f"Dummy request's headers: {response.json()}")
    return JSONResponse(content={"response": "hi", "status_code": 200})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)