"""Import osmium-exported GeoJSON obstacle nodes; reviewed overlays win."""
import json
from pathlib import Path
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from domain.osm_geojson import parse_obstacle_geojson
from apps.geo.models import Obstacle

class Command(BaseCommand):
    help='Import Tehran obstacle GeoJSON exported by osmium'

    def add_arguments(self,parser):
        parser.add_argument('input_file')

    @transaction.atomic
    def handle(self,input_file,**options):
        path=Path(input_file)
        if not path.is_file() or path.stat().st_size>200_000_000:
            raise CommandError('Missing or oversized GeoJSON file')
        try:
            features=parse_obstacle_geojson(json.loads(path.read_text(encoding='utf-8')))
        except (ValueError,UnicodeError,OSError) as e:
            raise CommandError('Invalid data/provenance in GeoJSON') from e
        added=updated=preserved=0
        for item in features:
            existing=Obstacle.objects.filter(osm_type='node',osm_id=item.osm_id).first()
            if existing and (existing.verified or existing.source in ('manual','removed')):
                preserved+=1
                continue
            _,created=Obstacle.objects.update_or_create(osm_type='node',osm_id=item.osm_id,
                defaults={'kind':item.kind,'location':Point(item.lon,item.lat,srid=4326),
                          'source':'osm','verified':False})
            added+=created
            updated+=not created
        self.stdout.write(self.style.SUCCESS(
            f'Tehran obstacles imported: {added} new; {updated} updated; {preserved} reviewed preserved'))
