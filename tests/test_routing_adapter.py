import pytest
from domain.fuel import baseline_liters
from apps.routing.osrm import OsrmClient, RoutingError

def test_osrm_route_parse(monkeypatch):
    class Resp:
        def raise_for_status(self): pass
        def json(self):return {'code':'Ok','routes':[{'distance':1000,'duration':90,'geometry':{'coordinates':[[51.3,35.6],[51.4,35.7]]}}]}
    def fake_get(url,params,timeout):
        assert '/route/v1/driving/51.3,35.6;51.4,35.7' in url
        return Resp()
    monkeypatch.setattr('apps.routing.osrm.httpx.get',fake_get)
    found=OsrmClient('http://osrm:5000').candidates((35.6,51.3),(35.7,51.4))
    assert len(found)==1
    assert found[0].distance_m==1000
    assert baseline_liters(1000,9.5)==pytest.approx(.095)

def test_no_route(monkeypatch):
    class Resp:
        def raise_for_status(self):pass
        def json(self):return {'code':'NoRoute'}
    monkeypatch.setattr('apps.routing.osrm.httpx.get',lambda *args,**kwargs:Resp())
    with pytest.raises(RoutingError,match='no_route'):
        OsrmClient('http://osrm').candidates((35.6,51.3),(35.7,51.4))
