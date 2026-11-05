"""Tehran route estimation: actual OSRM geometry, conservative obstacle evidence,
optional DEM and two fuel scenarios. No fabricated real-time traffic.
"""
import logging
from django.conf import settings
from django.contrib.gis.geos import Point, LineString
from apps.routing.models import RouteRequest, RoutePrediction
from django.contrib.gis.geos import Polygon
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.geo.models import Obstacle
from domain.elevation import ElevationClient, ElevationError, uniform_positions, terrain_from_elevations, apply_terrain
from domain.fuel import VehicleParameters, baseline_liters, estimate_physics
from domain.motion import RequiredSlowdown, RequiredStop, simulate_motion
from domain.route_factors import ObstaclePoint, match_obstacles
from .osrm import OsrmClient, RoutingError

log = logging.getLogger(__name__)


class CoordinatesSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=35.45,max_value=35.95)
    lon = serializers.FloatField(min_value=51.05,max_value=51.75)


class EstimateSerializer(serializers.Serializer):
    origin = CoordinatesSerializer()
    destination = CoordinatesSerializer()
    passengers = serializers.IntegerField(default=1,min_value=1,max_value=5)
    cargo_kg = serializers.FloatField(default=0,min_value=0,max_value=150)
    ac_on = serializers.BooleanField(default=False)
    signal_red_probability = serializers.FloatField(default=0.5,min_value=0,max_value=1)
    save_history = serializers.BooleanField(default=False)


def _nearby_obstacles(route) -> list[ObstaclePoint]:
    """PostGIS index bbox prefilter; conservative exact match happens in domain."""
    lons=[x[0] for x in route.coordinates];lats=[x[1] for x in route.coordinates]
    if len(lons)<2:return []
    bounds=(min(lons)-0.0003,min(lats)-0.0003,max(lons)+0.0003,max(lats)+0.0003)
    box=Polygon.from_bbox(bounds)
    rows=Obstacle.objects.filter(location__bboverlaps=box).exclude(source='removed').order_by('id')[:8000]
    return [ObstaclePoint(x.pk,x.kind,x.location.x,x.location.y,
            x.verified,x.road_name,x.direction,x.source) for x in rows]


def _terrain(route):
    """Optional elevation; unknown is explicitly reported rather than silently flat."""
    base=getattr(settings,"ELEVATION_BASE_URL","")
    if not base:
        return None,["grade_not_measured"]
    try:
        count=min(70,max(5,int(route.distance_m/250)+1))
        positions=uniform_positions(route.coordinates,count)
        heights=ElevationClient(base).elevations(positions)
        return terrain_from_elevations(heights,route.distance_m),["dem_resolution_limited"]
    except (ElevationError,ValueError) as exc:
        log.warning("elevation.unavailable code=%s",type(exc).__name__)
        return None,["grade_provider_unavailable"]


def _simulate(route,params,stops,slowdowns,terrain):
    samples=simulate_motion(route.distance_m,route.duration_s,stops,
                slowdowns=slowdowns,dt_s=2.0)
    if terrain is not None:
        samples=apply_terrain(samples,terrain,route.distance_m)
    return estimate_physics(samples,params)


class EstimateView(APIView):
    permission_classes=[AllowAny]

    def post(self,request):
        ser=EstimateSerializer(data=request.data);ser.is_valid(raise_exception=True)
        data=ser.validated_data
        start=(data['origin']['lat'],data['origin']['lon'])
        end=(data['destination']['lat'],data['destination']['lon'])
        if start==end:
            return Response({'error':'origin_equals_destination'},status=400)
        if data['save_history'] and not request.user.is_authenticated:
            return Response({'error':'authentication_required_for_history'},status=401)
        try:
            routes=OsrmClient(settings.OSRM_BASE_URL).candidates(start,end)
        except RoutingError as exc:
            log.warning('routing.error code=%s',str(exc))
            return Response({'error':str(exc)},status=503 if str(exc)=='routing_provider_unavailable' else 422)
        if not routes:return Response({'error':'no_route'},status=422)
        # Engineering hypotheses; these are NOT laboratory-calibrated Pride engine coefficients.
        params=VehicleParameters(mass_kg=915+75*data['passengers']+data['cargo_kg'],
            cd=0.35,frontal_area_m2=1.85,rolling_resistance=.013,
            drivetrain_efficiency=.86,engine_efficiency=.19,
            idle_lph=.75+(.20 if data['ac_on'] else 0),reference_urban_l100=9.5)
        history=None
        if data['save_history']:
            # Explicit opt-in: anonymous coordinates are never stored.
            history=RouteRequest.objects.create(user=request.user,
                origin=Point(start[1],start[0],srid=4326),
                destination=Point(end[1],end[0],srid=4326),
                scenario={'passengers':data['passengers'],'cargo_kg':data['cargo_kg'],
                          'ac_on':data['ac_on'],
                          'signal_red_probability':data['signal_red_probability']})
        response=[]
        for i,route in enumerate(routes[:3]):
            if not 0<route.distance_m<=100_000 or route.duration_s>36_000:continue
            projected=match_obstacles(route.coordinates,route.distance_m,route.road_steps,
                                      _nearby_obstacles(route))
            applied=[x for x in projected if x.usable_for_fuel and 2<x.at_m<route.distance_m-2]
            hard_stops=tuple(RequiredStop(x.at_m,2.0) for x in applied if x.kind=='stop')
            red_signals=tuple(RequiredStop(x.at_m,20.0) for x in applied if x.kind=='traffic_signals')
            slows=tuple(RequiredSlowdown(x.at_m,3.0 if x.kind in ('bump','hump') else 4.5)
                for x in applied if x.kind in ('bump','hump','crossing'))
            terrain, terrain_warnings=_terrain(route)
            try:
                green=_simulate(route,params,hard_stops,slows,terrain)
                red=_simulate(route,params,hard_stops+red_signals,slows,terrain) if red_signals else green
            except (RuntimeError,ValueError) as exc:
                log.warning('motion.unavailable code=%s',type(exc).__name__)
                continue
            prob=data['signal_red_probability']
            liters=green.liters*(1-prob)+red.liters*prob
            idle_l=green.idle_liters*(1-prob)+red.idle_liters*prob
            traction_l=green.propulsion_liters*(1-prob)+red.propulsion_liters*prob
            warnings=[*green.warnings,*terrain_warnings,'traffic_not_live',
                      'unreviewed_osm_not_applied','manual_obstacle_matching_is_conservative']
            if red_signals:
                warnings.append('signal_red_probability_is_assumed')
            else:
                warnings.append('signal_phase_unknown_or_no_reviewed_signals')
            prediction_id=None
            if history is not None:
                stored=RoutePrediction.objects.create(request=history,
                    geometry=LineString(*route.coordinates,srid=4326),
                    distance_m=route.distance_m,duration_s=route.duration_s,
                    baseline_l=baseline_liters(route.distance_m,9.5),
                    estimated_l=liters,idle_l=idle_l,propulsion_l=traction_l,
                    model_version=green.model_version,warnings=warnings,
                    assumptions={'physics_uncalibrated':True,
                        'terrain_available':terrain is not None,
                        'applied_obstacles':len(applied),
                        'signal_red_probability':prob})
                prediction_id=stored.pk
            response.append({
                'prediction_id':prediction_id,
                'index':i,'distance_m':route.distance_m,'osrm_duration_s':route.duration_s,
                'modeled_duration_s':round(green.duration_s*(1-prob)+red.duration_s*prob,2),
                'geometry':{'type':'LineString','coordinates':route.coordinates},
                'baseline_l':round(baseline_liters(route.distance_m,9.5),4),
                'estimated_l':round(liters,4),'estimated_range_l':[round(min(green.liters,red.liters),4),
                                                                  round(max(green.liters,red.liters),4)],
                'idle_l':round(idle_l,4),'propulsion_l':round(traction_l,4),
                'obstacle_summary':{'nearby':len(projected),'reviewed_applied':len(applied),
                  'signals_scenario':len(red_signals),'stops':len(hard_stops),
                  'slowdowns':len(slows)},
                'obstacles':[{'id':x.id,'kind':x.kind,'at_m':round(x.at_m,1),
                              'offset_m':x.offset_m,'applied':x.usable_for_fuel,
                              'reason':x.reason} for x in projected[:120]],
                'terrain':{'ascent_m':round(terrain.ascent_m,1),
                           'descent_m':round(terrain.descent_m,1)} if terrain else None,
                'warnings':list(dict.fromkeys(warnings)),
                'model_version':green.model_version})
        return Response({'vehicle':'pride-131','scope':'tehran','routes':response,
            'research_only':True,'data_quality':'partially_observed',
            'note':'Fuel values are uncalibrated research estimates, not measured consumption.'})
