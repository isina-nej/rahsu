from django.db import migrations,models

class Migration(migrations.Migration):
    dependencies=[('calibration','0001_initial'),('routing','0001_initial')]
    operations=[migrations.AddField(model_name='observedtrip',name='prediction',
        field=models.ForeignKey(to='routing.routeprediction',null=True,blank=True,
            on_delete=models.PROTECT))]
