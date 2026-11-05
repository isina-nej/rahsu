from django.conf import settings
from django.db import migrations,models
class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name='ObservedTrip',fields=[('id',models.BigAutoField(primary_key=True,serialize=False)),('created_at',models.DateTimeField(auto_now_add=True)),('distance_m',models.FloatField()),('observed_fuel_l',models.FloatField()),('method',models.CharField(choices=[('full_tank','full_tank'),('obd','obd'),('other','other')],max_length=32)),('calibration_split',models.CharField(default='unassigned',max_length=10)),('consent_given',models.BooleanField(default=False)),('notes',models.TextField(blank=True)),('user',models.ForeignKey(on_delete=models.PROTECT,to=settings.AUTH_USER_MODEL))])]
