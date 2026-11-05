"""Exact node traversal is stronger than proximity for physical calming."""
from domain.route_factors import match_obstacles,ObstaclePoint,RoadStep

LINE=((51.3,35.7),(51.31,35.7))
STEPS=(RoadStep('آزادی',LINE),)

def test_auto_calming_requires_exact_traversed_osm_node():
    bump=ObstaclePoint(1,'bump',51.305,35.7,source='osm',osm_type='node',osm_id=777)
    on=match_obstacles(LINE,900,STEPS,[bump],route_osm_nodes=(777,))
    off=match_obstacles(LINE,900,STEPS,[bump],route_osm_nodes=(888,))
    assert on[0].usable_for_fuel and on[0].reason=='osm_node_on_traversed_route'
    assert not off[0].usable_for_fuel

def test_crossing_traffic_light_and_stop_are_not_automatically_assumed():
    items=[ObstaclePoint(i,k,51.305,35.7,source='osm',osm_type='node',osm_id=700+i)
           for i,k in enumerate(['crossing','traffic_signals','stop'],1)]
    selected=match_obstacles(LINE,900,STEPS,items,route_osm_nodes=(701,702,703))
    assert len(selected)==3 and not any(x.usable_for_fuel for x in selected)

def test_geographically_distant_osm_node_cannot_affect_fuel():
    bump=ObstaclePoint(1,'hump',51.305,35.702,source='osm',osm_type='node',osm_id=777)
    assert match_obstacles(LINE,900,STEPS,[bump],route_osm_nodes=(777,))==[]

def test_manual_review_is_still_supported_without_osrm_annotations():
    manual=ObstaclePoint(2,'bump',51.305,35.7,True,'آزادی','both','manual')
    assert match_obstacles(LINE,900,STEPS,[manual])[0].usable_for_fuel
