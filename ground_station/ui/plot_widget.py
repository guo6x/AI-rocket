import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from PySide6.QtWidgets import QWidget, QVBoxLayout
import collections
import time

class RealtimePlotWidget(QWidget):
    """
    基于 PyQtGraph 封装的实时滚动折线图组件
    """
    def __init__(self, parent=None, max_points=1000, title="Real-time Telemetry"):
        super().__init__(parent)
        
        self.max_points = max_points
        
        # 使用 deque 构造定长队列，自动丢弃老数据
        self.history_time = collections.deque(maxlen=max_points)
        self.history_data1 = collections.deque(maxlen=max_points)
        self.history_data2 = collections.deque(maxlen=max_points)
        
        self.setup_ui(title)
        
    def setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 全局配置背景和前景色
        pg.setConfigOption('background', '#181818')
        pg.setConfigOption('foreground', '#d3d3d3')
        
        # 创建 Plot 容器
        self.plot_item = pg.PlotWidget(title=title)
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.setLabel('bottom', 'Time', units='s')
        
        # 创建两根折线的载体
        # 线条 1：比如 Altitude (高度)
        self.curve1 = self.plot_item.plot(pen=pg.mkPen(color='#00ff00', width=2), name="Alt")
        # 线条 2：比如 Pitch (俯仰角)
        self.curve2 = self.plot_item.plot(pen=pg.mkPen(color='#ff00ff', width=2), name="Pitch")
        
        self.plot_item.addLegend()
        
        layout.addWidget(self.plot_item)

    def update_plot(self, current_time, val1, val2=None):
        """
        每次收到新数据时调用，自动推进图表
        """
        self.history_time.append(current_time)
        self.history_data1.append(val1)
        
        if val2 is not None:
            self.history_data2.append(val2)
            
        # 刷新视图
        self.curve1.setData(self.history_time, self.history_data1)
        if val2 is not None:
            self.curve2.setData(self.history_time, self.history_data2)

    def clear(self):
        self.history_time.clear()
        self.history_data1.clear()
        self.history_data2.clear()
        self.curve1.setData([], [])
        self.curve2.setData([], [])
