"""Optional tracing setup, off by default and opt-in at runtime."""
import os
from django.apps import AppConfig

class OperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations'

    def ready(self):
        if os.environ.get('OTEL_TRACING_ENABLED') != '1':
            return
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        provider = TracerProvider(resource=Resource.create({'service.name':'rahsu-api'}))
        endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://alloy:4318').rstrip('/') + '/v1/traces'
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, timeout=5)))
        trace.set_tracer_provider(provider)
        DjangoInstrumentor().instrument()
