"""Unit-tested, transparent holdout quality metrics (not model claims)."""
from math import sqrt,isfinite

def fuel_error_metrics(pairs: list[tuple[float,float]]) -> dict:
    """(observed_l, predicted_l) on independent trips. Excludes zero observed fuel."""
    if not pairs or any(not all(isfinite(v) and v>0 for v in pair) for pair in pairs):
        raise ValueError("Need positive finite observed and predicted fuel")
    errors=[pred-actual for actual,pred in pairs]
    n=len(pairs)
    return {
        'n':n,
        'mae_l':round(sum(abs(e) for e in errors)/n,4),
        'rmse_l':round(sqrt(sum(e*e for e in errors)/n),4),
        'mape_pct':round(100*sum(abs(pred-actual)/actual for actual,pred in pairs)/n,2),
        'mean_bias_l':round(sum(errors)/n,4),
    }
