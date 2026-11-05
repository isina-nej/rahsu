"""Geometric proximity does not imply road-topology confidence."""
import pytest
from domain.route_factors import RoadStep, ObstaclePoint, project_point, match_obstacles

ROUTE = ((51.30, 35.70), (51.31, 35.70))
STEPS = (RoadStep("خیابان آزادی", ROUTE),)

def test_projection_is_metric_and_monotonic():
    d0, pos0, length = project_point((51.302, 35.70), ROUTE)
    d1, pos1, _ = project_point((51.306, 35.70), ROUTE)
    assert d0 < 2 and d1 < 2
    assert 0 < pos0 < pos1 < length

def test_unverified_obstacle_not_applied():
    ob = ObstaclePoint(1, "traffic_signals", 51.305, 35.70)
    matches = match_obstacles(ROUTE, 920, STEPS, [ob])
    assert len(matches) == 1
    assert not matches[0].usable_for_fuel
    assert matches[0].reason == "not_reviewed"

def test_same_nearby_road_without_name_confirmation_is_not_applied():
    ob = ObstaclePoint(2,"stop",51.305,35.70,True,"خیابان دیگر","both","manual")
    assert not match_obstacles(ROUTE, 920, STEPS,[ob])[0].usable_for_fuel

def test_only_explicitly_reviewed_bidirectional_named_road_applied():
    ob = ObstaclePoint(3,"bump",51.305,35.70,True,"خیابان آزادی","both","manual")
    assert match_obstacles(ROUTE, 920, STEPS,[ob])[0].usable_for_fuel
    assert not match_obstacles(ROUTE,920,STEPS,[ObstaclePoint(4,"stop",51.305,35.70,True,"خیابان آزادی","unknown","manual")])[0].usable_for_fuel

def test_distant_mapped_feature_is_excluded():
    ob = ObstaclePoint(5,"hump",51.305,35.701,True,"خیابان آزادی","both","manual")
    assert not match_obstacles(ROUTE,920,STEPS,[ob])
