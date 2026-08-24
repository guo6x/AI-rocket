import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
import collections

class ComparisonPlotWidget(QWidget):
    """
    滤波前后姿态对比曲线组件：
    - pitch_raw (虚线) vs pitch_flt (实线)
    - roll_raw (虚线) vs roll_flt (实线)
    """
    def __init__(self, parent=None, max_points=1000,
                 title="Attitude: Raw vs Filtered"):
        super().__init__(parent)
        self.max_points = max_points

        # 定长队列
        self.time_q = collections.deque(maxlen=max_points)
        self.pitch_raw_q = collections.deque(maxlen=max_points)
        self.pitch_flt_q = collections.deque(maxlen=max_points)
        self.roll_raw_q = collections.deque(maxlen=max_points)
        self.roll_flt_q = collections.deque(maxlen=max_points)

        self.setup_ui(title)

    def setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOption('background', '#181818')
        pg.setConfigOption('foreground', '#d3d3d3')

        self.plot_item = pg.PlotWidget(title=title)
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.setLabel('bottom', 'Time', units='s')
        self.plot_item.setLabel('left', 'Angle', units='°')

        # Pitch Raw - 虚线橙色
        self.c_pitch_raw = self.plot_item.plot(
            pen=pg.mkPen(color='#ff9800', width=1, style=pg.QtCore.Qt.DashLine),
            name="Pitch Raw"
        )
        # Pitch Filtered - 实线橙色加粗
        self.c_pitch_flt = self.plot_item.plot(
            pen=pg.mkPen(color='#ff9800', width=2),
            name="Pitch Flt"
        )
        # Roll Raw - 虚线青色
        self.c_roll_raw = self.plot_item.plot(
            pen=pg.mkPen(color='#00bcd4', width=1, style=pg.QtCore.Qt.DashLine),
            name="Roll Raw"
        )
        # Roll Filtered - 实线青色加粗
        self.c_roll_flt = self.plot_item.plot(
            pen=pg.mkPen(color='#00bcd4', width=2),
            name="Roll Flt"
        )

        self.plot_item.addLegend()
        layout.addWidget(self.plot_item)

    def update_plot(self, t, pitch_raw, pitch_flt, roll_raw, roll_flt):
        self.time_q.append(t)
        self.pitch_raw_q.append(pitch_raw)
        self.pitch_flt_q.append(pitch_flt)
        self.roll_raw_q.append(roll_raw)
        self.roll_flt_q.append(roll_flt)

        self.c_pitch_raw.setData(self.time_q, self.pitch_raw_q)
        self.c_pitch_flt.setData(self.time_q, self.pitch_flt_q)
        self.c_roll_raw.setData(self.time_q, self.roll_raw_q)
        self.c_roll_flt.setData(self.time_q, self.roll_flt_q)

    def clear(self):
        self.time_q.clear()
        self.pitch_raw_q.clear()
        self.pitch_flt_q.clear()
        self.roll_raw_q.clear()
        self.roll_flt_q.clear()
        self.c_pitch_raw.setData([], [])
        self.c_pitch_flt.setData([], [])
        self.c_roll_raw.setData([], [])
        self.c_roll_flt.setData([], [])
