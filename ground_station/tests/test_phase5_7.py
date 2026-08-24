import sys
import os
import socket
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.udp_reader import UdpReader
from core.telemetry_parser import TelemetryParser

def test_udp_reader():
    """模拟 ESP8266 向 UdpReader 发送 JSON 数据"""
    received = []
    
    reader = UdpReader(port=19999)
    reader.data_received.connect(lambda d: received.append(d))
    reader.start()
    
    time.sleep(0.5)  # 等待 reader 绑定端口
    
    # 模拟 ESP8266 发包
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_data = '{"time":5000,"pitch":12.5,"roll":-3.2,"yaw":45.0,"alt":200.0,"batt":7.2}'
    sock.sendto(test_data.encode('utf-8'), ("127.0.0.1", 19999))
    
    time.sleep(1.5)  # 等待接收
    
    reader.stop()
    sock.close()
    
    assert len(received) == 1, f"Expected 1 message, got {len(received)}"
    
    parser = TelemetryParser()
    result = parser.parse(received[0])
    assert len(result) > 0
    parsed = result[0]
    assert parsed["alt"] == 200.0
    assert parsed["pitch"] == 12.5
    
    print("UDP Reader test passed!")

def test_telemetry_parser_filtered():
    """测试包含 _raw/_flt 字段的数据"""
    parser = TelemetryParser()
    data = '{"pitch_raw":5.2,"pitch_flt":5.0,"roll_raw":-1.0,"roll_flt":-0.8,"alt":50.0}'
    result = parser.parse(data)
    assert len(result) > 0
    parsed = result[0]
    assert parsed["pitch_raw"] == 5.2
    assert parsed["pitch_flt"] == 5.0
    assert parsed["roll_flt"] == -0.8
    print("Filtered telemetry parser test passed!")

if __name__ == "__main__":
    # 需要 QApplication 来支持 QThread
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    test_telemetry_parser_filtered()
    test_udp_reader()
    
    print("\nAll Phase 5-7 tests passed!")
