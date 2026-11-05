from unittest.mock import patch
import pytest
from rest_framework.test import APIClient

pytestmark=pytest.mark.django_db

def test_log_proxy_requires_token(settings):
    r=APIClient().get('/api/v1/admin/observability/logs')
    assert r.status_code==401

def test_malicious_query_filter_cannot_be_injected(monkeypatch,settings):
    monkeypatch.setenv('OPS_READ_TOKEN','x'*40)
    r=APIClient().get('/api/v1/admin/observability/logs',
      {'service':'api"} |= "secret','level':'error'},
      HTTP_AUTHORIZATION='Bearer '+'x'*40)
    assert r.status_code==400

def test_trace_id_must_be_hex(monkeypatch):
    monkeypatch.setenv('OPS_READ_TOKEN','x'*40)
    r=APIClient().get('/api/v1/admin/observability/traces/any-string',
      HTTP_AUTHORIZATION='Bearer '+'x'*40)
    assert r.status_code==400

def test_only_24_hour_window_allowed(monkeypatch):
    monkeypatch.setenv('OPS_READ_TOKEN','x'*40)
    r=APIClient().get('/api/v1/admin/observability/logs',
      {'start':'2026-10-01T00:00:00Z','end':'2026-11-01T00:00:00Z'},
      HTTP_AUTHORIZATION='Bearer '+'x'*40)
    assert r.status_code==400
