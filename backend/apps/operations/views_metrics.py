"""Prometheus exposition; deploy behind a private network."""
from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class MetricsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
