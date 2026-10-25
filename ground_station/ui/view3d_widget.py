import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtGui, QtCore
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, QTimer


class CheckedGLViewWidget(gl.GLViewWidget):
    """Qt can retain a valid context while paintGL raises a driver error."""
    render_failed = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_ok = False
        self.render_error = None

    def paintGL(self):
        if self.render_error is not None:
            return
        try:
            super().paintGL()
            self.render_ok = True
        except Exception as error:
            self.render_ok = False
            self.render_error = repr(error)
            self.render_failed.emit(self.render_error)

class Rocket3DWidget(QWidget):
    """
    基于 PyOpenGL 和 PyQtGraph 的 3D 姿态指示器
    用来实时渲染火箭的三轴姿态 (Roll, Pitch, Yaw)
    """
    render_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建 OpenGL 视图
        self.gl_view = CheckedGLViewWidget()
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.gl_view.render_failed.connect(self.on_render_failure)
        self.gl_view.opts['distance'] = 25
        self.gl_view.opts['elevation'] = 20
        self.gl_view.opts['azimuth'] = 45

        # 设置深色科幻背景
        self.gl_view.setBackgroundColor('#181818')

        # 添加底部网格，作为大地参考面
        grid = gl.GLGridItem()
        grid.scale(2, 2, 2)
        grid.translate(0, 0, -6) # 把网格往下放，位于火箭底部
        self.gl_view.addItem(grid)

        # 添加 XYZ 坐标系 (红=X(向右), 绿=Y(向前), 蓝=Z(向上))
        self.axis = gl.GLAxisItem()
        self.axis.setSize(5, 5, 5)
        self.gl_view.addItem(self.axis)

        # 添加火箭本体模型 (用细长方体代替，长宽高 2x2x12)
        # 半透明浅蓝色
        from PySide6.QtGui import QVector3D
        self.rocket = gl.GLBoxItem(size=QVector3D(2, 2, 12), color=(50, 150, 255, 180))
        self.gl_view.addItem(self.rocket)

        layout.addWidget(self.gl_view)
        layout.addWidget(self.error_label)

        self.reset_pose()

    def on_render_failure(self, error):
        self.error_label.setText(f"3D DEGRADED / NOT_VERIFIED — {error}\nDashboard and curves remain available. Simplified model only; not CAD.")
        self.error_label.show()
        # Defer GL widget hiding until paintGL has returned.
        QTimer.singleShot(0, self.gl_view, self.gl_view.hide)
        self.render_failed.emit(error)

    def reset_pose(self):
        self.update_attitude(0, 0, 0)

    def update_attitude(self, roll, pitch, yaw):
        """
        根据 Roll, Pitch, Yaw (以度为单位) 更新 3D 模型的旋转。
        """
        transform = QtGui.QMatrix4x4()

        # 旋转顺序：航向(Yaw) -> 俯仰(Pitch) -> 横滚(Roll)
        transform.rotate(yaw, 0, 0, 1)
        transform.rotate(pitch, 0, 1, 0)
        transform.rotate(roll, 1, 0, 0)

        # GLBoxItem 的默认坐标系原点在顶点 (0,0,0) 并向 +X,+Y,+Z 延伸 size
        # 所以要把它的旋转中心（重心）移动到世界坐标系的原点 (0,0,0)
        # 重心 = 原点平移了 size / 2 = (-1, -1, -6)
        transform.translate(-1, -1, -6)

        # 应用矩阵到火箭本体
        self.rocket.setTransform(transform)

        # 让姿态轴跟着火箭一起旋转直观显示指向
        axis_transform = QtGui.QMatrix4x4()
        axis_transform.rotate(yaw, 0, 0, 1)
        axis_transform.rotate(pitch, 0, 1, 0)
        axis_transform.rotate(roll, 1, 0, 0)
        self.axis.setTransform(axis_transform)
