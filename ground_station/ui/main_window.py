import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QComboBox, QPushButton, QTextEdit, QLabel,
                               QLineEdit, QTabWidget, QStackedWidget)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PySide6.QtCore import Qt, QTimer
from core.command_link import CommandTracker, parse_command_response
from core.serial_reader import SerialReader, get_available_ports
from core.udp_reader import UdpReader
from core.data_logger import DataLogger
from core.telemetry_parser import TelemetryParser
from ui.dashboard import DashboardWidget
from ui.command_panel import CommandPanel

# 飞行阶段颜色映射 (跟 dashboard.py 一致)
FSTATE_COLORS = {
    "IDLE":    "#9e9e9e",
    "ARMED":   "#ff9800",
    "POWERED": "#f44336",
    "COAST":   "#2196f3",
    "DESCENT": "#4caf50",
    "LANDED":  "#9c27b0",
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Ad Astra Ground Station - V0.4")
        self.resize(1100, 800)
        
        self.data_thread = None  # 统一名称：可以是 SerialReader 或 UdpReader
        self.connection_mode = None
        self.last_rx_monotonic = None
        self.command_tracker = CommandTracker(timeout_seconds=1.5)
        self.parser = TelemetryParser()

        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_logger = DataLogger(log_dir=os.path.join(base_dir, "logs"))
        self.start_time = None
        self.last_fstate = None  # 飞行阶段变化跟踪

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # ========== 1. 顶部控制栏 ==========
        control_layout = QHBoxLayout()
        font = QFont("Consolas", 10)

        # 模式切换
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["串口 Serial", "WiFi UDP"])
        self.mode_combo.setFont(font)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        control_layout.addWidget(QLabel("模式:"))
        control_layout.addWidget(self.mode_combo)

        # 串口设置（默认显示）
        self.serial_stack = QWidget()
        serial_layout = QHBoxLayout(self.serial_stack)
        serial_layout.setContentsMargins(0, 0, 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.refresh_ports()
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFont(font)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200", "256000"])
        self.baudrate_combo.setCurrentText("115200")
        self.baudrate_combo.setFont(font)
        serial_layout.addWidget(QLabel("端口:"))
        serial_layout.addWidget(self.port_combo)
        serial_layout.addWidget(self.refresh_btn)
        serial_layout.addWidget(QLabel("波特率:"))
        serial_layout.addWidget(self.baudrate_combo)

        # UDP 设置（默认隐藏）
        self.udp_stack = QWidget()
        udp_layout = QHBoxLayout(self.udp_stack)
        udp_layout.setContentsMargins(0, 0, 0, 0)
        self.udp_port_input = QLineEdit("9876")
        self.udp_port_input.setMaximumWidth(80)
        self.udp_port_input.setFont(font)
        udp_layout.addWidget(QLabel("监听端口:"))
        udp_layout.addWidget(self.udp_port_input)
        self.udp_ip_input = QLineEdit()
        self.udp_ip_input.setPlaceholderText("ESP unicast IPv4")
        self.udp_ip_input.setMaximumWidth(120)
        self.udp_ip_input.setFont(font)
        udp_layout.addWidget(QLabel("ESP IP:"))
        udp_layout.addWidget(self.udp_ip_input)
        self.udp_command_port_input = QLineEdit("9876")
        self.udp_command_port_input.setMaximumWidth(80)
        self.udp_command_port_input.setFont(font)
        udp_layout.addWidget(QLabel("命令端口:"))
        udp_layout.addWidget(self.udp_command_port_input)
        self.udp_stack.setVisible(False)

        # 连接按钮
        self.connect_btn = QPushButton("🔌 连接")
        self.connect_btn.setFont(font)
        self.connect_btn.clicked.connect(self.toggle_connection)

        control_layout.addWidget(self.serial_stack)
        control_layout.addWidget(self.udp_stack)
        control_layout.addWidget(self.connect_btn)
        control_layout.addStretch()

        # ========== 2. 仪表盘 ==========
        self.dashboard = DashboardWidget()

        # ========== 3. 图表（Tab 切换） ==========
        from ui.plot_widget import RealtimePlotWidget
        from ui.comparison_plot import ComparisonPlotWidget

        self.tab_widget = QTabWidget()
        self.plot_panel = RealtimePlotWidget(title="Flight Telemetry (Alt & Pitch)")
        self.comparison_panel = ComparisonPlotWidget(title="Attitude: Raw vs Filtered")
        self.tab_widget.addTab(self.plot_panel, "📈 高度 & 俯仰")
        self.tab_widget.addTab(self.comparison_panel, "🔬 滤波对比")

        # 3D 姿态显示 Tab (可选, OpenGL 不可用时降级)
        try:
            from ui.view3d_widget import Rocket3DWidget
            self.view3d_panel = Rocket3DWidget()
            self.tab_widget.addTab(self.view3d_panel, "🛰️ 3D 姿态")
        except Exception as e:
            print(f"[WARN] 3D 姿态组件加载失败 (需 PyOpenGL): {e}")
            self.view3d_panel = None

        # ========== 4. 日志 + 指令面板 (横向分割) ==========
        bottom_layout = QHBoxLayout()

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        self.log_display.setStyleSheet("background-color: #1e1e1e; color: #00ff00;")

        self.command_panel = CommandPanel()
        self.command_panel.send_command.connect(self.on_send_command)
        self.command_panel.setMaximumWidth(420)

        bottom_layout.addWidget(self.log_display, stretch=2)
        bottom_layout.addWidget(self.command_panel, stretch=1)

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(100)
        self.command_timer.timeout.connect(self.poll_link_and_command_state)
        self.command_timer.start()

        # ========== 组装主布局 ==========
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.dashboard)
        main_layout.addWidget(self.tab_widget, stretch=2)
        main_layout.addLayout(bottom_layout, stretch=1)

    # ---- 模式切换 ----
    def on_mode_changed(self, index):
        is_serial = (index == 0)
        self.serial_stack.setVisible(is_serial)
        self.udp_stack.setVisible(not is_serial)

    # ---- 端口刷新 ----
    def refresh_ports(self):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = get_available_ports()
        # 控制台打印发现的所有端口（调试用）
        print(f"DEBUG: Found serial ports: {ports}")
        if ports:
            self.port_combo.addItems(ports)
            if current in ports:
                self.port_combo.setCurrentText(current)
            else:
                self.port_combo.setCurrentIndex(0) # 默认选中第一个
        else:
            self.port_combo.addItem("None")

    # ---- 连接/断开 ----
    def toggle_connection(self):
        if self.data_thread and self.data_thread.is_running:
            self.disconnect_data()
        else:
            self.connect_data()

    def connect_data(self):
        is_serial = (self.mode_combo.currentIndex() == 0)

        if is_serial:
            # 如果当前是 None，尝试最后刷新一次
            if self.port_combo.currentText() == "None":
                self.refresh_ports()
                
            port = self.port_combo.currentText()
            if not port or port == "None":
                self.log_message("[系统] 未找到可用串口")
                return
            baudrate = int(self.baudrate_combo.currentText())
            self.data_thread = SerialReader(port, baudrate)
            conn_info = f"{port} @ {baudrate} baud (Serial)"
            self.connection_mode = "serial"
        else:
            try:
                udp_port = int(self.udp_port_input.text())
                command_port = int(self.udp_command_port_input.text())
            except ValueError:
                self.log_message("[系统] UDP 端口必须是整数")
                self.command_panel.set_command_status("FAILED", detail="invalid port")
                return
            target_ip = self.udp_ip_input.text().strip()
            target = (target_ip, command_port)
            if not UdpReader.validate_target(target):
                self.log_message("[系统] 请输入明确的单播 ESP IPv4 地址和有效命令端口")
                self.command_panel.set_command_status("FAILED", detail="invalid WiFi target")
                return
            self.data_thread = UdpReader(port=udp_port, target_addr=target)
            conn_info = f"0.0.0.0:{udp_port} ← UDP; command → {target_ip}:{command_port}"
            self.connection_mode = "udp"

        self.data_thread.data_received.connect(self.on_data_received)
        if isinstance(self.data_thread, UdpReader):
            self.data_thread.command_response_received.connect(
                self.on_udp_command_response
            )
        self.data_thread.error_occurred.connect(self.on_error)
        self.data_thread.link_state_changed.connect(self.on_link_state_changed)

        self.data_logger.start_logging()
        self.data_thread.start()
        self.command_tracker.clear()
        self.last_rx_monotonic = None

        self.connect_btn.setText("⛔ 断开")
        self.connect_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.mode_combo.setEnabled(False)
        self.serial_stack.setEnabled(False)
        self.udp_stack.setEnabled(False)

        self.log_message(f"[系统] 已连接 {conn_info}. 正在接收数据...")
        self.command_panel.set_link_state("CONNECTING")
        self.command_panel.set_command_status("IDLE")

    def disconnect_data(self):
        if self.data_thread:
            self.data_thread.stop()
            self.data_thread = None

        self.data_logger.stop_logging()
        self.command_tracker.clear()
        self.connection_mode = None
        self.last_rx_monotonic = None
        self.start_time = None
        self.last_fstate = None
        self.plot_panel.clear()
        self.comparison_panel.clear()

        self.connect_btn.setText("🔌 连接")
        self.connect_btn.setStyleSheet("")
        self.mode_combo.setEnabled(True)
        self.serial_stack.setEnabled(True)
        self.udp_stack.setEnabled(True)

        self.log_message("[系统] 已断开连接")
        self.command_panel.set_link_state("DISCONNECTED")
        self.command_panel.set_command_status("IDLE")

    # ---- 数据接收回调 ----
    def on_data_received(self, data):
        from datetime import datetime
        timestamp = datetime.now().strftime("[%H:%M:%S.%f]")[:-4] + "]"
        self.log_display.append(f"{timestamp} {data}")
        self.log_display.ensureCursorVisible()

        command_response = parse_command_response(data)
        if command_response is not None:
            resolved = self.command_tracker.resolve(data)
            if resolved is not None:
                self.show_command_update(resolved)
            else:
                self.log_message(f"[CMD] Unmatched response: {data}")
            return

        self.last_rx_monotonic = time.monotonic()
        if self.connection_mode == "udp":
            self.command_panel.set_link_state("UDP ACTIVE")

        # TelemetryParser now returns a list of dictionaries
        parsed_list = self.parser.parse(data)

        for parsed in parsed_list:
            if parsed:
                self.dashboard.update_indicators(parsed)

                # 飞行阶段变化回显 (彩色高亮)
                fstate = parsed.get("fstate")
                if fstate and fstate != self.last_fstate:
                    self.last_fstate = fstate
                    self.log_fstate_change(fstate, parsed.get("time", 0))

                if self.start_time is None:
                    self.start_time = time.time()
                elapsed = time.time() - self.start_time

                # 图表 1：高度 + 俯仰（优先使用滤波值）
                alt = parsed.get("alt", 0.0)
                pitch = parsed.get("pitch_flt", parsed.get("pitch", 0.0))
                self.plot_panel.update_plot(elapsed, alt, pitch)

                # 图表 2：滤波对比（如果数据里包含 _raw/_flt 字段）
                if "pitch_raw" in parsed:
                    self.comparison_panel.update_plot(
                        elapsed,
                        parsed.get("pitch_raw", 0.0),
                        parsed.get("pitch_flt", 0.0),
                        parsed.get("roll_raw", 0.0),
                        parsed.get("roll_flt", 0.0)
                    )

                # 3D 姿态更新
                if self.view3d_panel is not None:
                    roll = parsed.get("roll_flt", parsed.get("roll_raw", 0.0))
                    yaw = parsed.get("yaw", 0.0)
                    try:
                        self.view3d_panel.update_attitude(roll, pitch, yaw)
                    except Exception:
                        pass

                # Log structured data as well
                self.data_logger.log(parsed)

        # Always log raw data
        self.data_logger.log(data)

    def on_udp_command_response(self, data, source_addr):
        if (
            not isinstance(self.data_thread, UdpReader)
            or not self.data_thread.is_expected_response_source(source_addr)
        ):
            self.log_message(
                f"[CMD] Spurious UDP response from {source_addr}: {data}"
            )
            return
        self.on_data_received(data)

    def log_fstate_change(self, fstate, mission_time_ms):
        """飞行阶段变化彩色回显"""
        color = FSTATE_COLORS.get(fstate, "#ffffff")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Bold)
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(
            f"\n>>> [PHASE] {fstate}  (t={mission_time_ms/1000.0:.1f}s) <<<\n",
            fmt
        )
        self.log_display.ensureCursorVisible()

    # ---- 指令下发回调 ----
    def on_send_command(self, command_text):
        if self.data_thread and self.data_thread.is_running:
            if self.command_tracker.pending:
                if command_text != "estop":
                    update = self.command_tracker.reject_local(
                        command_text, "previous command awaiting ACK"
                    )
                    self.show_command_update(update)
                    return
                superseded = self.command_tracker.cancel_pending(
                    "superseded by ESTOP"
                )
                if superseded is not None:
                    self.show_command_update(superseded)

            if self.data_thread.send(command_text):
                update = self.command_tracker.mark_sent(command_text)
                self.show_command_update(update)
                self.log_message(f"[CMD >>] {command_text}")
            else:
                self.show_command_update(
                    self.command_tracker.fail(command_text, "transport unavailable")
                )
        else:
            self.log_message("[系统] 未连接，无法发送指令")
            self.show_command_update(
                self.command_tracker.fail(command_text, "link unavailable")
            )

    def show_command_update(self, update):
        self.command_panel.set_command_status(
            update.status, update.command, update.detail
        )
        self.log_message(
            f"[CMD {update.status}] {update.command}"
            + (f" — {update.detail}" if update.detail else "")
        )

    def on_link_state_changed(self, state):
        self.command_panel.set_link_state(state)

    def poll_link_and_command_state(self):
        expired = self.command_tracker.expire()
        if expired is not None:
            self.show_command_update(expired)
        if (
            self.connection_mode == "udp"
            and self.data_thread
            and self.data_thread.is_running
            and self.last_rx_monotonic is not None
            and time.monotonic() - self.last_rx_monotonic > 2.5
        ):
            self.command_panel.set_link_state("TELEMETRY LOST")

    # ---- 错误处理 ----
    def on_error(self, error_msg):
        self.log_message(f"[致命错误] {error_msg}")
        self.disconnect_data()

    def log_message(self, msg):
        self.log_display.append(msg)

    def closeEvent(self, event):
        self.disconnect_data()
        event.accept()
