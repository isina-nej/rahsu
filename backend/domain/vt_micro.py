"""Calibratable VT-Micro-inspired speed/acceleration fuel-rate model.

NOT the published VT-Micro coefficients. This implementation scales inputs,
uses two separate third-order polynomial regressions and requires measured
instantaneous fuel-flow in L/s with trip-disjoint holdout for validation.
"""
from dataclasses import dataclass
from math import exp, isfinite, log
from typing import Sequence


def features(v_mps: float, a_mps2: float) -> tuple[float,...]:
    if not all(isfinite(x) for x in (v_mps,a_mps2)) or v_mps<0 or abs(a_mps2)>10:
        raise ValueError("Invalid speed or acceleration")
    v=v_mps/20.0
    a=a_mps2/3.0
    return tuple(v**i * a**j for i in range(4) for j in range(4))


@dataclass(frozen=True)
class VTMicroModel:
    positive_coefficients: tuple[float,...]
    negative_coefficients: tuple[float,...]
    version: str = 'vtmicro-scaled-v1'

    def __post_init__(self):
        if len(self.positive_coefficients)!=16 or len(self.negative_coefficients)!=16:
            raise ValueError("VT-Micro requires 16 coefficients in each acceleration regime")
        if not all(isfinite(x) for x in (*self.positive_coefficients,*self.negative_coefficients)):
            raise ValueError("Non-finite coefficients")

    def flow_lps(self,v_mps:float,a_mps2:float)->float:
        x=features(v_mps,a_mps2)
        coeffs=self.positive_coefficients if a_mps2>=0 else self.negative_coefficients
        exponent=sum(w*f for w,f in zip(coeffs,x))
        # Prevent overflow from extrapolation; these are safety bounds, not calibration.
        return exp(max(-20,min(0,exponent)))


@dataclass(frozen=True)
class TrainingRow:
    trip_id: str
    speed_mps: float
    acceleration_mps2: float
    measured_lps: float


def train(rows:Sequence[TrainingRow],ridge:float=0.02)->VTMicroModel:
    """Numpy least-squares ridge fit; for offline calibration, not web requests."""
    import numpy as np
    if len(rows)<100 or not isfinite(ridge) or ridge<=0:
        raise ValueError("Need >=100 measured rows and positive regularization")
    groups=[[],[]]
    for row in rows:
        if (not row.trip_id or not isfinite(row.measured_lps)
             or not 0 < row.measured_lps <= .05):
            raise ValueError("Invalid measured fuel flow")
        x=features(row.speed_mps,row.acceleration_mps2)
        groups[0 if row.acceleration_mps2>=0 else 1].append((x,log(row.measured_lps)))
    if any(len(group)<40 for group in groups):
        raise ValueError("Insufficient data in each acceleration regime")
    estimates=[]
    for group in groups:
        X=np.array([sample[0] for sample in group],dtype=float)
        y=np.array([sample[1] for sample in group],dtype=float)
        penalty=np.eye(16)*ridge
        penalty[0,0]=0
        coef=np.linalg.solve(X.T@X+penalty,X.T@y)
        estimates.append(tuple(float(x) for x in coef))
    return VTMicroModel(estimates[0],estimates[1])


def validate(model:VTMicroModel,rows:Sequence[TrainingRow])->dict:
    if not rows:raise ValueError("Empty holdout")
    predictions=[model.flow_lps(x.speed_mps,x.acceleration_mps2) for x in rows]
    actual=[x.measured_lps for x in rows]
    if any(not isfinite(x) or x<=0 for x in actual):
        raise ValueError("Invalid holdout observations")
    n=len(rows)
    return {'n':n,
       'mae_lps':sum(abs(p-a) for p,a in zip(predictions,actual))/n,
       'mape_pct':100*sum(abs(p-a)/a for p,a in zip(predictions,actual))/n}
