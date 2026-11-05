import pytest
from domain.osm import parse_osm_obstacles

def test_only_valid_tehran_nodes_and_known_tags():
    data={'elements':[
      {'type':'node','id':11,'lat':35.7,'lon':51.4,'tags':{'highway':'traffic_signals'}},
      {'type':'node','id':12,'lat':35.7,'lon':51.4,'tags':{'traffic_calming':'bump'}},
      {'type':'node','id':13,'lat':36.5,'lon':51.4,'tags':{'traffic_calming':'hump'}},
      {'type':'node','id':14,'lat':35.7,'lon':51.4,'tags':{'shop':'bakery'}},
      {'type':'way','id':15,'lat':35.7,'lon':51.4,'tags':{'highway':'stop'}},
    ]}
    result=parse_osm_obstacles(data)
    assert [(x.osm_id,x.kind) for x in result]==[(11,'traffic_signals'),(12,'bump')]

def test_malformed_payload_rejected():
    with pytest.raises(ValueError):parse_osm_obstacles({'elements':'oops'})

def test_duplicate_id_is_deduplicated():
    item={'type':'node','id':1,'lat':35.7,'lon':51.4,'tags':{'highway':'stop'}}
    assert len(parse_osm_obstacles({'elements':[item,item]}))==1
