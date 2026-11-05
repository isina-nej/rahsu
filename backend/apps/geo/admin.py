from django.contrib import admin
from .models import Obstacle, ObstacleReport, ObstacleRevision
from .review import decide_report

@admin.register(Obstacle)
class ObstacleAdmin(admin.ModelAdmin):
    list_display=('id','kind','road_name','direction','source','verified','updated_at')
    list_filter=('kind','verified','source','direction')
    search_fields=('road_name',)

@admin.register(ObstacleReport)
class ObstacleReportAdmin(admin.ModelAdmin):
    list_display=('id','action','kind','road_name','direction','status','created_at')
    list_filter=('status','kind','action')
    readonly_fields=('submitted_by','reviewer','reviewed_at','created_at')
    actions=['approve_reports','reject_reports']

    @admin.action(description='Approve selected reports (record revision)')
    def approve_reports(self,request,queryset):
        for report in queryset.filter(status='pending'):
            decide_report(report.pk,request.user,True)

    @admin.action(description='Reject selected reports (record revision)')
    def reject_reports(self,request,queryset):
        for report in queryset.filter(status='pending'):
            decide_report(report.pk,request.user,False)

@admin.register(ObstacleRevision)
class ObstacleRevisionAdmin(admin.ModelAdmin):
    list_display=('id','report','reviewer','created_at')
    readonly_fields=('report','obstacle','reviewer','before','after','created_at')
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
