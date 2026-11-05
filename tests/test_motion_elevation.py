from math import isclose
import pytest
from domain.elevation import uniform_positions, terrain_from_elevations, apply_terrain
from domain.motion import simulate_motion, RequiredSlowdown, RequiredStop

def test_uniform_route_positions_respect_endpoints():
    route=((51.3,35.7),(51.302,35.7),(51.31,35.7))
    positions=uniform_positions(route,10)
    assert positions[0]==route[0]
    assert positions[-1][0]==pytest.approx(route[-1][0])
    assert all(a[0]<=b[0] for a,b in zip(positions,positions[1:]))

def test_uphill_and_downhill_grade_sign():
    t=terrain_from_elevations([100.,105.,110.,100.,90.],400.)
    assert t.ascent_m>0 and t.descent_m>0
    assert any(x>0 for x in t.grades_rad)
    assert any(x<0 for x in t.grades_rad)
    motion=simulate_motion(400.,60.)
    updated=apply_terrain(motion,t,400.)
    assert any(x.grade_rad>0 for x in updated)
    assert any(x.grade_rad<0 for x in updated)

def test_speed_bump_slows_not_full_stops():
    normal=simulate_motion(1000,100)
    bump=simulate_motion(1000,100,slowdowns=(RequiredSlowdown(500,3.0),))
    at=[p for p in bump if abs(p.s_m-500)<1e-3]
    assert len(at)==1 and at[0].v_mps==pytest.approx(3.)
    assert bump[-1].s_m==pytest.approx(1000.)
    assert bump[-1].t_s>normal[-1].t_s

def test_invalid_grade_rejected():
    with pytest.raises(ValueError):terrain_from_elevations([100,float('nan'),90],300)

def test_zero_duration_stop_remains_valid():
    samples=simulate_motion(600,90,(RequiredStop(250,0),))
    assert samples[-1].s_m==pytest.approx(600)
