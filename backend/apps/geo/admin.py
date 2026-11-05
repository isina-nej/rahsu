from django.contrib import admin
from django.utils import timezone
from .models import Obstacle,ObstacleReport

@admin.register(Obstacle)
class ObstacleAdmin(admin.ModelAdmin):
    list_display=('id','kind','source','verified','updated_at')
    list_filter=('kind','verified','source')

@admin.register(ObstacleReport)
class ObstacleReportAdmin(admin.ModelAdmin):
    list_display=('id','action','kind','status','created_at')
    list_filter=('status','kind','action')
    readonly_fields=('submitted_by','reviewer','reviewed_at','created_at')
    actions=['approve_reports','reject_reports']
    @admin.action(description='Approve selected reports (review only)')
    def approve_reports(self,request,queryset):
        for report in queryset.filter(status='pending'):
            if report.action=='add':
                Obstacle.objects.create(kind=report.kind,location=report.location,source='manual',verified=True)
            elif report.action=='remove' and report.obstacle:
                report.obstacle.verified=False
                report.obstacle.save(update_fields=['verified'])
            elif report.action=='correct' and report.obstacle:
                report.obstacle.kind=report.kind
                report.obstacle.location=report.location
                report.obstacle.verified=True
                report.obstacle.save(update_fields=['kind','location','verified'])
            report.status='approved'; report.reviewer=request.user; report.reviewed_at=timezone.now()
            report.save(update_fields=['status','reviewer','reviewed_at'])
    @admin.action(description='Reject selected reports')
    def reject_reports(self,request,queryset):
        queryset.filter(status='pending').update(status='rejected',reviewer=request.user,reviewed_at=timezone.now())
