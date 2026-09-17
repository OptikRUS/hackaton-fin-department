from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import CollectorRegistry, make_asgi_app
from starlette.types import ASGIApp

from src.config.settings import settings

EXCLUDED_URLS = "health,metrics"


def create_metrics_asgi_app() -> ASGIApp:
    resource = Resource.create(
        attributes={
            "service.name": settings.APP.NAME,
            "service.version": settings.APP.VERSION,
        },
    )
    registry = CollectorRegistry()
    reader = PrometheusMetricReader(registry=registry)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    return make_asgi_app(registry=registry)
