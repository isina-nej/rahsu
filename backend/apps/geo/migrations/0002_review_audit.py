from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('geo','0001_initial'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AddField(model_name='obstaclereport',name='road_name',
            field=models.CharField(blank=True,max_length=180)),
        migrations.AddField(model_name='obstaclereport',name='direction',
            field=models.CharField(default='unknown',max_length=16)),
        migrations.CreateModel(name='ObstacleRevision',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('before',models.JSONField(default=dict)),('after',models.JSONField(default=dict)),
            ('created_at',models.DateTimeField(auto_now_add=True)),
            ('obstacle',models.ForeignKey(null=True,on_delete=models.SET_NULL,to='geo.obstacle')),
            ('report',models.OneToOneField(on_delete=models.PROTECT,to='geo.obstaclereport')),
            ('reviewer',models.ForeignKey(on_delete=models.PROTECT,to=settings.AUTH_USER_MODEL))])
    ]
