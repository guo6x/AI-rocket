import socket
import ipaddress
from PySide6.QtCore import QThread, Signal
from core.command_link import parse_command_response

class UdpReader(QThread):
    """
    通过 WiFi UDP 接收 ESP8266 透传数据的后台线程。
    与 SerialReader 接口一致（都发射 data_received / error_occurred 信号）。
    """
    data_received = Signal(str)
    command_response_received = Signal(str, object)
    error_occurred = Signal(str)
    link_state_changed = Signal(str)

    def __init__(self, host="0.0.0.0", port=8888, target_addr=None, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.target_addr = target_addr
        self.is_running = False
        self.sock = None

    def run(self):
        self.is_running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)  # 1秒超时，方便检测 stop 信号
            self.link_state_changed.emit("UDP LISTENING")

            while self.is_running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    if data:
                        decoded = data.decode('utf-8', errors='replace').strip()
                        if parse_command_response(decoded) is not None:
                            self.command_response_received.emit(decoded, addr)
                        elif decoded:
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
            self.link_state_changed.emit("DISCONNECTED")
            if self.sock:
                self.sock.close()

    @staticmethod
    def validate_target(target_addr):
        if not isinstance(target_addr, tuple) or len(target_addr) != 2:
            return False
        host, port = target_addr
        try:
            address = ipaddress.ip_address(host)
            port = int(port)
        except (ValueError, TypeError):
            return False
        return (
            address.version == 4
            and not address.is_unspecified
            and not address.is_multicast
            and str(address) != "255.255.255.255"
            and 1 <= port <= 65535
        )

    def is_expected_response_source(self, source_addr):
        if not self.validate_target(self.target_addr):
            return False
        if not isinstance(source_addr, tuple) or len(source_addr) < 2:
            return False
        try:
            source_ip = ipaddress.ip_address(source_addr[0])
            target_ip = ipaddress.ip_address(self.target_addr[0])
            source_port = int(source_addr[1])
            target_port = int(self.target_addr[1])
        except (ValueError, TypeError):
            return False
        return source_ip == target_ip and source_port == target_port

    def send(self, data):
        """
        向指定地址发送 UDP 数据（用于反向指令下发）。
        The constructor target is explicit unicast IPv4: ("192.168.x.x", port).
        """
        command = data.strip()
        if (not self.sock or not self.validate_target(self.target_addr)
                or not command or len(command.encode("utf-8")) > 128
                or "\n" in command or "\r" in command):
            return False
        try:
            self.sock.sendto(command.encode('utf-8'), self.target_addr)
            return True
        except Exception as e:
            self.error_occurred.emit(f"UDP send error: {e}")
            return False

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()
