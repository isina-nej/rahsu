"""Live PostGIS API smoke tests with a fake routing adapter and local obstacles."""
from unittest.mock import patch
import pytest
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.geo.models import Obstacle
from apps.routing.osrm import RouteCandidate
from domain.route_factors import RoadStep

ROUTE=((51.300,35.700),(51.310,35.700))

@pytest.mark.django_db
def test_estimate_returns_real_adapter_geometry_and_obstacle_evidence(settings):
    settings.ELEVATION_BASE_URL=""
    Obstacle.objects.create(kind='bump',location=Point(51.305,35.7,srid=4326),
       source='manual',verified=True,road_name='خیابان آزادی',direction='both')
    Obstacle.objects.create(kind='traffic_signals',location=Point(51.307,35.7,srid=4326),
       source='osm',verified=False)
    route=RouteCandidate(940,110,ROUTE,(RoadStep('خیابان آزادی',ROUTE),))
    with patch('apps.routing.views.OsrmClient') as client:
        client.return_value.candidates.return_value=[route]
        response=APIClient().post('/api/v1/estimates/',{
            'origin':{'lat':35.7,'lon':51.3},'destination':{'lat':35.7,'lon':51.31},
            'passengers':2},format='json')
    assert response.status_code==200,response.content
    body=response.json()
    assert body['routes'][0]['obstacle_summary']['reviewed_applied']==1
    assert body['routes'][0]['obstacle_summary']['nearby']==2
    assert body['routes'][0]['terrain'] is None
    assert 'grade_not_measured' in body['routes'][0]['warnings']
    assert body['routes'][0]['estimated_l']>0

@pytest.mark.django_db
def test_invalid_out_of_scope_coordinates_rejected():
    response=APIClient().post('/api/v1/estimates/',{
        'origin':{'lat':32,'lon':51.3},'destination':{'lat':35.7,'lon':51.31}},format='json')
    assert response.status_code==400
