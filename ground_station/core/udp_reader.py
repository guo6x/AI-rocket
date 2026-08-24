import socket
from PySide6.QtCore import QThread, Signal

class UdpReader(QThread):
    """
    通过 WiFi UDP 接收 ESP8266 透传数据的后台线程。
    与 SerialReader 接口一致（都发射 data_received / error_occurred 信号）。
    """
    data_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, host="0.0.0.0", port=8888, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.is_running = False
        self.sock = None

    def run(self):
        self.is_running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)  # 1秒超时，方便检测 stop 信号

            while self.is_running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    if data:
                        decoded = data.decode('utf-8', errors='replace').strip()
                        if decoded:
                            self.data_received.emit(decoded)
                except socket.timeout:
                    continue  # 超时后重新检查 is_running
                except Exception as e:
                    if self.is_running:
                        self.error_occurred.emit(f"UDP recv error: {e}")
                    break
        except Exception as e:
            self.error_occurred.emit(f"UDP bind error on {self.host}:{self.port}: {e}")
        finally:
            self.is_running = False
            if self.sock:
                self.sock.close()

    def send(self, data, target_addr=None):
        """
        向指定地址发送 UDP 数据（用于反向指令下发）。
        target_addr 格式: ("192.168.x.x", port)
        """
        if self.sock and target_addr:
            try:
                self.sock.sendto(data.encode('utf-8'), target_addr)
            except Exception as e:
                print(f"UDP send error: {e}")

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()
