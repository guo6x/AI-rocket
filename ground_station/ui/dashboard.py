from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class DashboardWidget(QWidget):
    """
    仪表盘面板组件，用于显示核心飞行参数 (数值显示)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100) # 固定高度
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 定义需要展示的字段（使用滤波后的数据作为主显示）
        self.indicators = {
            "time": self.create_indicator_card("Mission Time (ms)", "0"),
            "alt": self.create_indicator_card("Altitude (m)", "0.00"),
            "pitch_flt": self.create_indicator_card("Pitch Flt (°)", "0.00"),
            "roll_flt": self.create_indicator_card("Roll Flt (°)", "0.00"),
            "yaw": self.create_indicator_card("Yaw (°)", "0.00"),
            "batt": self.create_indicator_card("BAT (V)", "0.0"),
            "auto": self.create_indicator_card("Mode", "MANUAL"),
            "fstate": self.create_indicator_card("F-STATE", "IDLE")
        }
        
        for key, widget in self.indicators.items():
            layout.addWidget(widget)

    def create_indicator_card(self, title, initial_value):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("background-color: #2b2b2b; color: white; border-radius: 5px;")
        
        v_layout = QVBoxLayout(card)
        v_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #aaaaaa;")
        
        value_label = QLabel(initial_value)
        # 用数字字体来显示数据更好看
        value_label.setFont(QFont("Consolas", 16, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        
        v_layout.addWidget(title_label)
        v_layout.addWidget(value_label)
        
        # 把用来更新的 Label 挂在 card 上方便后续调用
        card.value_label = value_label
        return card

    def update_indicators(self, parsed_data):
        """
        根据解析好的字典更新 UI。如果字典里有这个键，就刷新数字。
        """
        for key, value in parsed_data.items():
            if key in self.indicators:
                # 特殊处理 auto 模式指示
                if key == "auto":
                    if value:
                        display_text = "AUTO"
                        self.indicators[key].value_label.setStyleSheet("color: #4caf50;")
                    else:
                        display_text = "MANUAL"
                        self.indicators[key].value_label.setStyleSheet("color: #ff9800;")
                # 飞行阶段状态灯
                elif key == "fstate":
                    display_text = str(value)
                    color_map = {
                        "IDLE": "#9e9e9e",      # 灰
                        "ARMED": "#ff9800",      # 橙 (待命)
                        "POWERED": "#f44336",    # 红 (升空)
                        "COAST": "#2196f3",      # 蓝 (滑行)
                        "DESCENT": "#4caf50",    # 绿 (下降)
                        "LANDED": "#9c27b0",     # 紫 (着陆)
                    }
                    c = color_map.get(str(value), "#ffffff")
                    self.indicators[key].value_label.setStyleSheet(f"color: {c}; font-weight: bold;")
                elif isinstance(value, float):
                    display_text = f"{value:.2f}"
                else:
                    display_text = str(value)
                    
                self.indicators[key].value_label.setText(display_text)
