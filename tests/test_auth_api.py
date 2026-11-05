import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_csrf_protected_session_login():
    User=get_user_model()
    User.objects.create_user(username='driver123',password='Long-Secret-For-Testing-123!')
    client=APIClient(enforce_csrf_checks=True)
    token=client.get('/api/v1/auth/csrf/').json()['csrfToken']
    no_csrf=client.post('/api/v1/auth/login/',{'username':'driver123',
                 'password':'Long-Secret-For-Testing-123!'},format='json')
    assert no_csrf.status_code==403
    logged=client.post('/api/v1/auth/login/',{'username':'driver123',
                'password':'Long-Secret-For-Testing-123!'},format='json',HTTP_X_CSRFTOKEN=token)
    assert logged.status_code==200,logged.content
    assert client.get('/api/v1/auth/me/').json()['authenticated'] is True

@pytest.mark.django_db
def test_signup_default_closed(monkeypatch):
    monkeypatch.delenv('ALLOW_PUBLIC_SIGNUP',raising=False)
    c=APIClient()
    r=c.post('/api/v1/auth/register/',{'username':'hello',
              'password':'Valid-Secret-For-Testing-123!'},format='json')
    assert r.status_code==403
