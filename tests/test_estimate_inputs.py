import pytest
from rest_framework.test import APIClient

def test_non_finite_measurement_is_rejected():
    response=APIClient().post('/api/v1/estimates/',{
      'origin':{'lat':35.7,'lon':51.3},
      'destination':{'lat':35.7,'lon':51.4},
      'cargo_kg':'NaN'},format='json')
    assert response.status_code==400
