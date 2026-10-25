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
    widget.gl_view.paintGL()
    assert paint.call_count == 1
    assert len(errors) == 1


def test_successful_paint_is_recorded_separately_from_context(monkeypatch):
    monkeypatch.setattr(gl.GLViewWidget, "paintGL", lambda _: None)
    widget = CheckedGLViewWidget()
    widget.paintGL()
    assert widget.render_ok and widget.render_error is None
    widget.deleteLater()
