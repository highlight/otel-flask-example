# OpenTelemetry Flask Example

This repository is built by [highlight.io](https://highlight.io), an open source observability platform that has both a cloud service and a self-hosted offering. OpenTelemetry is a spec supported by many observability providers, but if you want an opinionated, easy to use, and fully featured observability platform, you can head over to [highlight.io](https://highlight.io).

## What is this repository?

This repository is a simple Flask application that demonstrates how to use OpenTelemetry to instrument a Flask application. For the full guide, see this [blog post](https://www.highlight.io/blog/the-complete-guide-to-python-and-opentelemetry).  

This repository covers:
- [x] Setting up basic logs, traces, and metrics and how to forward this over to an OTEL backend (see `o11y.py`)
- [x] Catching every incoming request using the standard `traceparent` header, and creating a span for each request
- [x] Instrumenting outgoing requests using the `requests` library

## Development Setup

### Prerequisites
- Python 3.8 or higher
- [Poetry](https://python-poetry.org/docs/#installation)

### Installation Steps
1. Clone the repository
2. Configure your `HIGHLIGHT_PROJECT_ID` (or your vendor's specific config) in `o11y.py`
3. Install dependencies:
   ```bash
   poetry install --no-root
   ```

4. Run the app:
   ```bash
   poetry run python main.py
   ```