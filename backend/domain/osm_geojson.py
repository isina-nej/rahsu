"""Ingest GeoJSON exported by osmium from a real licensed OSM extract."""
from domain.osm import BOUNDING_BOX, HIGHWAY, TRAFFIC_CALMING, OSMObstacle

def parse_obstacle_geojson(document: dict) -> list[OSMObstacle]:
    if not isinstance(document,dict) or document.get('type')!='FeatureCollection':
        raise ValueError('GeoJSON FeatureCollection required')
    features=document.get('features')
    if not isinstance(features,list):
        raise ValueError('Invalid GeoJSON features')
    by_id={}
    for feature in features:
        if not isinstance(feature,dict):
            continue
        geom=feature.get('geometry')
        props=feature.get('properties')
        if not isinstance(geom,dict) or geom.get('type')!='Point' or not isinstance(props,dict):
            continue
        kind=TRAFFIC_CALMING.get(props.get('traffic_calming')) or HIGHWAY.get(props.get('highway'))
        if not kind:continue
        osm_ref=props.get('@id',feature.get('id',''))
        if not isinstance(osm_ref,str) or not osm_ref.startswith('node/'):
            continue
        try:
            osm_id=int(osm_ref[5:])
            lon,lat=map(float,geom['coordinates'][:2])
        except (ValueError,TypeError,KeyError,IndexError):
            continue
        if osm_id<=0 or not (BOUNDING_BOX[0]<=lon<=BOUNDING_BOX[2] and BOUNDING_BOX[1]<=lat<=BOUNDING_BOX[3]):
            continue
        by_id[osm_id]=OSMObstacle(osm_id,kind,lat,lon)
    return list(by_id.values())
