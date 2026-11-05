import math
import pytest
from domain.vt_micro import VTMicroModel,TrainingRow,features,train,validate

def test_feature_matrix_and_flow_are_finite():
    assert len(features(10.0,0.8))==16
    model=VTMicroModel(tuple([-8.5]+[0.]*15),tuple([-8.5]+[0.]*15))
    assert 0<model.flow_lps(10,.3)<.05

def test_invalid_acceleration_or_coefficients():
    with pytest.raises(ValueError):features(-1,0)
    with pytest.raises(ValueError):VTMicroModel((1.,),(1.,))

def test_offline_fit_on_synthetic_measurements_is_possible():
    pytest.importorskip('numpy')
    rows=[]
    for trip in range(10):
        for step in range(80):
            v=3+(step%24)*.55
            a=(.4+(step%6)*.1)*(1 if step%2 else -1)
            q=math.exp(-9.3+.012*v+.06*a)
            rows.append(TrainingRow(str(trip),v,a,q))
    model=train(rows[:640])
    result=validate(model,rows[640:])
    assert result['n']==160 and math.isfinite(result['mape_pct'])
    assert result['mape_pct']<15
