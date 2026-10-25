"""A duration observation cannot be substituted with N fast synthetic frames."""
from scripts.system_v1_runtime import gl_pixel_evidence, soak_finished


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


def test_framebuffer_evidence_rejects_null_blank_and_unchanged_frames():
    from PySide6.QtGui import QColor, QImage

    blank = QImage(40, 40, QImage.Format.Format_RGBA8888)
    blank.fill(QColor(24, 24, 24))
    first = blank.copy()
    second = blank.copy()
    for x in range(10):
        for y in range(10):
            first.setPixelColor(x, y, QColor(50, 150, 255))
            second.setPixelColor(x + 20, y + 20, QColor(50, 150, 255))
    for pair in ([QImage(), first], [blank, blank], [first, first], [blank, first]):
        assert not gl_pixel_evidence(pair)["distinct_nonempty_frames"]
    alpha_only = first.copy()
    for x in range(10):
        for y in range(10):
            alpha_only.setPixelColor(x, y, QColor(50, 150, 255, 127))
    assert not gl_pixel_evidence([first, alpha_only])["distinct_nonempty_frames"]
    evidence = gl_pixel_evidence([first, second])
    assert evidence == {"distinct_nonempty_frames": True, "changed_pixels": 200,
                        "blue_pixels_per_pose": [100, 100]}
