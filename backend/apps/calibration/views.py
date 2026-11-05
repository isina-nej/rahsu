"""Consent-based trip records and independent holdout metrics."""
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F
from .models import ObservedTrip
from apps.routing.models import RoutePrediction
from .metrics import fuel_error_metrics


class TripSerializer(serializers.Serializer):
    prediction_id=serializers.IntegerField(min_value=1)
    distance_m=serializers.FloatField(min_value=100,max_value=100_000)
    observed_fuel_l=serializers.FloatField(min_value=.001,max_value=30)
    method=serializers.ChoiceField(choices=['full_tank','obd','other'])
    consent_given=serializers.BooleanField(required=True)
    notes=serializers.CharField(required=False,default='',max_length=500,allow_blank=True)


class ObservedTripView(APIView):
    permission_classes=[IsAuthenticated]

    def get(self,request):
        rows=ObservedTrip.objects.filter(user=request.user).order_by('-created_at')[:100]
        return Response({'results':[{'id':t.pk,'prediction_id':t.prediction_id,
           'distance_m':t.distance_m,'observed_fuel_l':t.observed_fuel_l,
           'method':t.method,'created_at':t.created_at,'split':t.calibration_split}
           for t in rows]})

    def post(self,request):
        ser=TripSerializer(data=request.data);ser.is_valid(raise_exception=True)
        data=ser.validated_data
        if data['consent_given'] is not True:
            return Response({'error':'explicit_consent_required'},status=400)
        prediction=RoutePrediction.objects.filter(
            pk=data['prediction_id'],request__user=request.user).first()
        if prediction is None:
            return Response({'error':'owned_prediction_required'},status=404)
        ratio=data['distance_m']/prediction.distance_m
        if not .6 <= ratio <= 1.5:
            return Response({'error':'observed_distance_incompatible_with_prediction'},status=400)
        record=ObservedTrip.objects.create(user=request.user,prediction=prediction,
            distance_m=data['distance_m'],observed_fuel_l=data['observed_fuel_l'],
            method=data['method'],notes=data['notes'],consent_given=True)
        return Response({'id':record.pk,'status':'accepted',
          'note':'Full-tank estimates for one short trip can be unreliable; OBD per-trip measurement is preferred.'},
          status=201)


class HoldoutMetricsView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        pairs=list(ObservedTrip.objects.filter(consent_given=True,
          calibration_split='holdout',prediction__isnull=False).values_list(
              'observed_fuel_l','prediction__estimated_l'))
        if len(pairs)<5:
            return Response({'status':'insufficient_holdout_trips','count':len(pairs),
                'minimum':5,'metrics':None})
        return Response({'status':'evaluated','scope':'holdout_only',
            'metrics':fuel_error_metrics(pairs)})
