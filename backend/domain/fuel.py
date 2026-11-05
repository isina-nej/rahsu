"""Pure SI-unit physics fuel estimation, independent of web frameworks.

This is a research estimator, NOT a calibrated engine map or a measured fuel flow.
"""

from dataclasses import dataclass
from math import cos, isfinite, sin
from typing import Sequence

G = 9.80665


@dataclass(frozen=True)
class VehicleParameters:
    mass_kg: float
    cd: float
    frontal_area_m2: float
    rolling_resistance: float
    drivetrain_efficiency: float
    engine_efficiency: float
    idle_lph: float
    reference_urban_l100: float
    rotational_mass_factor: float = 1.06
    air_density_kg_m3: float = 1.225
    gasoline_energy_j_l: float = 32_000_000.0

    def __post_init__(self) -> None:
        positive = (self.mass_kg, self.frontal_area_m2, self.idle_lph,
                    self.reference_urban_l100, self.gasoline_energy_j_l)
        if not all(isfinite(x) and x > 0 for x in positive):
            raise ValueError("Vehicle parameters must be finite and positive")
        if not (0 < self.drivetrain_efficiency <= 1 and 0 < self.engine_efficiency <= 1):
            raise ValueError("Efficiencies must be in (0,1]")
        if self.cd <= 0 or self.rolling_resistance <= 0 or self.rotational_mass_factor < 1:
            raise ValueError("Invalid physical coefficients")


@dataclass(frozen=True)
class MotionSample:
    t_s: float
    s_m: float
    v_mps: float
    a_mps2: float
    grade_rad: float = 0.0


@dataclass(frozen=True)
class FuelEstimate:
    liters: float
    distance_m: float
    duration_s: float
    idle_liters: float
    propulsion_liters: float
    model_version: str
    warnings: tuple[str, ...] = ()


def baseline_liters(distance_m: float, reference_urban_l100: float) -> float:
    if not (isfinite(distance_m) and distance_m >= 0 and isfinite(reference_urban_l100)
            and reference_urban_l100 > 0):
        raise ValueError("Invalid baseline inputs")
    return (distance_m / 1000.0) * reference_urban_l100 / 100.0


def wheel_power_w(sample: MotionSample, params: VehicleParameters, wind_mps: float = 0.0) -> float:
    """Positive power demand at wheels. Wind is longitudinal, + is tailwind."""
    v = sample.v_mps
    if v < 0 or not all(isfinite(x) for x in (v, sample.a_mps2, sample.grade_rad, wind_mps)):
        raise ValueError("Invalid motion sample")
    m = params.mass_kg
    relative_wind = v - wind_mps
    f_aero = 0.5 * params.air_density_kg_m3 * params.cd * params.frontal_area_m2 * relative_wind * abs(relative_wind)
    f_roll = m * G * params.rolling_resistance * cos(sample.grade_rad)
    f_gravity = m * G * sin(sample.grade_rad)
    f_accel = m * params.rotational_mass_factor * sample.a_mps2
    return v * (f_aero + f_roll + f_gravity + f_accel)


def estimate_physics(
    samples: Sequence[MotionSample], params: VehicleParameters, *, wind_mps: float = 0.0,
) -> FuelEstimate:
    """Left-point integration of q_idle + positive tractive power / (efficiencies*LHV).

    Deliberate simplifications: no engine RPM/BSFC, cold-start, regen, braking
    fuel-cut, or time-dependent A/C. Estimate is not guaranteed accurate without
    calibration. A braking episode contributes idle consumption, not negative fuel.
    """
    if len(samples) < 2:
        raise ValueError("At least two motion samples are required")
    idle = traction = 0.0
    for previous, current in zip(samples, samples[1:]):
        dt = current.t_s - previous.t_s
        if dt <= 0 or current.s_m < previous.s_m or current.v_mps < 0:
            raise ValueError("Samples must have strictly increasing time and nondecreasing distance")
        idle += params.idle_lph * dt / 3600.0
        power_w = max(wheel_power_w(previous, params, wind_mps), 0.0)
        traction += power_w * dt / (
            params.drivetrain_efficiency * params.engine_efficiency * params.gasoline_energy_j_l
        )
    return FuelEstimate(
        liters=idle + traction,
        distance_m=samples[-1].s_m - samples[0].s_m,
        duration_s=samples[-1].t_s - samples[0].t_s,
        idle_liters=idle,
        propulsion_liters=traction,
        model_version="physics-prototype-0.1",
        warnings=("uncalibrated_for_pride", "no_measured_traffic", "idealized_engine_and_drive_cycle"),
    )
