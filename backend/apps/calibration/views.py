"""Consent-based trip records and independent holdout metrics."""
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F
from .models import ObservedTrip
from apps.routing.models import RoutePrediction
from .metrics import fuel_error_metrics, paired_model_comparison


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
        # Evaluate only consented, held-out observations. Repeated submissions
        # of the same prediction are not independent test examples.
        rows=ObservedTrip.objects.filter(
            consent_given=True,calibration_split='holdout',
            prediction__isnull=False,
        ).order_by('prediction_id','created_at','pk').values_list(
            'prediction_id','observed_fuel_l','distance_m',
            'prediction__distance_m','prediction__baseline_l',
            'prediction__estimated_l')
        paired=[]
        seen=set()
        duplicate=distance_mismatch=invalid=0
        for prediction_id,observed,actual_m,planned_m,base,physics in rows:
            if prediction_id in seen:
                duplicate+=1
                continue
            seen.add(prediction_id)
            if not planned_m or not .9<=actual_m/planned_m<=1.1:
                distance_mismatch+=1
                continue
            if any(x is None or x<=0 for x in (observed,base,physics)):
                invalid+=1
                continue
            paired.append((observed,base,physics))
        selection={
            'selected':len(paired),'distinct_predictions':len(seen),
            'excluded_duplicate_predictions':duplicate,
            'excluded_distance_mismatch':distance_mismatch,
            'excluded_invalid':invalid,
        }
        if len(paired)<5:
            return Response({'status':'insufficient_holdout_trips',
                'count':len(paired),'minimum':5,'metrics':None,
                'comparison':None,'selection':selection})
        comparison=paired_model_comparison(paired)
        return Response({
            'status':'evaluated','scope':'holdout_only',
            'metrics':comparison['physics'],  # Existing API field.
            'comparison':comparison,'selection':selection,
            'scientifically_validated':False,
            'warning':'Exploratory holdout; driver independence and measured fuel quality still require verification.',
        })
