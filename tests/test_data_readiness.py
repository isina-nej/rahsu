from unittest.mock import patch
import httpx
import pytest
from rest_framework.test import APIClient
from apps.operations.models import OpsAccessEvent

pytestmark = pytest.mark.django_db


def test_readiness_rejects_anonymous_user():
    response = APIClient().get('/api/v1/admin/observability/readiness')
    assert response.status_code == 401
    assert OpsAccessEvent.objects.filter(operation='data',
                                         auth_method='denied').exists()


def test_missing_osrm_is_visible_without_false_accuracy_claim(monkeypatch):
    monkeypatch.setenv('OPS_READ_TOKEN', 'x'*48)
    with patch('apps.operations.readiness.httpx.get',
               side_effect=httpx.ConnectError('unavailable')):
        response = APIClient().get(
            '/api/v1/admin/observability/readiness',
            HTTP_AUTHORIZATION='Bearer '+'x'*48)
    assert response.status_code == 200
    assert response.data['routing']['osrm_reachable'] is False
    assert response.data['fuel_accuracy_claimed'] is False
    assert response.data['software_data_ready'] is False
