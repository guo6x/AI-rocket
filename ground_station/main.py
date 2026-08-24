import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtGui import QSurfaceFormat

# 把当前脚本所在目录加到系统路径，方便 import core 和 ui
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

def main():
    # 终极修复 PyQtGraph/PyOpenGL 在 PySide6 Windows 下的黑屏/上下文崩溃
    # 强制使用旧版 Desktop OpenGL，关闭可能导致冲突的新版 Rhi 或 GLES2
    os.environ["QT_OPENGL"] = "desktop"
    os.environ["QT_QUICK_BACKEND"] = "software"
    
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    # 强制降低 OpenGL 版本要求，提升硬件兼容性 (虚拟机/老显卡/核显)
    fmt = QSurfaceFormat()
    fmt.setVersion(2, 1)
    fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 现代样式的跨平台基础
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
