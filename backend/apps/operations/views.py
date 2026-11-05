"""Remote read-only observability API.

Fixed allowlists, bounded time windows and independent bearer token.
Never expose arbitrary Loki LogQL or PromQL from a user-controlled input.
"""
import hmac
import logging
import os
import re
from datetime import datetime,timedelta,timezone

import httpx
from django.conf import settings
from django.db import connection, DatabaseError
from .models import OpsAccessEvent
from .logging import request_id
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

log=logging.getLogger('rahsu.ops')
SERVICES={'api','worker','osrm','loki','alloy','prometheus','grafana','tempo'}
LEVELS={'error','warning','info','debug'}
HEX32=re.compile(r'^[0-9a-f]{32}$')
METRIC_QUERIES={
    'requests_rate':'sum(rate(rahsu_http_requests_total[5m]))',
    'errors_rate':'sum(rate(rahsu_http_requests_total{status=~"5.."}[5m]))',
    'p95_latency_seconds':'histogram_quantile(0.95,sum(rate(rahsu_http_duration_seconds_bucket[5m])) by (le))',
    'api_up':'up{job="api-health"}',
}


def ops_authorized(request):
    if request.user.is_authenticated and request.user.is_staff:
        return True
    expected=os.getenv('OPS_READ_TOKEN','')
    authorization=request.headers.get('Authorization','')
    supplied=authorization[7:] if authorization.startswith('Bearer ') else ''
    return bool(expected and len(expected)>=32 and
       hmac.compare_digest(supplied,expected))


class OpsRateThrottle(SimpleRateThrottle):
    scope='ops'

    def get_cache_key(self,request,view):
        return self.cache_format % {'scope':self.scope,
                                    'ident':self.get_ident(request)}

class OpsView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[OpsRateThrottle]
    audit_operation='logs'

    def finalize_response(self,request,response,*args,**kwargs):
        result=super().finalize_response(request,response,*args,**kwargs)
        actor=request.user if request.user.is_authenticated and request.user.is_staff else None
        method='staff' if actor else ('token' if ops_authorized(request) else 'denied')
        try:
            OpsAccessEvent.objects.create(
                operation=self.audit_operation,auth_method=method,
                response_status=result.status_code,request_id=request_id.get(),user=actor)
        except DatabaseError:
            log.error('ops.audit.write_failed operation=%s',self.audit_operation)
        return result

    def authorized(self,request):
        if not ops_authorized(request):
            return Response({'error':'unauthorized'},status=401)
        return None


class LiveView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        return Response({'status':'live'})


class ReadyView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        try:
            connection.ensure_connection()
        except Exception:
            return Response({'status':'not_ready'},status=503)
        return Response({'status':'ready'})


class VersionView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        return Response({'name':'rahsu','version':'0.2.0','scope':'Tehran/Pride',
                         'model':'physics-prototype-0.1'})


def _date(raw,default):
    if not raw:return default
    dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Timezone required')
    return dt.astimezone(timezone.utc)


class LogsView(OpsView):
    def get(self,request):
        denied=self.authorized(request)
        if denied is not None:return denied
        service=request.query_params.get('service','api')
        level=request.query_params.get('level','error').lower()
        try:
            limit=int(request.query_params.get('limit','50'))
            now=datetime.now(timezone.utc)
            start=_date(request.query_params.get('start'),now-timedelta(hours=1))
            end=_date(request.query_params.get('end'),now)
            if not 1<=limit<=200 or not(start<end<=now+timedelta(minutes=1)):
                raise ValueError
            if end-start>timedelta(hours=24):raise ValueError
        except (ValueError,TypeError):
            return Response({'error':'invalid_time_window_or_limit'},status=400)
        if service not in SERVICES or level not in LEVELS:
            return Response({'error':'invalid_filter'},status=400)
        trace_id=request.query_params.get('trace_id','').lower()
        request_id=request.query_params.get('request_id','').lower()
        if (trace_id and not HEX32.fullmatch(trace_id)) or (request_id and not HEX32.fullmatch(request_id)):
            return Response({'error':'invalid_correlation_id'},status=400)
        query='{service="'+service+'"} | json | level="'+level.upper()+'"'
        if trace_id:query+=' | trace_id="'+trace_id+'"'
        if request_id:query+=' | request_id="'+request_id+'"'
        try:
            response=httpx.get(settings.LOKI_BASE_URL+'/loki/api/v1/query_range',
                params={'query':query,'start':start.isoformat(),'end':end.isoformat(),
                        'limit':limit,'direction':'backward'},timeout=6.0)
            response.raise_for_status()
            data=response.json()
            if data.get('status')!='success':raise ValueError
        except (httpx.HTTPError,ValueError,TypeError):
            return Response({'error':'logs_unavailable'},status=503)
        log.info('ops.logs.read service=%s level=%s limit=%s',service,level,limit)
        return Response({'data':data.get('data',{}),'filters':{
            'service':service,'level':level,'start':start.isoformat(),'end':end.isoformat()},
            'limit':limit})


class MetricsSummaryView(OpsView):
    audit_operation='metrics'
    def get(self,request):
        denied=self.authorized(request)
        if denied is not None:return denied
        base=getattr(settings,'PROMETHEUS_BASE_URL','').rstrip('/')
        if not base:return Response({'error':'prometheus_not_configured'},status=503)
        result={}
        try:
            with httpx.Client(timeout=4.0) as client:
                for key,query in METRIC_QUERIES.items():
                    resp=client.get(base+'/api/v1/query',params={'query':query})
                    resp.raise_for_status()
                    parsed=resp.json()
                    rows=parsed.get('data',{}).get('result',[])
                    result[key]=float(rows[0]['value'][1]) if rows else None
        except (httpx.HTTPError,ValueError,TypeError,KeyError,IndexError):
            return Response({'error':'prometheus_unavailable'},status=503)
        log.info('ops.metrics.read')
        return Response({'metrics':result,'queries':'fixed_allowlist'})


class TraceView(OpsView):
    audit_operation='trace'
    def get(self,request,trace_id):
        denied=self.authorized(request)
        if denied is not None:return denied
        if not HEX32.fullmatch(trace_id.lower()):
            return Response({'error':'invalid_trace_id'},status=400)
        base=getattr(settings,'TEMPO_BASE_URL','').rstrip('/')
        if not base:return Response({'error':'tempo_not_configured'},status=503)
        try:
            response=httpx.get(base+'/api/traces/'+trace_id.lower(),
                headers={'Accept':'application/json'},timeout=6.0)
            if response.status_code==404:
                return Response({'error':'trace_not_found'},status=404)
            response.raise_for_status()
            data=response.json()
        except (httpx.HTTPError,ValueError):
            return Response({'error':'tempo_unavailable'},status=503)
        log.info('ops.trace.read')
        return Response({'trace_id':trace_id.lower(),'trace':data})

class AuditAccessView(OpsView):
    """Staff-only, bounded, metadata-only audit trail."""
    permission_classes=[IsAdminUser]
    audit_operation='audit'

    def get(self,request):
        rows=OpsAccessEvent.objects.select_related('user').order_by('-created_at')[:100]
        return Response({'results':[
            {'id':x.pk,'created_at':x.created_at,'operation':x.operation,
             'auth_method':x.auth_method,'response_status':x.response_status,
             'request_id':x.request_id,'actor':x.user.get_username() if x.user else None}
            for x in rows],'limit':100})
