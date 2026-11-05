import pytest
from domain.vehicle_specs import research_vehicle

def test_pride_vehicle_assumptions_are_versioned_and_explicitly_uncalibrated():
    pride=research_vehicle('pride-131')
    assert pride.model_status=='uncalibrated_research_hypothesis'
    assert pride.public_assumptions()['curb_mass_kg']==915
    assert pride.public_assumptions()['reference_urban_l100']==9.5

def test_cargo_passengers_and_ac_affect_vehicle_parameters():
    pride=research_vehicle('pride-131')
    base=pride.parameterize(passengers=1,cargo_kg=0,ac_on=False)
    loaded=pride.parameterize(passengers=3,cargo_kg=40,ac_on=True)
    assert loaded.mass_kg>base.mass_kg
    assert loaded.idle_lph>base.idle_lph
    assert base.reference_urban_l100==loaded.reference_urban_l100

def test_invalid_new_vehicle_or_load_is_rejected():
    with pytest.raises(ValueError,match='vehicle_not_supported'):
        research_vehicle('unmeasured-model')
    with pytest.raises(ValueError,match='invalid_vehicle_load'):
        research_vehicle('pride-131').parameterize(passengers=10,cargo_kg=0,ac_on=False)
