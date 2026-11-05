"""Consent-based reference measurements for later holdout validation."""
from django.conf import settings
from django.db import models

class ObservedTrip(models.Model):
    prediction = models.ForeignKey('routing.RoutePrediction',null=True,blank=True,on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    distance_m = models.FloatField()
    observed_fuel_l = models.FloatField()
    method = models.CharField(max_length=32, choices=[('full_tank','full_tank'),('obd','obd'),('other','other')])
    calibration_split = models.CharField(max_length=10, default='unassigned')
    consent_given = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
