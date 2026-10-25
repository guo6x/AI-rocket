"""A duration observation cannot be substituted with N fast synthetic frames."""
from scripts.system_v1_runtime import soak_finished


def test_long_wall_clock_soak_requires_actual_elapsed_duration():
    assert not soak_finished(target_seconds=7200, elapsed_seconds=300,
                             sample_count=1000000, sample_target=4500)
    assert not soak_finished(target_seconds=7200, elapsed_seconds=7199.99,
                             sample_count=900000, sample_target=4500)
    assert soak_finished(target_seconds=7200, elapsed_seconds=7200,
                         sample_count=100000, sample_target=4500)


def test_short_legacy_sample_soak_still_requires_requested_count():
    assert not soak_finished(target_seconds=0, elapsed_seconds=999999,
                             sample_count=4499, sample_target=4500)
    assert soak_finished(target_seconds=0, elapsed_seconds=300,
                         sample_count=4500, sample_target=4500)
