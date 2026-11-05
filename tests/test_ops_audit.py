import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.operations.models import OpsAccessEvent

@pytest.mark.django_db
def test_unauthorized_logs_access_is_audited():
    response=APIClient().get('/api/v1/admin/observability/logs')
    assert response.status_code==401
    event=OpsAccessEvent.objects.get(operation='logs')
    assert event.auth_method=='denied'
    assert event.response_status==401 and event.user_id is None
    assert len(event.request_id)==32

@pytest.mark.django_db
def test_service_token_does_not_leak_or_allow_audit_read(monkeypatch):
    secret='a'*64
    monkeypatch.setenv('OPS_READ_TOKEN',secret)
    client=APIClient()
    response=client.get('/api/v1/admin/observability/logs',
              {'service':'injected'},HTTP_AUTHORIZATION='Bearer '+secret)
    assert response.status_code==400
    event=OpsAccessEvent.objects.get(operation='logs')
    assert event.auth_method=='token'
    assert secret not in str(event.__dict__)
    response=client.get('/api/v1/admin/observability/audit',
              HTTP_AUTHORIZATION='Bearer '+secret)
    assert response.status_code in (401,403)

@pytest.mark.django_db
def test_staff_can_review_bounded_audit():
    user=get_user_model().objects.create_user(username='audit-admin',
          password='example-password-1234',is_staff=True)
    client=APIClient()
    client.force_authenticate(user=user)
    response=client.get('/api/v1/admin/observability/logs',{'level':'invalid'})
    assert response.status_code==400
    result=client.get('/api/v1/admin/observability/audit')
    assert result.status_code==200
    assert result.data['results'][0]['actor']=='audit-admin'
    assert result.data['results'][0]['operation']=='logs'
    assert OpsAccessEvent.objects.count()==2
