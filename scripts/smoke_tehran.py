#!/usr/bin/env python3
"""Live end-to-end Tehran Pride smoke check. Never fabricate provider responses.

Run against an operator-owned local/staging Rahsu API after loading actual
Tehran OSRM graph and PostGIS obstacles.
"""
import argparse
import json
import sys
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


FIXED_TEST_ROUTE = {
    'origin': {'lat':35.6892,'lon':51.3890},
    'destination':{'lat':35.7000,'lon':51.4100},
    'passengers':1,'cargo_kg':0,'ac_on':False,
}


def request_json(base: str, path: str, payload: dict | None = None) -> dict:
    headers={'Accept':'application/json'}
    if payload is None:
        req=Request(base+path,headers=headers)
    else:
        headers['Content-Type']='application/json'
        req=Request(base+path,data=json.dumps(payload).encode('utf-8'),
                    headers=headers,method='POST')
    with urlopen(req, timeout=20) as res:
        if res.status!=200:
            raise RuntimeError(f'Unexpected HTTP {res.status} for {path}')
        return json.load(res)


def validate_estimate(obj: dict) -> dict:
    """Raise when the output is absent, invalid, mocked, or not Tehran Pride."""
    if not isinstance(obj,dict) or obj.get('scope')!='tehran' or obj.get('vehicle')!='pride-131':
        raise ValueError('Wrong research scope or missing response')
    if obj.get('research_only') is not True:
        raise ValueError('Unverified prediction must retain research-only flag')
    routes=obj.get('routes')
    if not isinstance(routes,list) or not routes:
        raise ValueError('No live routing results')
    for route in routes:
        geometry=route.get('geometry',{})
        if geometry.get('type')!='LineString' or len(geometry.get('coordinates',[]))<2:
            raise ValueError('Missing OSRM LineString geometry')
        if (route.get('distance_m',0)<=100 or route.get('osrm_duration_s',0)<=0
            or route.get('baseline_l',0)<=0 or route.get('estimated_l',0)<=0):
            raise ValueError('Non-positive or incomplete route estimate')
        if not isinstance(route.get('warnings'),list):
            raise ValueError('Prediction uncertainty metadata missing')
        if 'topology_matched_osm_calming' not in route.get('obstacle_summary',{}):
            raise ValueError('Topology match evidence is missing')
    return {'routes':len(routes),
            'first_distance_m':routes[0]['distance_m'],
            'first_estimated_l':routes[0]['estimated_l'],
            'first_map_version':routes[0].get('map_data_version'),
            'research_only':True}


def main() -> int:
    parser=argparse.ArgumentParser(description='Rahsu live Tehran routing smoke test')
    parser.add_argument('--api',default='http://127.0.0.1:8000',
                        help='Operator-controlled Rahsu API base URL')
    args=parser.parse_args()
    base=args.api.rstrip('/')
    try:
        if request_json(base,'/api/v1/health/live').get('status')!='live':
            raise ValueError('Liveness failed')
        if request_json(base,'/api/v1/health/ready').get('status')!='ready':
            raise ValueError('Readiness failed')
        result=validate_estimate(
            request_json(base,'/api/v1/estimates/',FIXED_TEST_ROUTE))
    except (URLError,HTTPError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print(f'RAHSU SMOKE FAILED: {exc.__class__.__name__}: {exc}',file=sys.stderr)
        return 1
    print('RAHSU TEHRAN SMOKE PASSED '+json.dumps(result,ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
