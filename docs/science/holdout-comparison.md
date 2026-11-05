# Scientific holdout: Pride baseline vs route-aware physics

`GET /api/v1/admin/calibration/metrics/` evaluates paired predictions on
**the same consented actual trips**:
`baseline_l` (reference consumption × planned distance) and
`estimated_l` (experimental route-aware physics model).

Assign previously unassigned trips without exposing personal data:
```bash
cd backend
python manage.py assign_calibration_splits --dry-run
python manage.py assign_calibration_splits
```
A stable hash of the route request groups alternative route predictions in
one split, preventing request-level leakage. Existing assignments are kept.

The report includes matched sample counts, exclusions, separate model
MAE/RMSE/MAPE and relative MAE improvement vs baseline, which is **not an
accuracy percentage**. A negative value is possible.

Actual distance outside 90–110% of planned distance makes the observation
incomparable and excludes it; duplicate submissions of one prediction are
also excluded from the metric. At least five eligible holdout records are
required for preliminary feedback. Five samples do **not** establish
statistical significance, per-driver generalization, or validated Pride
coefficients. Real per-trip OBD fuel measurements, separate drivers and
independent evaluation are essential for reliable conclusions.
