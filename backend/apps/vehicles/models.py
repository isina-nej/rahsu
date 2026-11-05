"""Vehicle facts and calibration hypotheses. Use nullable values for unknown facts."""
from django.db import models

class VehicleVariant(models.Model):
    slug = models.SlugField(unique=True)
    name_fa = models.CharField(max_length=120)
    engine_cc = models.PositiveSmallIntegerField(null=True, blank=True)
    curb_mass_kg = models.FloatField(null=True, blank=True)
    reference_urban_l100 = models.FloatField(null=True, blank=True)
    cd = models.FloatField(null=True, blank=True)
    frontal_area_m2 = models.FloatField(null=True, blank=True)
    rolling_resistance = models.FloatField(null=True, blank=True)
    drivetrain_efficiency = models.FloatField(null=True, blank=True)
    engine_efficiency = models.FloatField(null=True, blank=True)
    idle_lph = models.FloatField(null=True, blank=True)
    source_note = models.TextField(blank=True)
    calibrated = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_fa
