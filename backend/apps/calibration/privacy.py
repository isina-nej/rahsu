"""Subject-controlled deletion of consenting research data."""
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.calibration.models import ObservedTrip
from apps.routing.models import RouteRequest


class DeleteStudyDataView(APIView):
    permission_classes=[IsAuthenticated]

    @transaction.atomic
    def delete(self,request):
        if request.data.get('confirmation')!='DELETE_MY_STUDY_DATA':
            return Response({'error':'explicit_confirmation_required'},status=400)
        # Observations PROTECT predictions. Delete them first.
        obs_count=ObservedTrip.objects.filter(user=request.user).count()
        ObservedTrip.objects.filter(user=request.user).delete()
        route_count=RouteRequest.objects.filter(user=request.user).count()
        RouteRequest.objects.filter(user=request.user).delete()
        return Response({'deleted_observations':obs_count,'deleted_route_requests':route_count,
                         'status':'deleted'})
