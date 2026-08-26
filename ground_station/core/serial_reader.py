import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal

class SerialReader(QThread):
    data_received = Signal(str)
    error_occurred = Signal(str)
    link_state_changed = Signal(str)

    def __init__(self, port, baudrate=115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.is_running = False
        self.serial_port = None

    def run(self):
        self.is_running = True
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1)
            self.link_state_changed.emit("SERIAL CONNECTED")
            while self.is_running:
                # 阻塞读取直到超时或收到换行符
                line = self.serial_port.readline()
                if line:
                    try:
                        decoded_line = line.decode('utf-8', errors='replace').strip()
                        if decoded_line:
                            self.data_received.emit(decoded_line)
                    except Exception as e:
                        print(f"Decode error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Serial Connect/Read error: {e}")
        finally:
            self.is_running = False
            self.link_state_changed.emit("DISCONNECTED")
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()

    def send(self, data):
        """向串口写入数据（用于指令下发）"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((data + '\n').encode('utf-8'))
                return True
            except Exception as e:
                self.error_occurred.emit(f"Serial send error: {e}")
        return False

def get_available_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]
