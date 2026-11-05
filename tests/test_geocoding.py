from unittest.mock import patch
import pytest
from rest_framework.test import APIClient

def test_geocoder_disabled_is_explicit(settings):
    settings.GEOCODER_BASE_URL=''
    response=APIClient().get('/api/v1/geocode/',{'q':'میدان آزادی'})
    assert response.status_code==503
    assert response.json()['error']=='geocoder_not_configured'

def test_geocoder_bounded_and_sanitized(settings):
    settings.GEOCODER_BASE_URL='http://nominatim:8080'
    class Resp:
        def raise_for_status(self):pass
        def json(self):
            return [{'display_name':'میدان آزادی','lat':'35.7','lon':'51.32'},
                    {'display_name':'outside','lat':'34','lon':'55'}]
    with patch('apps.routing.geocoding.cache') as cache,patch('apps.routing.geocoding.httpx.get',return_value=Resp()) as get:
        cache.get.return_value=None
        cache.add.return_value=True
        response=APIClient().get('/api/v1/geocode/',{'q':'میدان آزادی'})
    assert response.status_code==200
    assert len(response.json()['results'])==1
    assert get.call_args.kwargs['params']['bounded']==1

def test_geocoder_rejects_empty_input(settings):
    settings.GEOCODER_BASE_URL='http://nominatim:8080'
    assert APIClient().get('/api/v1/geocode/',{'q':'a'}).status_code==400
