import pytest
from domain.osm_geojson import parse_obstacle_geojson

def test_osmium_point_provenance_and_tehran_bounds():
    data={'type':'FeatureCollection','features':[
      {'type':'Feature','properties':{'@id':'node/41','highway':'traffic_signals'},
         'geometry':{'type':'Point','coordinates':[51.35,35.72]}},
      {'type':'Feature','properties':{'@id':'way/99','traffic_calming':'hump'},
         'geometry':{'type':'Point','coordinates':[51.35,35.72]}},
      {'type':'Feature','properties':{'@id':'node/50','traffic_calming':'bump'},
         'geometry':{'type':'Point','coordinates':[60,30]}},
    ]}
    found=parse_obstacle_geojson(data)
    assert len(found)==1 and found[0].osm_id==41

def test_bad_geojson_rejected():
    with pytest.raises(ValueError):
        parse_obstacle_geojson({'type':'Point','coordinates':[51.3,35.7]})
