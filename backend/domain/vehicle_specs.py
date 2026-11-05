"""Versioned vehicle parameter registry for research estimators.

Coefficients below are engineering starting hypotheses, NOT calibrated or
factory-certified powertrain maps. Future vehicles add specs here without
changing the routing request pipeline.
"""
from dataclasses import dataclass
from math import isfinite

from domain.fuel import VehicleParameters


@dataclass(frozen=True)
class ResearchVehicleSpec:
    slug: str
    name_fa: str
    curb_mass_kg: float
    passenger_mass_kg: float
    urban_reference_l100: float
    cd: float
    frontal_area_m2: float
    rolling_resistance: float
    drivetrain_efficiency: float
    engine_efficiency: float
    idle_lph: float
    ac_extra_idle_lph: float
    model_status: str = "uncalibrated_research_hypothesis"

    def parameterize(self, *, passengers: int, cargo_kg: float,
                     ac_on: bool) -> VehicleParameters:
        if (not isinstance(passengers,int) or not 1<=passengers<=5
                or not isfinite(cargo_kg) or not 0<=cargo_kg<=150):
            raise ValueError('invalid_vehicle_load')
        return VehicleParameters(
            mass_kg=self.curb_mass_kg + passengers*self.passenger_mass_kg + cargo_kg,
            cd=self.cd, frontal_area_m2=self.frontal_area_m2,
            rolling_resistance=self.rolling_resistance,
            drivetrain_efficiency=self.drivetrain_efficiency,
            engine_efficiency=self.engine_efficiency,
            idle_lph=self.idle_lph+(self.ac_extra_idle_lph if ac_on else 0),
            reference_urban_l100=self.urban_reference_l100,
        )

    def public_assumptions(self) -> dict:
        return {
            "coefficient_status":self.model_status,
            "curb_mass_kg":self.curb_mass_kg,
            "assumed_mass_per_person_kg":self.passenger_mass_kg,
            "reference_urban_l100":self.urban_reference_l100,
            "cd_hypothesis":self.cd,
            "frontal_area_m2_hypothesis":self.frontal_area_m2,
            "rolling_resistance_hypothesis":self.rolling_resistance,
            "engine_efficiency_hypothesis":self.engine_efficiency,
            "drivetrain_efficiency_hypothesis":self.drivetrain_efficiency,
            "idle_lph_hypothesis":self.idle_lph,
            "extra_ac_idle_lph_hypothesis":self.ac_extra_idle_lph,
        }


VEHICLE_SPECS = {
    'pride-131':ResearchVehicleSpec(
        slug='pride-131',name_fa='پراید ۱۳۱ دنده‌ای',
        curb_mass_kg=915.0,passenger_mass_kg=75.0,
        urban_reference_l100=9.5,
        cd=.35,frontal_area_m2=1.85,rolling_resistance=.013,
        drivetrain_efficiency=.86,engine_efficiency=.19,
        idle_lph=.75,ac_extra_idle_lph=.20,
    ),
}


def research_vehicle(slug: str) -> ResearchVehicleSpec:
    """A strict preset lookup; missing vehicles are never substituted."""
    try:
        return VEHICLE_SPECS[slug]
    except KeyError as exc:
        raise ValueError('vehicle_not_supported') from exc
