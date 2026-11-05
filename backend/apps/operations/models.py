"""Metadata-only audit of sensitive monitoring access."""
from django.conf import settings
from django.db import models

class OpsAccessEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    operation = models.CharField(max_length=12)
    auth_method = models.CharField(max_length=12)
    response_status = models.PositiveSmallIntegerField()
    request_id = models.CharField(max_length=32, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='rahsu_observability_accesses',
        on_delete=models.SET_NULL)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['operation', '-created_at'], name='ops_access_operation_idx'),
            models.Index(fields=['response_status', '-created_at'], name='ops_access_status_idx'),
        ]
