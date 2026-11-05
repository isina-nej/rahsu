#!/usr/bin/env python3
"""Offline Pride VT-Micro regression from consented per-trip measured CSV.

CSV columns: trip_id,speed_mps,acceleration_mps2,measured_lps.
At least two distinct trip IDs in each split and 100 train rows are required.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from domain.vt_micro import TrainingRow,train,validate  # noqa:E402

def read_csv(path:Path):
    with path.open(newline='',encoding='utf-8') as handle:
        data=csv.DictReader(handle)
        required={'trip_id','speed_mps','acceleration_mps2','measured_lps'}
        if not required.issubset(data.fieldnames or []):
            raise ValueError(f'Missing fields: {sorted(required)}')
        return [TrainingRow(row['trip_id'],float(row['speed_mps']),
             float(row['acceleration_mps2']),float(row['measured_lps'])) for row in data]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('csv_file',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'data/models/priority-pride-vtmicro.json')
    args=p.parse_args()
    rows=read_csv(args.csv_file)
    trip_ids=sorted({r.trip_id for r in rows})
    if len(trip_ids)<8:
        raise SystemExit('Need >=8 distinct measured trips for trip-disjoint validation')
    holdout={tid for tid in trip_ids if int(hashlib.sha256(tid.encode()).hexdigest(),16)%5==0}
    if len(holdout)<2 or len(trip_ids)-len(holdout)<2:
        # Deterministic fallback still splits by entire trips, never time-steps.
        holdout=set(trip_ids[-max(2,len(trip_ids)//5):])
    training=[r for r in rows if r.trip_id not in holdout]
    validation=[r for r in rows if r.trip_id in holdout]
    model=train(training)
    report=validate(model,validation)
    artifact={'model':'vtmicro-scaled','version':model.version,'vehicle':'pride-131',
       'trained_at':datetime.now(timezone.utc).isoformat(),
       'training_rows':len(training),'validation_rows':len(validation),
       'train_trip_count':len(set(r.trip_id for r in training)),
       'validation_trip_count':len(holdout),
       'features':'speed_mps/20 and acceleration_mps2/3, cubic cross-products',
       'positive_coefficients':model.positive_coefficients,
       'negative_coefficients':model.negative_coefficients,
       'holdout_metrics':report,'status':'experimental_not_approved'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # No raw data or participant identifiers in model artifact.
    args.output.write_text(json.dumps(artifact,indent=2),encoding='utf-8')
    os.chmod(args.output,0o600)
    print(json.dumps({'holdout':report,'output':str(args.output)}))

if __name__=='__main__':main()
