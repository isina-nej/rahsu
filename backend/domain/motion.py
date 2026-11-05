"""Deterministic approximate driving profile with controlled stops.

A placeholder for a road-class/grade-aware speed-profile engine. No fabricated
live traffic or actual traffic light cycles are assumed.
"""

from dataclasses import dataclass
from math import isfinite, sqrt

from domain.fuel import MotionSample


@dataclass(frozen=True)
class RequiredStop:
    at_m: float
    duration_s: float

@dataclass(frozen=True)
class RequiredSlowdown:
    at_m: float
    speed_mps: float


def simulate_motion(
    distance_m: float, nominal_duration_s: float, stops: tuple[RequiredStop, ...] = (), *,
    dt_s: float = 1.0, max_accel_mps2: float = 1.25, max_brake_mps2: float = 2.0,
    slowdowns: tuple[RequiredSlowdown, ...] = (),
) -> list[MotionSample]:
    if not (isfinite(distance_m) and 0 < distance_m <= 500_000 and isfinite(nominal_duration_s)
            and nominal_duration_s > 0 and 0 < dt_s <= 2):
        raise ValueError("Invalid route or timestep")
    if max_accel_mps2 <= 0 or max_brake_mps2 <= 0:
        raise ValueError("Invalid acceleration bounds")
    events: dict[float, tuple[float, float]] = {}
    for stop in stops:
        if not (isfinite(stop.at_m) and 0 < stop.at_m < distance_m
                and isfinite(stop.duration_s) and stop.duration_s >= 0):
            raise ValueError("Invalid stop")
        speed, duration = events.get(stop.at_m, (0.0, 0.0))
        events[stop.at_m] = (0.0, duration + stop.duration_s)
    for slow in slowdowns:
        if not (isfinite(slow.at_m) and 0 < slow.at_m < distance_m
                and isfinite(slow.speed_mps) and 0 < slow.speed_mps <= 22):
            raise ValueError("Invalid slowdown")
        if slow.at_m in events:
            speed, duration = events[slow.at_m]
            events[slow.at_m] = (min(speed, slow.speed_mps), duration)
        else:
            events[slow.at_m] = (slow.speed_mps, 0.0)
    ordered = [(at, speed, duration) for at, (speed, duration) in sorted(events.items())]
    target_v = min(22.0, max(2.0, distance_m / nominal_duration_s))
    points = [MotionSample(t_s=0.0, s_m=0.0, v_mps=0.0, a_mps2=0.0)]
    s = t = v = 0.0
    index = 0
    hold = 0.0
    max_steps = int((distance_m / 2.0 + sum(x[2] for x in ordered) + 3600) / dt_s) + 1000
    for _ in range(max_steps):
        if s >= distance_m - 1e-6:
            break
        if hold > 0:
            new_v = 0.0
            hold = max(0.0, hold - dt_s)
        else:
            next_event = ordered[index] if index < len(ordered) else None
            remaining = max(0.0, next_event[0] - s) if next_event else None
            safe_v = sqrt(next_event[1] ** 2 + 2 * max_brake_mps2 * remaining) if remaining is not None else target_v
            wanted = min(target_v, safe_v)
            new_v = min(wanted, v + max_accel_mps2 * dt_s) if wanted >= v else max(wanted, v - max_brake_mps2 * dt_s)
        s_next = s + (v + new_v) * dt_s / 2.0
        if index < len(ordered) and s_next >= ordered[index][0] - 1e-6:
            s_next = ordered[index][0]
            new_v = ordered[index][1]
            hold = ordered[index][2]
            index += 1
        if s_next >= distance_m:
            s_next = distance_m
            new_v = 0.0
        t += dt_s
        a = (new_v - v) / dt_s
        s, v = s_next, new_v
        points.append(MotionSample(t_s=t, s_m=s, v_mps=v, a_mps2=a))
    else:
        raise RuntimeError("Driving profile did not converge")
    if s < distance_m - 1e-6:
        raise RuntimeError("Driving profile stopped early")
    return points
