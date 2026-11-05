from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import VehicleVariant

class VehicleListView(APIView):
    permission_classes=[AllowAny]
    def get(self, request):
        return Response({'results':list(VehicleVariant.objects.values('slug','name_fa','engine_cc','curb_mass_kg','reference_urban_l100','calibrated'))})
