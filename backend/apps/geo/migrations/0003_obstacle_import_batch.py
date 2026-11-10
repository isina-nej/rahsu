from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('geo', '0002_review_audit')]

    operations = [
        migrations.CreateModel(
            name='ObstacleImportBatch',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('file_sha256', models.CharField(max_length=64, db_index=True)),
                ('source_filename', models.CharField(max_length=128)),
                ('recognized_nodes', models.PositiveIntegerField(default=0)),
                ('created_count', models.PositiveIntegerField(default=0)),
                ('updated_count', models.PositiveIntegerField(default=0)),
                ('reviewed_preserved_count', models.PositiveIntegerField(default=0)),
            ],
            options={'ordering': ('-created_at',)},
        ),
    ]
