"""Rendering exceptions must become a visible degraded state, not context PASS."""

from unittest.mock import Mock

import pyqtgraph.opengl as gl

from ui.view3d_widget import CheckedGLViewWidget, Rocket3DWidget


def test_valid_context_is_not_a_successful_frame_and_paint_error_is_sticky(monkeypatch):
    paint = Mock(side_effect=RuntimeError("synthetic driver error"))
    monkeypatch.setattr(gl.GLViewWidget, "paintGL", paint)
    widget = Rocket3DWidget()
    errors = []
    widget.render_failed.connect(errors.append)
    assert not widget.gl_view.render_ok
    widget.gl_view.paintGL()
    assert not widget.gl_view.render_ok
    assert "synthetic driver error" in widget.gl_view.render_error
    assert len(errors) == 1
    assert "DEGRADED / NOT_VERIFIED" in widget.error_label.text()
    assert not widget.fallback.isHidden()
    assert "2D fallback active" in widget.error_label.text()
    widget.gl_view.paintGL()
    assert paint.call_count == 1
    assert len(errors) == 1


def test_successful_paint_is_recorded_separately_from_context(monkeypatch):
    monkeypatch.setattr(gl.GLViewWidget, "paintGL", lambda _: None)
    widget = CheckedGLViewWidget()
    widget.paintGL()
    assert widget.render_ok and widget.render_error is None
    widget.deleteLater()


def test_2d_fallback_is_real_qt_painting_and_updates_for_two_poses(qt_application):
    from ui.attitude_fallback import AttitudeFallbackWidget
    from PySide6.QtCore import Qt

    widget = AttitudeFallbackWidget()
    widget.resize(600, 360)
    widget.show()
    qt_application.processEvents()
    widget.update_attitude(0.0, 0.0)
    qt_application.processEvents()
    zero_frame = widget.grab().toImage()
    assert not zero_frame.isNull()
    assert zero_frame.width() == 600 and zero_frame.height() == 360
    # Confirm background and instrument pixels are actually different.
    assert zero_frame.pixelColor(5, 5) != zero_frame.pixelColor(150, 180)
    widget.update_attitude(35.0, -20.0)
    qt_application.processEvents()
    changed_frame = widget.grab().toImage()
    assert not changed_frame.isNull() and changed_frame != zero_frame
    assert widget.pitch_deg == -20.0 and widget.roll_deg == 35.0
    assert "2D" in widget.accessibleName()
    widget.close()


def test_2d_fallback_fails_closed_on_bad_data_without_repainting_old_pose(qt_application):
    import pytest
    from ui.attitude_fallback import AttitudeFallbackWidget

    widget = AttitudeFallbackWidget()
    widget.update_attitude(12.0, -7.0)
    for value in (None, float("nan"), float("inf"), "12", 10**400):
        with pytest.raises((ValueError, TypeError)):
            widget.update_attitude(value, 0.0)
        assert (widget.roll_deg, widget.pitch_deg) == (12.0, -7.0)
    widget.deleteLater()
