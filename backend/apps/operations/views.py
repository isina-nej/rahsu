"""Public readiness and restricted, read-only log search proxy."""
import hmac
import os
import httpx
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

class LiveView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'status': 'live'})

class ReadyView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            connection.ensure_connection()
        except Exception:
            return Response({'status': 'not_ready'}, status=503)
        return Response({'status': 'ready'})

class VersionView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'name':'rahsu','version':'0.1.0','scope':'Tehran/Pride','model':'physics-prototype-0.1'})

class LogsView(APIView):
    """Requires a dedicated API token; never exposes arbitrary Loki selectors."""
    permission_classes = [AllowAny]
    def get(self, request):
        configured = os.getenv('OPS_READ_TOKEN', '')
        supplied = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        if not configured or not hmac.compare_digest(supplied, configured):
            return Response({'error':'unauthorized'}, status=401)
        limit = min(max(int(request.query_params.get('limit', '50')),1),200) if request.query_params.get('limit', '50').isdigit() else 50
        level = request.query_params.get('level', 'error').lower()
        if level not in ('error','warning','info','debug'):
            return Response({'error':'invalid_level'},status=400)
        query = '{service="rahsu-api"} | json | level="'+level.upper()+'"'
        from django.conf import settings
        try:
            with httpx.Client(timeout=4.0) as client:
                response = client.get(settings.LOKI_BASE_URL+'/loki/api/v1/query_range',params={'query':query,'limit':limit})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return Response({'error':'logs_unavailable'},status=503)
        return Response({'data':data.get('data',{}),'limit':limit})
