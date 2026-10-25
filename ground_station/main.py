import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QSurfaceFormat

# 把当前脚本所在目录加到系统路径，方便 import core 和 ui
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from core.opengl_backend import configure_pyopengl_backend

def create_application(argv=None):
    # Keep desktop GL as the default. An explicit software selection must use
    # the same dispatcher in Qt and PyOpenGL, before any GL functions import.
    os.environ.setdefault("QT_OPENGL", "desktop")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    backend_error = None
    try:
        backend = configure_pyopengl_backend()
    except (RuntimeError, OSError) as error:
        backend, backend_error = "unavailable", str(error)

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    # 强制降低 OpenGL 版本要求，提升硬件兼容性 (虚拟机/老显卡/核显)
    fmt = QSurfaceFormat()
    fmt.setVersion(2, 1)
    fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv if argv is None else argv)
    app.setProperty("opengl_backend", backend)
    app.setProperty("opengl_backend_error", backend_error)
    app.setStyle("Fusion") # 现代样式的跨平台基础
    return app


def main():
    app = create_application()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
