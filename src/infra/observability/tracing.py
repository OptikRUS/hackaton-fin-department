from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config.settings import settings


def setup_tracing() -> None:
    resource = Resource.create(
        attributes={
            "service.name": settings.APP.NAME,
            "service.version": settings.APP.VERSION,
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL.ENDPOINT,
        timeout=settings.OTEL.TIMEOUT,
        insecure=True,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)
