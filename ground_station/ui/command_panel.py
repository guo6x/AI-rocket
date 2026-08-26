import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QDoubleSpinBox, QSlider,
                               QGroupBox, QCheckBox, QLineEdit, QMenu,
                               QInputDialog, QFrame, QScrollArea,
                               QMessageBox)
from PySide6.QtGui import QFont, QAction
from PySide6.QtCore import Signal, Qt

# ============================================================
# 可右键编辑的快捷指令按钮
# ============================================================
class QuickButton(QPushButton):
    """右键可编辑标签和指令的快捷按钮"""
    send_command = Signal(str)

    def __init__(self, label, command, parent=None):
        super().__init__(label, parent)
        self.command_str = command
        self.setFont(QFont("Consolas", 9))
        self.setMinimumHeight(30)
        self.clicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self._update_tooltip()

    def _on_click(self):
        self.send_command.emit(self.command_str)

    def _update_tooltip(self):
        self.setToolTip(f"指令: {self.command_str}\n右键编辑")

    def _show_menu(self, pos):
        menu = QMenu(self)
        edit_label = QAction("编辑按钮名称", self)
        edit_cmd = QAction("编辑指令内容", self)
        edit_label.triggered.connect(self._edit_label)
        edit_cmd.triggered.connect(self._edit_command)
        menu.addAction(edit_label)
        menu.addAction(edit_cmd)
        menu.exec(self.mapToGlobal(pos))

    def _edit_label(self):
        text, ok = QInputDialog.getText(self, "编辑按钮", "按钮名称:", text=self.text())
        if ok and text:
            self.setText(text)

    def _edit_command(self):
        text, ok = QInputDialog.getText(self, "编辑指令", "指令字符串:", text=self.command_str)
        if ok and text:
            self.command_str = text
            self._update_tooltip()


# ============================================================
# 主指令面板
# ============================================================
class CommandPanel(QWidget):
    """
    TVC 指令下发面板 V2：
    - 安全锁 + E-STOP + Reset
    - 双轴舵机滑杆
    - PID 调参
    - 通用指令输入框
    - 可右键编辑的快捷指令按钮栏
    """
    send_command = Signal(str)

    DEFAULT_QUICK_BUTTONS = [
        ("🟢 AUTO ON", "auto_on"),
        ("🔴 AUTO OFF", "auto_off"),
        ("🔄 Reset", "reset"),
        ("📐 归中", "set_servo:90,90"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.armed = False
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(5)

        # ===== 安全锁 + 紧急按钮行 =====
        arm_layout = QHBoxLayout()
        self.arm_checkbox = QCheckBox("🔒 Controls Locked")
        self.arm_checkbox.setFont(QFont("Consolas", 9, QFont.Bold))
        self.arm_checkbox.setStyleSheet("color: #4caf50;")
        self.arm_checkbox.toggled.connect(self.on_arm_toggled)
        arm_layout.addWidget(self.arm_checkbox)
        arm_layout.addStretch()

        # ARM 按钮（进入待发射）
        self.arm_btn = QPushButton("🚀 ARM")
        self.arm_btn.setFixedSize(72, 32)
        self.arm_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self.arm_btn.setStyleSheet(
            "background-color: #ff6f00; color: white; border-radius: 4px;"
        )
        self.arm_btn.clicked.connect(self.on_arm_launch)

        # 手动开伞（需要二次确认）
        self.chute_btn = QPushButton("🪂 开伞")
        self.chute_btn.setFixedSize(72, 32)
        self.chute_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self.chute_btn.setStyleSheet(
            "background-color: #1565c0; color: white; border-radius: 4px;"
        )
        self.chute_btn.clicked.connect(self.on_deploy_chute)

        self.estop_btn = QPushButton("🛑 E-STOP")
        self.estop_btn.setFixedSize(80, 32)
        self.estop_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self.estop_btn.setStyleSheet(
            "background-color: #d32f2f; color: white; border-radius: 4px;"
        )
        self.estop_btn.clicked.connect(self.on_estop)

        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setFixedSize(72, 32)
        self.reset_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self.reset_btn.setStyleSheet(
            "background-color: #388e3c; color: white; border-radius: 4px;"
        )
        self.reset_btn.clicked.connect(self.on_reset)

        arm_layout.addWidget(self.arm_btn)
        arm_layout.addWidget(self.chute_btn)
        arm_layout.addWidget(self.reset_btn)
        arm_layout.addWidget(self.estop_btn)
        main_layout.addLayout(arm_layout)

        status_layout = QHBoxLayout()
        self.link_status_label = QLabel("LINK: DISCONNECTED")
        self.command_status_label = QLabel("COMMAND: IDLE")
        self.link_status_label.setFont(QFont("Consolas", 8, QFont.Bold))
        self.command_status_label.setFont(QFont("Consolas", 8, QFont.Bold))
        status_layout.addWidget(self.link_status_label)
        status_layout.addWidget(self.command_status_label)
        main_layout.addLayout(status_layout)

        # ===== 双轴舵机 =====
        servo_group = QGroupBox("舵机 (Pitch / Roll)")
        servo_group.setFont(QFont("Consolas", 9))
        servo_lay = QVBoxLayout(servo_group)
        servo_lay.setSpacing(3)

        self.pitch_slider, self.pitch_label = self._make_servo_row("P:", servo_lay)
        self.roll_slider, self.roll_label = self._make_servo_row("R:", servo_lay)

        self.servo_send_btn = QPushButton("📤 发送舵机")
        self.servo_send_btn.setEnabled(False)
        self.servo_send_btn.clicked.connect(self.on_send_servo)
        servo_lay.addWidget(self.servo_send_btn)
        main_layout.addWidget(servo_group)

        # ===== PID =====
        pid_group = QGroupBox("PID 调参")
        pid_group.setFont(QFont("Consolas", 9))
        pid_lay = QHBoxLayout(pid_group)
        self.kp_spin = self._make_spin("Kp", 1.0, pid_lay)
        self.ki_spin = self._make_spin("Ki", 0.01, pid_lay)
        self.kd_spin = self._make_spin("Kd", 0.5, pid_lay)
        self.pid_send_btn = QPushButton("📤")
        self.pid_send_btn.setEnabled(False)
        self.pid_send_btn.clicked.connect(self.on_send_pid)
        pid_lay.addWidget(self.pid_send_btn)
        main_layout.addWidget(pid_group)

        # ===== 快捷按钮栏 =====
        quick_group = QGroupBox("快捷指令 (右键编辑)")
        quick_group.setFont(QFont("Consolas", 9))
        self.quick_layout = QHBoxLayout(quick_group)
        self.quick_layout.setSpacing(4)
        self.quick_buttons = []
        for label, cmd in self.DEFAULT_QUICK_BUTTONS:
            btn = QuickButton(label, cmd)
            btn.send_command.connect(self.send_command.emit)
            self.quick_layout.addWidget(btn)
            self.quick_buttons.append(btn)
        main_layout.addWidget(quick_group)

        # ===== 通用指令输入框 =====
        cmd_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入任意指令，如 set_servo:90,90")
        self.cmd_input.setFont(QFont("Consolas", 10))
        self.cmd_input.returnPressed.connect(self.on_send_raw)
        self.cmd_send_btn = QPushButton("📤 发送")
        self.cmd_send_btn.setFont(QFont("Consolas", 10))
        self.cmd_send_btn.clicked.connect(self.on_send_raw)
        cmd_layout.addWidget(self.cmd_input, stretch=1)
        cmd_layout.addWidget(self.cmd_send_btn)
        main_layout.addLayout(cmd_layout)

    # ---- 工厂方法 ----
    def _make_servo_row(self, label, parent_layout):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 180)
        slider.setValue(90)
        slider.setEnabled(False)
        val_label = QLabel("90°")
        val_label.setFont(QFont("Consolas", 11, QFont.Bold))
        val_label.setMinimumWidth(40)
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}°"))
        slider.sliderReleased.connect(self.on_send_servo)
        row.addWidget(slider, stretch=1)
        row.addWidget(val_label)
        parent_layout.addLayout(row)
        return slider, val_label

    def _make_spin(self, label, default, layout):
        lbl = QLabel(label + ":")
        lbl.setFont(QFont("Consolas", 9))
        spin = QDoubleSpinBox()
        spin.setRange(-100.0, 100.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.01)
        spin.setValue(default)
        spin.setEnabled(False)
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return spin

    # ---- 逻辑回调 ----
    def on_arm_toggled(self, checked):
        self.armed = checked
        for w in [self.pitch_slider, self.roll_slider, self.servo_send_btn,
                  self.kp_spin, self.ki_spin, self.kd_spin, self.pid_send_btn]:
            w.setEnabled(checked)
        if checked:
            self.arm_checkbox.setText("🔓 Controls Unlocked")
            self.arm_checkbox.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.arm_checkbox.setText("🔒 Controls Locked")
            self.arm_checkbox.setStyleSheet("color: #4caf50;")

    def on_send_servo(self):
        if not self.armed:
            return
        cmd = f"set_servo:{self.pitch_slider.value()},{self.roll_slider.value()}"
        self.send_command.emit(cmd)

    def on_send_pid(self):
        if not self.armed:
            return
        cmd = f"set_pid:{round(self.kp_spin.value(),3)},{round(self.ki_spin.value(),3)},{round(self.kd_spin.value(),3)}"
        self.send_command.emit(cmd)

    def on_arm_launch(self):
        self.send_command.emit("arm")

    def on_deploy_chute(self):
        # 二次确认对话框，防止误操作
        reply = QMessageBox.warning(
            self, "⚠️ 手动开伞确认",
            "确定要立即弹射降落伞吗？\n\n"
            "此操作不可撤销，仅在紧急情况下使用。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.send_command.emit("deploy_chute")

    def on_estop(self):
        self.send_command.emit("estop")
        self.arm_checkbox.setChecked(False)

    def on_reset(self):
        self.send_command.emit("reset")

    def on_send_raw(self):
        text = self.cmd_input.text().strip()
        if text:
            self.send_command.emit(text)
            self.cmd_input.clear()

    def set_link_state(self, state):
        self.link_status_label.setText(f"LINK: {state}")

    def set_command_status(self, status, command="", detail=""):
        text = f"COMMAND: {status}"
        if command:
            text += f" {command}"
        if detail:
            text += f" ({detail})"
        self.command_status_label.setText(text)
