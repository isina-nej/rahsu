"""Route predictions, model provenance and input snapshots."""
from django.conf import settings
from django.contrib.gis.db import models

class RouteRequest(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    origin = models.PointField(srid=4326, geography=True)
    destination = models.PointField(srid=4326, geography=True)
    scenario = models.JSONField(default=dict)
    route_provider = models.CharField(max_length=32, default='osrm')
    source_version = models.CharField(max_length=120, blank=True)

class RoutePrediction(models.Model):
    request = models.ForeignKey(RouteRequest, related_name='predictions', on_delete=models.CASCADE)
    geometry = models.LineStringField(srid=4326)
    distance_m = models.FloatField()
    duration_s = models.FloatField()
    baseline_l = models.FloatField()
    estimated_l = models.FloatField()
    idle_l = models.FloatField()
    propulsion_l = models.FloatField()
    model_version = models.CharField(max_length=64)
    warnings = models.JSONField(default=list)
    assumptions = models.JSONField(default=dict)
