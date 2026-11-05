from math import isclose

import pytest

from domain.fuel import MotionSample, VehicleParameters, baseline_liters, estimate_physics, wheel_power_w
from domain.motion import RequiredStop, simulate_motion


@pytest.fixture
def pride():
    # Engineering hypotheses, NOT factory-verified or calibrated coefficients.
    return VehicleParameters(
        mass_kg=1060, cd=0.35, frontal_area_m2=1.85,
        rolling_resistance=0.013, drivetrain_efficiency=0.86,
        engine_efficiency=0.19, idle_lph=0.75, reference_urban_l100=9.5,
    )


def test_baseline():
    assert baseline_liters(10000, 9.5) == pytest.approx(0.95)


def test_baseline_bad_inputs():
    with pytest.raises(ValueError):
        baseline_liters(-1, 9.5)


def test_traction_positive_for_moving_vehicle(pride):
    sample = MotionSample(t_s=0, s_m=0, v_mps=10, a_mps2=0)
    assert wheel_power_w(sample, pride) > 0


def test_grade_increases_required_power(pride):
    flat = wheel_power_w(MotionSample(0, 0, 10, 0, 0), pride)
    up = wheel_power_w(MotionSample(0, 0, 10, 0, 0.05), pride)
    assert up > flat


def test_stops_add_idling_and_motion_samples(pride):
    nonstop = simulate_motion(1000, 100)
    stop = simulate_motion(1000, 100, (RequiredStop(500, 25),))
    assert stop[-1].s_m == pytest.approx(1000)
    assert stop[-1].t_s > nonstop[-1].t_s
    total = estimate_physics(stop, pride)
    assert total.liters > 0
    assert total.idle_liters > 0
    assert isclose(total.idle_liters + total.propulsion_liters, total.liters)


def test_invalid_sample_sequence(pride):
    with pytest.raises(ValueError):
        estimate_physics([MotionSample(0, 0, 0, 0), MotionSample(0, 5, 5, 1)], pride)
