import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point,LineString
from rest_framework.test import APIClient
from apps.routing.models import RouteRequest,RoutePrediction
from apps.calibration.models import ObservedTrip

@pytest.mark.django_db
def test_consent_and_ownership_bound_to_estimated_route():
    User=get_user_model()
    user=User.objects.create_user(username='driver',password='randompass')
    other=User.objects.create_user(username='otherdriver',password='randompass')
    req=RouteRequest.objects.create(user=user,origin=Point(51.3,35.7,srid=4326),
                                   destination=Point(51.31,35.7,srid=4326))
    pred=RoutePrediction.objects.create(request=req,
        geometry=LineString((51.3,35.7),(51.31,35.7),srid=4326),
        distance_m=900,duration_s=120,baseline_l=.085,
        estimated_l=.1,idle_l=.02,propulsion_l=.08,
        model_version='prototype')
    data={'prediction_id':pred.pk,'distance_m':900,'observed_fuel_l':.11,
          'method':'obd','consent_given':True}
    c=APIClient();c.force_authenticate(user=other)
    assert c.post('/api/v1/trips/observations/',data,format='json').status_code==404
    c.force_authenticate(user=user)
    assert c.post('/api/v1/trips/observations/',{**data,'consent_given':False},format='json').status_code==400
    response=c.post('/api/v1/trips/observations/',data,format='json')
    assert response.status_code==201,response.content
    assert ObservedTrip.objects.count()==1

@pytest.mark.django_db
def test_metrics_stay_private():
    c=APIClient()
    assert c.get('/api/v1/admin/calibration/metrics/').status_code in (401,403)
