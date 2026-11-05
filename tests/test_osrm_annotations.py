"""OSRM node-annotation contract: a real route may expose traversed OSM nodes."""
from apps.routing.osrm import OsrmClient

def test_route_osm_node_annotations_are_parsed_without_float_conversion(monkeypatch):
    big_id=9876543210987654
    class Resp:
        def raise_for_status(self): pass
        def json(self):
            return {'code':'Ok','routes':[{
                'distance':950,'duration':115,
                'geometry':{'coordinates':[[51.3,35.7],[51.305,35.7],[51.31,35.7]]},
                'legs':[{'annotation':{'nodes':[123,big_id,123,0,None,True]},
                         'steps':[{'name':'خیابان آزادی',
                                   'geometry':{'coordinates':[[51.3,35.7],[51.31,35.7]]}}]}]
            }]}
    def fake_get(url,params,timeout):
        assert params['annotations']=='nodes'
        assert params['geometries']=='geojson'
        assert params['overview']=='full'
        return Resp()
    monkeypatch.setattr('apps.routing.osrm.httpx.get',fake_get)
    route=OsrmClient('http://osrm:5000').candidates((35.7,51.3),(35.7,51.31))[0]
    assert route.osm_node_ids==(123,big_id)
    assert route.road_steps[0].name=='خیابان آزادی'
