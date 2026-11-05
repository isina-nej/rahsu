"""OSM observations and moderated local overlays."""
from django.conf import settings
from django.contrib.gis.db import models

class Obstacle(models.Model):
    TYPE_CHOICES = [(x, x) for x in ('traffic_signals', 'bump', 'hump', 'stop', 'crossing', 'other')]
    kind = models.CharField(max_length=32, choices=TYPE_CHOICES)
    location = models.PointField(srid=4326, geography=True, spatial_index=True)
    osm_type = models.CharField(max_length=16, blank=True)
    osm_id = models.BigIntegerField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    source = models.CharField(max_length=24, default='osm')
    direction = models.CharField(max_length=16, default='unknown')
    road_name = models.CharField(max_length=180, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['osm_type', 'osm_id'], name='unique_osm_obstacle')]

class ObstacleReport(models.Model):
    STATUS = [(x, x) for x in ('pending', 'approved', 'rejected')]
    ACTIONS = [(x, x) for x in ('add', 'correct', 'remove')]
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    obstacle = models.ForeignKey(Obstacle, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=10, choices=ACTIONS)
    kind = models.CharField(max_length=32)
    location = models.PointField(srid=4326, geography=True)
    note = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default='pending')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='reviewed_reports', on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
