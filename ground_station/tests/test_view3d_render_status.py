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


def test_actual_item_tree_error_is_not_a_successful_frame_and_restores_stack(monkeypatch):
    """Exercise pyqtgraph traversal, not a stub that raises from paintGL itself."""
    from importlib import import_module
    from PySide6.QtGui import QMatrix4x4

    view_module = import_module("pyqtgraph.opengl.GLViewWidget")
    monkeypatch.setattr(view_module.GL, "glClearColor", lambda *_args: None)
    monkeypatch.setattr(view_module.GL, "glClear", lambda *_args: None)
    view = CheckedGLViewWidget()
    monkeypatch.setattr(view, "setProjection", lambda *_args: None)
    monkeypatch.setattr(view, "setModelview", lambda: None)
    original_transform = QMatrix4x4()
    view._modelViewStack[:] = [original_transform]

    class Item:
        def __init__(self, parent=None, error=None):
            self.parent = parent
            self.children = []
            self.paint = Mock(side_effect=error)
            if parent is not None:
                parent.children.append(self)

        def parentItem(self):
            return self.parent

        def childItems(self):
            return list(self.children)

        def depthValue(self):
            return 0

        def visible(self):
            return True

        def transform(self):
            return QMatrix4x4()

    root = Item()
    child = Item(root, RuntimeError("synthetic child item paint failure"))
    view.items[:] = [root]
    failures = []
    view.render_failed.connect(failures.append)

    view.paintGL()

    assert len(view._modelViewStack) == 1
    assert view._modelViewStack[0] is original_transform
    assert not view.render_ok
    assert "synthetic child item paint failure" in view.render_error
    assert failures == [view.render_error]
    view.paintGL()
    assert child.paint.call_count == 1
    assert len(failures) == 1
    view.deleteLater()


def test_context_initialization_failure_activates_visible_fallback_once(monkeypatch):
    initialize = Mock(side_effect=RuntimeError("synthetic context initialization failure"))
    monkeypatch.setattr(gl.GLViewWidget, "initializeGL", initialize)
    widget = Rocket3DWidget()
    failures = []
    widget.render_failed.connect(failures.append)

    widget.gl_view.initializeGL()

    assert not widget.gl_view.render_ok
    assert "synthetic context initialization failure" in widget.gl_view.render_error
    assert not widget.fallback.isHidden()
    assert "DEGRADED / NOT_VERIFIED" in widget.error_label.text()
    assert len(failures) == 1
    widget.gl_view.initializeGL()
    assert initialize.call_count == 1
    assert len(failures) == 1


def test_backend_configuration_error_retains_2d_without_loading_gl_view(monkeypatch, qt_application):
    from ui import main_window

    previous = qt_application.property("opengl_backend_error")
    monkeypatch.setattr(main_window, "get_available_ports", lambda: [])
    qt_application.setProperty("opengl_backend_error", "synthetic unsafe late backend switch")
    try:
        window = main_window.MainWindow()
        assert not hasattr(window.view3d_panel, "gl_view")
        assert "synthetic unsafe late backend switch" in window.view3d_status_label.text()
        assert "2D fallback active" in window.view3d_status_label.text()
        window.close()
    finally:
        qt_application.setProperty("opengl_backend_error", previous)


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
    # QImage stores physical pixels (Windows here uses 150% display scaling).
    # Preserve exact logical geometry without assuming devicePixelRatio == 1.
    assert zero_frame.deviceIndependentSize().width() == 600
    assert zero_frame.deviceIndependentSize().height() == 360
    dpr = zero_frame.devicePixelRatio()
    assert zero_frame.width() == round(600 * dpr)
    assert zero_frame.height() == round(360 * dpr)
    # Confirm background and instrument pixels are actually different.
    assert zero_frame.pixelColor(round(5 * dpr), round(5 * dpr)) != zero_frame.pixelColor(round(150 * dpr), round(180 * dpr))
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


def test_unrendered_gl_tab_eventually_activates_fallback_without_claiming_3d(monkeypatch, qt_application):
    import sys
    import time
    from types import SimpleNamespace
    from PySide6.QtWidgets import QWidget
    from ui import main_window

    class FakeView(QWidget):
        def __init__(self):
            super().__init__()
            self.gl_view = SimpleNamespace(
                isVisible=lambda: True, isValid=lambda: False,
                render_ok=False, render_error=None,
            )
            self.fallback = QWidget(self)
            self.fallback.hide()
            self.failures = []

        def on_render_failure(self, text):
            self.failures.append(text)
            self.gl_view.render_error = text
            self.fallback.show()

        def update_attitude(self, *_args):
            pass

    monkeypatch.setattr(main_window, "get_available_ports", lambda: [])
    monkeypatch.setitem(sys.modules, "ui.view3d_widget", SimpleNamespace(Rocket3DWidget=FakeView))
    window = main_window.MainWindow()
    window.command_timer.stop()
    window.tab_widget.setCurrentWidget(window.view3d_panel)
    window._gl_no_frame_since = time.monotonic() - 2.0
    window.poll_link_and_command_state()
    assert window.view3d_panel.failures == ["no successful OpenGL frame after 1.5 seconds"]
    assert not window.view3d_panel.fallback.isHidden()
    assert "3D DEGRADED / NOT_VERIFIED" in window.view3d_status_label.text()
    window.data_thread = None
    window.close()
