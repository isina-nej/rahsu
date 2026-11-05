"""Exporter namespace. Future counters must avoid user IDs and coordinates in labels."""
from prometheus_client import Counter,Histogram
request_count=Counter('rahsu_http_requests_total','HTTP requests',('method','status'))
request_latency=Histogram('rahsu_http_duration_seconds','Request duration')
