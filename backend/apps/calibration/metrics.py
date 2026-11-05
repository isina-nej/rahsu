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

def paired_model_comparison(triples: list[tuple[float,float,float]]) -> dict:
    """Holdout (observed, distance baseline, physics) in litres per trip."""
    if not triples:
        raise ValueError('Need paired observations')
    baseline=fuel_error_metrics([(observed,base) for observed,base,_ in triples])
    physics=fuel_error_metrics([(observed,candidate) for observed,_,candidate in triples])
    baseline_mae=sum(abs(observed-base) for observed,base,_ in triples)/len(triples)
    physics_mae=sum(abs(observed-candidate) for observed,_,candidate in triples)/len(triples)
    improvement=(100*(baseline_mae-physics_mae)/baseline_mae if baseline_mae else None)
    return {
        'n':len(triples), 'baseline':baseline, 'physics':physics,
        'relative_mae_improvement_pct':round(improvement,2) if improvement is not None else None,
        'candidate_beats_baseline_mae':physics_mae<baseline_mae,
        'independent_validation_required':True,
    }
