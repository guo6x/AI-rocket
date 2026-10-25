"""Own Qt objects until deterministic teardown, before Python finalization."""

import gc

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication
from shiboken6 import delete


def _drain_deferred_deletes(app):
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def qt_application():
    """Keep one QApplication alive even for tests that only need QCoreApplication."""
    app = QApplication.instance()
    owns_app = app is None
    if owns_app:
        app = QApplication([])
    yield app
    _drain_deferred_deletes(app)
    if owns_app:
        delete(app)
    gc.collect()


@pytest.fixture(autouse=True)
def cleanup_qt_widgets(qt_application):
    """close() hides widgets; also destroy them while Qt and Python are live."""
    yield
    for widget in qt_application.topLevelWidgets():
        # pyqtgraph also exposes parentless internal menus/tool windows here;
        # only the application windows under test own the complete graph.
        if (
            widget.parentWidget() is not None
            or not type(widget).__module__.startswith("ui.")
        ):
            continue
        for timer in widget.findChildren(QTimer):
            timer.stop()
        widget.close()
        widget.deleteLater()
    _drain_deferred_deletes(qt_application)
