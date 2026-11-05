"""On-demand Tehran geocoding via a self-hosted Nominatim-compatible API.

No autocomplete or unbounded public Nominatim usage; remote provider must be
explicitly configured by the operator.
"""
import httpx
from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class GeocodeQuery(serializers.Serializer):
    q=serializers.CharField(min_length=2,max_length=120,trim_whitespace=True)


class GeocodeView(APIView):
    permission_classes=[AllowAny]

    def get(self,request):
        ser=GeocodeQuery(data=request.query_params);ser.is_valid(raise_exception=True)
        base=getattr(settings,'GEOCODER_BASE_URL','').rstrip('/')
        if not base:
            return Response({'error':'geocoder_not_configured'},status=503)
        q=ser.validated_data['q']
        cached=cache.get('geocode:'+q.lower())
        if cached is not None:
            return Response(cached)
        # At most one uncached external request/s per shared cache.
        if not cache.add('geocoder_rate_lock',True,timeout=2):
            return Response({'error':'geocoder_rate_limited'},status=429)
        try:
            response=httpx.get(base+'/search',params={
                'q':q,'format':'jsonv2','limit':6,'addressdetails':1,'accept-language':'fa',
                'viewbox':'51.05,35.95,51.75,35.45','bounded':1,
            },headers={'User-Agent':'RahsuUniversityResearch/0.2 (operator configured provider)'},
            timeout=6.0)
            response.raise_for_status()
            data=response.json()
            if not isinstance(data,list):
                raise ValueError('Invalid provider payload')
        except (httpx.HTTPError,ValueError):
            return Response({'error':'geocoder_unavailable'},status=503)
        results=[]
        for entry in data:
            try:
                lat,lon=float(entry['lat']),float(entry['lon'])
                if 35.45<=lat<=35.95 and 51.05<=lon<=51.75:
                    results.append({'label':str(entry.get('display_name',''))[:240],
                        'lat':lat,'lon':lon})
            except (KeyError,ValueError,TypeError):
                continue
        output={'results':results,'provider':'configured_nominatim','scope':'tehran'}
        cache.set('geocode:'+q.lower(),output,timeout=86_400)
        return Response(output)
