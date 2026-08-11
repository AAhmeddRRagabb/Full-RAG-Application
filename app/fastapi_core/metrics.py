from prometheus_client import (
    Counter, 
    Histogram, 
    generate_latest, 
    CONTENT_TYPE_LATEST
)

from fastapi import (
    FastAPI,
    Request,
    Response
)

from starlette.middleware.base import BaseHTTPMiddleware
import time
from helpers.config import get_settings
settings = get_settings()


# Metrics
REQUEST_COUNT = Counter(
    name = "http_total_requests",
    documentation = "Total HTTP Requests",
    labelnames = ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    name = 'http_request_duration_s',
    documentation = "HTTP Request Durations in Seconds",
    labelnames = ['method', 'endpoint']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # process the request
        response = await call_next(request)

        # metrics
        duration = time.time() - start_time
        endpoint = request.url.path

        REQUEST_COUNT.labels(
            method = request.method,
            endpoint = endpoint,
            status = response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method = request.method,
            endpoint = endpoint
        ).observe(duration)


        return response


def setup_metrics(app: FastAPI):
    app.add_middleware(PrometheusMiddleware)

    @app.get(f"/{settings.METRICS_ENDPOINT}", include_in_schema = False)
    def metrics():
        return Response(
            generate_latest(),
            media_type = CONTENT_TYPE_LATEST
        )

