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

@pytest.mark.django_db
def test_opt_in_history_creates_owned_predictions(settings):
    from django.contrib.auth import get_user_model
    from apps.routing.models import RouteRequest, RoutePrediction
    user=get_user_model().objects.create_user(username='test_driver',password='not-a-real-secret')
    settings.ELEVATION_BASE_URL=''
    route=RouteCandidate(940,110,ROUTE,(RoadStep('خیابان آزادی',ROUTE),))
    c=APIClient()
    data={'origin':{'lat':35.7,'lon':51.3},'destination':{'lat':35.7,'lon':51.31},
          'save_history':True}
    with patch('apps.routing.views.OsrmClient') as provider:
        provider.return_value.candidates.return_value=[route]
        assert c.post('/api/v1/estimates/',data,format='json').status_code==401
        c.force_authenticate(user=user)
        response=c.post('/api/v1/estimates/',data,format='json')
    assert response.status_code==200,response.content
    assert response.json()['routes'][0]['prediction_id'] is not None
    assert RouteRequest.objects.count()==1
    assert RoutePrediction.objects.count()==1

@pytest.mark.django_db
def test_osrm_annotated_osm_speed_bump_changes_route_scenario(settings, monkeypatch):
    """Full API: real OSRM HTTP parser + OSM node topology + PostGIS + model."""
    settings.ELEVATION_BASE_URL = ''
    for osm_id, kind, lon in ((771,'bump',51.305), (772,'stop',51.307),
                              (773,'hump',51.309)):
        Obstacle.objects.create(
            osm_type='node', osm_id=osm_id, kind=kind, verified=False,
            source='osm',location=Point(lon,35.7,srid=4326))
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {'code':'Ok','routes':[{
                'distance':940, 'duration':110,
                'geometry':{'coordinates':[[51.3,35.7],[51.305,35.7],[51.31,35.7]]},
                'legs':[{'annotation':{'nodes':[100,771,772,200]},
                         'steps':[{'name':'خیابان آزادی','geometry':{
                             'coordinates':[[51.3,35.7],[51.31,35.7]]}}]}]}]}
    def mocked_http(url, params, timeout):
        assert params['annotations']=='nodes'
        return FakeResponse()
    monkeypatch.setattr('apps.routing.osrm.httpx.get',mocked_http)
    response=APIClient().post('/api/v1/estimates/',{
        'origin':{'lat':35.7,'lon':51.3},
        'destination':{'lat':35.7,'lon':51.31}},format='json')
    assert response.status_code==200,response.content
    data=response.json()['routes'][0]
    assert data['obstacle_summary']['nearby']==3
    assert data['obstacle_summary']['total_applied']==1
    assert data['obstacle_summary']['topology_matched_osm_calming']==1
    assert data['obstacle_summary']['reviewed_applied']==0
    assert data['obstacle_summary']['stops']==0
    assert data['obstacle_summary']['slowdowns']==1
    assert sum(o['applied'] for o in data['obstacles'])==1
    assert any(o['reason']=='osm_node_on_traversed_route'
               for o in data['obstacles'])

@pytest.mark.django_db
def test_explicit_opt_in_stores_osm_source_version_for_reproducibility(settings):
    from django.contrib.auth import get_user_model
    from apps.routing.models import RouteRequest
    settings.ELEVATION_BASE_URL=''
    user=get_user_model().objects.create_user(username='map-date-user',
        password='not-a-real-secret')
    route=RouteCandidate(940,110,ROUTE,osm_data_version='2026-10-31T00:00:00Z')
    client=APIClient();client.force_authenticate(user=user)
    with patch('apps.routing.views.OsrmClient') as provider:
        provider.return_value.candidates.return_value=[route]
        result=client.post('/api/v1/estimates/',{
            'origin':{'lat':35.7,'lon':51.3},
            'destination':{'lat':35.7,'lon':51.31},'save_history':True},
            format='json')
    assert result.status_code==200,result.content
    assert RouteRequest.objects.get().source_version=='2026-10-31T00:00:00Z'
    assert result.data['routes'][0]['map_data_version']=='2026-10-31T00:00:00Z'

@pytest.mark.django_db
def test_postgis_corridor_excludes_obstacles_near_bbox_but_off_route():
    from apps.routing.views import _nearby_obstacles
    along=Obstacle.objects.create(kind='bump',osm_type='node',osm_id=991,
        location=Point(51.305,35.7,srid=4326),source='osm')
    Obstacle.objects.create(kind='hump',osm_type='node',osm_id=992,
        location=Point(51.305,35.70022,srid=4326),source='osm')
    route=RouteCandidate(940,110,ROUTE)
    rows=_nearby_obstacles(route)
    assert {x.id for x in rows}=={along.pk}
