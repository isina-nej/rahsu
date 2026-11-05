from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='OpsAccessEvent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True,
                serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ('operation', models.CharField(max_length=12)),
            ('auth_method', models.CharField(max_length=12)),
            ('response_status', models.PositiveSmallIntegerField()),
            ('request_id', models.CharField(max_length=32, blank=True)),
            ('user', models.ForeignKey(null=True, blank=True,
                related_name='rahsu_observability_accesses',
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ('-created_at',)}),
        migrations.AddIndex(model_name='opsaccessevent',
            index=models.Index(fields=['operation', '-created_at'],name='ops_access_operation_idx')),
        migrations.AddIndex(model_name='opsaccessevent',
            index=models.Index(fields=['response_status', '-created_at'],name='ops_access_status_idx')),
    ]
