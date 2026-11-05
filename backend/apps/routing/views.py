"""End-to-end initial estimate; only genuine OSRM routes, never fabricated alternatives."""
import logging
from django.conf import settings
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from domain.fuel import VehicleParameters, baseline_liters, estimate_physics
from domain.motion import simulate_motion
from .osrm import OsrmClient,RoutingError

log=logging.getLogger(__name__)

class CoordinatesSerializer(serializers.Serializer):
    lat=serializers.FloatField(min_value=35.45,max_value=35.95)
    lon=serializers.FloatField(min_value=51.05,max_value=51.75)

class EstimateSerializer(serializers.Serializer):
    origin=CoordinatesSerializer()
    destination=CoordinatesSerializer()
    passengers=serializers.IntegerField(default=1,min_value=1,max_value=5)
    cargo_kg=serializers.FloatField(default=0,min_value=0,max_value=150)
    ac_on=serializers.BooleanField(default=False)

class EstimateView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        ser=EstimateSerializer(data=request.data);ser.is_valid(raise_exception=True)
        data=ser.validated_data
        start=(data['origin']['lat'],data['origin']['lon']);end=(data['destination']['lat'],data['destination']['lon'])
        if start==end:return Response({'error':'origin_equals_destination'},status=400)
        try:routes=OsrmClient(settings.OSRM_BASE_URL).candidates(start,end)
        except RoutingError as exc:
            log.warning('routing.error code=%s',str(exc))
            return Response({'error':str(exc)},status=503 if str(exc)=='routing_provider_unavailable' else 422)
        if not routes:return Response({'error':'no_route'},status=422)
        # Parameters below are engineering placeholders, NOT measured Pride specifications.
        params=VehicleParameters(mass_kg=915+75*data['passengers']+data['cargo_kg'],cd=0.35,frontal_area_m2=1.85,rolling_resistance=.013,drivetrain_efficiency=.86,engine_efficiency=.19,idle_lph=.75+(0.20 if data['ac_on'] else 0),reference_urban_l100=9.5)
        result=[]
        for i,route in enumerate(routes[:3]):
            if route.distance_m>100000 or route.duration_s>36000:continue
            samples=simulate_motion(route.distance_m,route.duration_s,dt_s=2.0)
            fuel=estimate_physics(samples,params)
            result.append({'index':i,'distance_m':route.distance_m,'osrm_duration_s':route.duration_s,'modeled_duration_s':fuel.duration_s,'geometry':{'type':'LineString','coordinates':route.coordinates},'baseline_l':round(baseline_liters(route.distance_m,9.5),4),'estimated_l':round(fuel.liters,4),'idle_l':round(fuel.idle_liters,4),'propulsion_l':round(fuel.propulsion_liters,4),'warnings':[ *fuel.warnings,'obstacles_not_applied','grade_not_applied','tehran_traffic_unavailable'],'model_version':fuel.model_version})
        return Response({'vehicle':'pride-131','scope':'tehran','routes':result,'research_only':True})
