"""Transaction-safe moderator workflow; never overwrite audited revisions."""
from django.db import transaction
from django.utils import timezone
from .models import Obstacle,ObstacleReport,ObstacleRevision


def _snapshot(obj):
    if obj is None:return {}
    return {'id':obj.pk,'kind':obj.kind,'lon':obj.location.x,'lat':obj.location.y,
            'verified':obj.verified,'source':obj.source,
            'road_name':obj.road_name,'direction':obj.direction}


@transaction.atomic
def decide_report(report_id: int, reviewer, approve: bool) -> ObstacleReport:
    if not reviewer or not reviewer.is_active or not reviewer.is_staff:
        raise PermissionError('staff_required')
    report=ObstacleReport.objects.select_for_update().get(pk=report_id)
    if report.status != 'pending':
        raise ValueError('report_already_reviewed')
    obstacle=None
    if report.obstacle_id:
        obstacle=Obstacle.objects.select_for_update().filter(pk=report.obstacle_id).first()
    if report.action in ('remove','correct') and obstacle is None:
        raise ValueError('obstacle_not_found')
    before=_snapshot(obstacle)
    if approve:
        if report.action == 'add':
            obstacle=Obstacle.objects.create(kind=report.kind,location=report.location,
                verified=True,source='manual',road_name=report.road_name,
                direction=report.direction)
            report.obstacle=obstacle
        elif report.action == 'correct':
            obstacle.kind=report.kind
            obstacle.location=report.location
            obstacle.source='manual'
            obstacle.verified=True
            obstacle.road_name=report.road_name
            obstacle.direction=report.direction
            obstacle.save(update_fields=['kind','location','source','verified','road_name','direction','updated_at'])
        elif report.action == 'remove':
            # Keep tombstones, so future OSM imports do NOT resurrect deletions.
            obstacle.source='removed'
            obstacle.verified=True
            obstacle.save(update_fields=['source','verified','updated_at'])
        report.status='approved'
    else:
        report.status='rejected'
    report.reviewer=reviewer
    report.reviewed_at=timezone.now()
    report.save(update_fields=['obstacle','status','reviewer','reviewed_at'])
    ObstacleRevision.objects.create(
        report=report,obstacle=obstacle,reviewer=reviewer,
        before=before,after=_snapshot(obstacle))
    return report
