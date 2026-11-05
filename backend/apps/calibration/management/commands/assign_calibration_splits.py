"""Stable train/holdout assignment for consented measured trip records."""
import hashlib
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.calibration.models import ObservedTrip


def split_for_request(request_id: int) -> str:
    """All alternative predictions for one request share one split."""
    digest=hashlib.sha256(f'rahsu-split-v1:{request_id}'.encode()).digest()
    value=int.from_bytes(digest[:8],byteorder='big')
    return 'holdout' if value%5==0 else 'train'


class Command(BaseCommand):
    help='Assign unassigned consented trip observations to disjoint splits'

    def add_arguments(self,parser):
        parser.add_argument('--dry-run',action='store_true')

    @transaction.atomic
    def handle(self,*args,**options):
        rows=list(ObservedTrip.objects.filter(
            consent_given=True,calibration_split='unassigned',
            prediction__isnull=False,
        ).select_related('prediction').order_by('pk'))
        tally={'train':0,'holdout':0}
        for row in rows:
            name=split_for_request(row.prediction.request_id)
            row.calibration_split=name
            tally[name]+=1
        if rows and not options['dry_run']:
            ObservedTrip.objects.bulk_update(rows,['calibration_split'],batch_size=500)
        self.stdout.write(
            f"train={tally['train']} holdout={tally['holdout']} dry_run={options['dry_run']}")
