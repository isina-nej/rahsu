import pytest
from apps.calibration.metrics import fuel_error_metrics

def test_metrics_exact():
    m=fuel_error_metrics([(1,1.1),(2,1.8)])
    assert m['n']==2
    assert m['mae_l']==pytest.approx(.15)
    assert m['mape_pct']==pytest.approx(10.)
    assert m['mean_bias_l']==pytest.approx(-.05)

def test_invalid_measurement_rejected():
    with pytest.raises(ValueError):
        fuel_error_metrics([(0.0,1.0)])
