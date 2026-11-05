"""The split must not leak one route request across train and holdout."""
from apps.calibration.management.commands.assign_calibration_splits import split_for_request

def test_hash_partition_is_stable_and_grouped():
    assert split_for_request(123)==split_for_request(123)
    assert split_for_request(123) in ('train','holdout')
    distribution={split_for_request(n) for n in range(1,70)}
    assert distribution=={'train','holdout'}
