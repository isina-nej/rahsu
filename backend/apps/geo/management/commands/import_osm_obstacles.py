"""Import a *saved* bounded Overpass node export. No uncontrolled API calls."""
import json
from pathlib import Path
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from domain.osm import parse_osm_obstacles
from apps.geo.models import Obstacle

class Command(BaseCommand):
    help = 'Import saved Tehran Overpass JSON nodes (not a live query)'

    def add_arguments(self, parser):
        parser.add_argument('json_file', help='Path to a bounded Overpass JSON export')

    @transaction.atomic
    def handle(self, json_file, **kwargs):
        path = Path(json_file)
        if not path.is_file() or path.stat().st_size > 100_000_000:
            raise CommandError('Input file missing or too large')
        try:
            parsed = parse_osm_obstacles(json.loads(path.read_text(encoding='utf-8')))
        except (ValueError, OSError, UnicodeError) as e:
            raise CommandError('Invalid JSON or obstacle schema') from e
        created = updated = skipped = 0
        for item in parsed:
            existing = Obstacle.objects.filter(osm_type='node',osm_id=item.osm_id).first()
            if existing and (existing.verified or existing.source == 'manual'):
                skipped += 1
                continue
            obj, was_created = Obstacle.objects.update_or_create(
                osm_type='node',osm_id=item.osm_id,
                defaults={'kind': item.kind,'location':Point(item.lon,item.lat,srid=4326),'source':'osm','verified':False},
            )
            created += was_created
            updated += not was_created
        self.stdout.write(f'Imported {created} new; updated {updated}; preserved {skipped} reviewed records.')
