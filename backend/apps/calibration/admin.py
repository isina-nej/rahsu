from django.contrib import admin
from .models import ObservedTrip

@admin.register(ObservedTrip)
class ObservedTripAdmin(admin.ModelAdmin):
    list_display=('id','user','prediction','method','consent_given','calibration_split','created_at')
    list_filter=('consent_given','method','calibration_split')
    readonly_fields=('user','prediction','observed_fuel_l','distance_m','method','consent_given','created_at')
    actions=['assign_holdout','assign_training']

    @admin.action(description='Assign to independent holdout')
    def assign_holdout(self,request,queryset):
        queryset.filter(consent_given=True,calibration_split='unassigned').update(calibration_split='holdout')

    @admin.action(description='Assign to training set')
    def assign_training(self,request,queryset):
        queryset.filter(consent_given=True,calibration_split='unassigned').update(calibration_split='training')
