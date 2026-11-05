import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.routing.models import RouteRequest

@pytest.mark.django_db
def test_delete_own_research_data_only_with_confirmation():
    User=get_user_model()
    user=User.objects.create_user(username='privacy_user',password='Not-A-Secret-Test-12234!')
    other=User.objects.create_user(username='another_privacy_user',password='Not-A-Secret-Test-12234!')
    for owner in (user,other):
        RouteRequest.objects.create(user=owner,
            origin=Point(51.3,35.7,srid=4326),destination=Point(51.4,35.7,srid=4326))
    c=APIClient();c.force_authenticate(user=user)
    assert c.delete('/api/v1/me/study-data/',{},format='json').status_code==400
    r=c.delete('/api/v1/me/study-data/',{'confirmation':'DELETE_MY_STUDY_DATA'},format='json')
    assert r.status_code==200
    assert not RouteRequest.objects.filter(user=user).exists()
    assert RouteRequest.objects.filter(user=other).exists()
