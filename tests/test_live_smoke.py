"""Verify the deployment smoke validator without a network or fake production graph."""
import pytest
from scripts.smoke_tehran import validate_estimate

GOOD={
 'scope':'tehran','vehicle':'pride-131','research_only':True,
 'routes':[{
   'geometry':{'type':'LineString','coordinates':[[51.39,35.69],[51.41,35.7]]},
   'distance_m':2300,'osrm_duration_s':240,'baseline_l':.22,
   'estimated_l':.2,'map_data_version':'2026-10-01T00:00:00Z',
   'warnings':['uncalibrated_for_pride'],
   'obstacle_summary':{'topology_matched_osm_calming':2}
 }]
}

def test_smoke_accepts_structurally_valid_research_result():
    assert validate_estimate(GOOD)['routes']==1

@pytest.mark.parametrize('field,value',[
    ('routes',[]),
    ('research_only',False),
    ('vehicle','some-other-car'),
])
def test_smoke_rejects_incomplete_or_false_claims(field,value):
    with pytest.raises(ValueError):
        validate_estimate({**GOOD,field:value})

def test_smoke_fails_without_topology_evidence():
    bad={**GOOD,'routes':[{**GOOD['routes'][0],'obstacle_summary':{}}]}
    with pytest.raises(ValueError):
        validate_estimate(bad)
