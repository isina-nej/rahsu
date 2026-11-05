from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.geo.models import Obstacle,ObstacleReport,ObstacleRevision
from apps.geo.review import decide_report
import pytest

@pytest.mark.django_db
def test_mod_decision_tombstone_preserves_osm_id_and_audit():
    User=get_user_model()
    mod=User.objects.create_user(username='mod',password='change-this',is_staff=True)
    submitter=User.objects.create_user(username='reporter',password='change-this')
    original=Obstacle.objects.create(osm_type='node',osm_id=1001,kind='bump',
        location=Point(51.30,35.7,srid=4326),source='osm')
    report=ObstacleReport.objects.create(submitted_by=submitter,obstacle=original,
        action='remove',kind='bump',location=original.location)
    decide_report(report.pk,mod,True)
    original.refresh_from_db();report.refresh_from_db()
    assert original.source=='removed'
    assert report.status=='approved'
    assert ObstacleRevision.objects.get(report=report).before['source']=='osm'
    assert not Obstacle.objects.exclude(source='removed').filter(pk=original.pk).exists()
    with pytest.raises(ValueError,match='already_reviewed'):
        decide_report(report.pk,mod,True)

@pytest.mark.django_db
def test_report_review_api_requires_staff():
    User=get_user_model()
    normal=User.objects.create_user(username='someone',password='change-this')
    admin=User.objects.create_user(username='moderator',password='change-this',is_staff=True)
    request_data={'action':'add','kind':'stop','lat':35.7,'lon':51.3,
      'road_name':'خیابان آزادی','direction':'both'}
    c=APIClient();c.force_authenticate(user=normal)
    created=c.post('/api/v1/obstacle-reports/',request_data,format='json')
    assert created.status_code==201
    report_id=created.json()['id']
    denied=c.patch('/api/v1/admin/obstacle-reports/',{'id':report_id,'decision':'approve'},format='json')
    assert denied.status_code==403
    c.force_authenticate(user=admin)
    approved=c.patch('/api/v1/admin/obstacle-reports/',{'id':report_id,'decision':'approve'},format='json')
    assert approved.status_code==200,approved.content
    obstacle=Obstacle.objects.get(pk=approved.json()['obstacle_id'])
    assert obstacle.road_name=='خیابان آزادی' and obstacle.source=='manual'
    assert ObstacleRevision.objects.count()==1
