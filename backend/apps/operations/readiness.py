"""Protected data-readiness diagnostics for a genuine Tehran deployment."""
import httpx
from django.conf import settings
from rest_framework.response import Response
from apps.geo.models import Obstacle
from apps.vehicles.models import VehicleVariant
from apps.calibration.models import ObservedTrip
from .views import OpsView


class DataReadinessView(OpsView):
    audit_operation = 'data'

    def get(self, request):
        denied = self.authorized(request)
        if denied is not None:
            return denied
        road_graph = False
        try:
            result = httpx.get(
                settings.OSRM_BASE_URL + '/nearest/v1/driving/51.389,35.689',
                params={'number': 1}, timeout=2.5)
            result.raise_for_status()
            road_graph = result.json().get('code') == 'Ok'
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            pass
        obstacles = Obstacle.objects.exclude(source='removed')
        amount = obstacles.count()
        reviewed = obstacles.filter(verified=True).count()
        pride = VehicleVariant.objects.filter(slug='pride-131').first()
        holdout = ObservedTrip.objects.filter(
            consent_given=True, calibration_split='holdout').count()
        base_ready = bool(pride and road_graph and amount > 0)
        return Response({
            'stage': 'research_uncalibrated' if base_ready else 'missing_prerequisites',
            'routing': {'osrm_reachable': road_graph,
                        'network_coverage_verified': False},
            'obstacles': {'recorded': amount, 'reviewed': reviewed,
                          'city_coverage_verified': False},
            'vehicle': {'pride_seeded': bool(pride),
                        'calibrated': bool(pride and pride.calibrated)},
            'measurement': {'holdout_trips': holdout},
            'providers': {
                'geocoder_configured': bool(settings.GEOCODER_BASE_URL),
                'elevation_configured': bool(settings.ELEVATION_BASE_URL),
                'live_traffic': False,
            },
            'software_data_ready': base_ready,
            'fuel_accuracy_claimed': False,
        })
