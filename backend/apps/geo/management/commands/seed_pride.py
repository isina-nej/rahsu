from django.core.management.base import BaseCommand
from apps.vehicles.models import VehicleVariant

class Command(BaseCommand):
    help='Seed the initial Tehran Pride 131 research vehicle'
    def handle(self,*args,**kwargs):
        VehicleVariant.objects.update_or_create(slug='pride-131',defaults={
            'name_fa':'پراید ۱۳۱ دنده‌ای','engine_cc':1323,'curb_mass_kg':915,
            'reference_urban_l100':9.5,'cd':None,'frontal_area_m2':None,
            'rolling_resistance':None,'drivetrain_efficiency':None,
            'engine_efficiency':None,'idle_lph':None,'calibrated':False,
            'source_note':'Published reference figures; physics coefficient estimates must be provided separately and calibrated.'})
        self.stdout.write(self.style.SUCCESS('Pride 131 reference seeded'))
