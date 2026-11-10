"""Django/PostGIS check: real importer history and reviewed overrides."""
import hashlib
import json

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command, CommandError

from apps.geo.models import Obstacle, ObstacleImportBatch


pytestmark=pytest.mark.django_db


def fixture_payload():
    return {'type':'FeatureCollection','features':[
        {'type':'Feature','properties':{'@id':'node/801','traffic_calming':'bump'},
         'geometry':{'type':'Point','coordinates':[51.39,35.70]}},
        {'type':'Feature','properties':{'@id':'node/802','highway':'stop'},
         'geometry':{'type':'Point','coordinates':[51.40,35.71]}},
    ]}


def test_import_writes_checksum_counts_and_preserves_reviewed(tmp_path):
    path=tmp_path/'tehran-obstacles.geojson'
    payload=json.dumps(fixture_payload(),ensure_ascii=False).encode('utf-8')
    path.write_bytes(payload)
    call_command('import_osm_geojson',str(path))
    batch=ObstacleImportBatch.objects.get()
    assert batch.file_sha256==hashlib.sha256(payload).hexdigest()
    assert batch.source_filename=='tehran-obstacles.geojson'
    assert batch.recognized_nodes==2 and batch.created_count==2
    reviewed=Obstacle.objects.get(osm_id=801)
    reviewed.source='manual'
    reviewed.verified=True
    reviewed.save()
    call_command('import_osm_geojson',str(path))
    newest=ObstacleImportBatch.objects.first()
    assert newest.created_count==0
    assert newest.updated_count==1
    assert newest.reviewed_preserved_count==1
    assert Obstacle.objects.get(osm_id=801).source=='manual'
    assert ObstacleImportBatch.objects.count()==2


def test_empty_or_unknown_osm_input_fails_closed(tmp_path):
    path=tmp_path/'empty.geojson'
    path.write_text('{"type":"FeatureCollection","features":[]}',encoding='utf-8')
    with pytest.raises(CommandError):
        call_command('import_osm_geojson',str(path))
    assert ObstacleImportBatch.objects.count()==0
