# Experimental VT-Micro-inspired offline calibration

Training requires per-second measured *instantaneous* Pride fuel flow (litres/second), speed (m/s), acceleration (m/s²) and a trip identifier. A single total fuel number for an entire trip is insufficient to fit 32 coefficients.

The implementation uses two third-order speed/acceleration polynomial regressions in log fuel rate, with normalized features and ridge regularization. It is **inspired by** VT-Micro but is NOT a reproduction of a published parameter set.

Run `uv sync --extra science`, then `uv run python scripts/calibrate_vt_micro.py data/private/pride-fuel-samples.csv`. Real measured data must be collected legally and with participant consent. Training and holdout are split by **trip**, not sample, to prevent leakage. The JSON output contains coefficients and holdout MAE/MAPE, no participant identifiers.

The trained model is marked `experimental_not_approved` and must NOT automatically replace the physics model until an independent scientific assessment, sanity checks and uncertainty analysis are completed. Synthetic fixture tests only verify implementation behavior, not predictive performance in Tehran.
