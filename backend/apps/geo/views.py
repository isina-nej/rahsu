from django.contrib.gis.geos import Point
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from .models import Obstacle, ObstacleReport
from .review import decide_report

class ObstacleListView(APIView):
    permission_classes=[AllowAny]

    def get(self, request):
        from django.contrib.gis.geos import Polygon
        from django.contrib.gis.measure import D
        from math import isfinite
        try:
            if 'bbox' in request.query_params:
                bbox=list(map(float,request.query_params['bbox'].split(',')))
                if len(bbox)!=4 or any(not isfinite(x) for x in bbox):
                    raise ValueError
                minlon,minlat,maxlon,maxlat=bbox
                if not(51.05<=minlon<maxlon<=51.75 and
                       35.45<=minlat<maxlat<=35.95 and
                       (maxlon-minlon)*(maxlat-minlat)<=0.18):
                    raise ValueError
                polygon=Polygon.from_bbox(tuple(bbox))
                qs=Obstacle.objects.exclude(source='removed').filter(location__bboverlaps=polygon)
            else:
                lat=float(request.query_params['lat'])
                lon=float(request.query_params['lon'])
                radius=float(request.query_params.get('radius_m','500'))
                if not (all(isfinite(x) for x in (lat,lon,radius))
                       and 35.45<=lat<=35.95 and 51.05<=lon<=51.75):
                    raise ValueError
                radius=min(max(radius,100),3000)
                qs=Obstacle.objects.exclude(source='removed').filter(
                    location__distance_lte=(Point(lon,lat,srid=4326),D(m=radius)))
        except (KeyError,ValueError,TypeError):
            return Response({'error':'provide_valid_tehran_bounds'},status=400)
        rows=list(qs.order_by('id')[:1001])
        return Response({'results':[{'id':x.pk,'kind':x.kind,
            'lon':x.location.x,'lat':x.location.y,'source':x.source,
            'verified':x.verified,'road_name':x.road_name}
            for x in rows[:1000]],'truncated':len(rows)>1000})

class ReportSerializer(serializers.Serializer):
    action=serializers.ChoiceField(choices=['add','correct','remove'])
    kind=serializers.ChoiceField(choices=['traffic_signals','bump','hump','stop','crossing','other'])
    lat=serializers.FloatField(min_value=35.45,max_value=35.95)
    lon=serializers.FloatField(min_value=51.05,max_value=51.75)
    note=serializers.CharField(required=False,max_length=1000,allow_blank=True)
    road_name=serializers.CharField(required=False,max_length=180,allow_blank=True,default='')
    direction=serializers.ChoiceField(required=False,choices=['unknown','both','forward','reverse'],default='unknown')
    obstacle_id=serializers.IntegerField(required=False,min_value=1)

class ObstacleReportView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=ReportSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        data=serializer.validated_data
        if data['action'] in ('remove','correct') and not data.get('obstacle_id'):
            return Response({'error':'obstacle_id_required'},status=400)
        obstacle=Obstacle.objects.filter(pk=data['obstacle_id']).first() if data.get('obstacle_id') else None
        if data['action'] in ('remove','correct') and obstacle is None:
            return Response({'error':'obstacle_not_found'},status=404)
        obj=ObstacleReport.objects.create(submitted_by=request.user,obstacle=obstacle,action=data['action'],kind=data['kind'],location=Point(data['lon'],data['lat'],srid=4326),note=data.get('note',''),road_name=data.get('road_name',''),direction=data.get('direction','unknown'))
        return Response({'id':obj.pk,'status':'pending'},status=201)

class ModerateReportsView(APIView):
    permission_classes=[IsAdminUser]

    def get(self,request):
        status_value=request.query_params.get('status','pending')
        if status_value not in ('pending','approved','rejected'):
            return Response({'error':'invalid_status'},status=400)
        rows=ObstacleReport.objects.filter(status=status_value).order_by('-created_at')[:100]
        return Response({'results':[{'id':x.pk,'action':x.action,'kind':x.kind,
          'road_name':x.road_name,'direction':x.direction,'obstacle_id':x.obstacle_id,
          'lat':x.location.y,'lon':x.location.x,'note':x.note,
          'status':x.status} for x in rows]})

    def patch(self,request):
        try:
            report_id=int(request.data.get('id'))
        except (ValueError,TypeError):
            return Response({'error':'invalid_id'},status=400)
        verdict=request.data.get('decision')
        if verdict not in ('approve','reject'):
            return Response({'error':'invalid_decision'},status=400)
        try:
            report=decide_report(report_id,request.user,verdict=='approve')
        except ObstacleReport.DoesNotExist:
            return Response({'error':'report_not_found'},status=404)
        except ValueError as exc:
            return Response({'error':str(exc)},status=409)
        return Response({'id':report.pk,'status':report.status,'obstacle_id':report.obstacle_id})
