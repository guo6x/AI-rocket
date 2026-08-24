import sys
import os
import json
import time

# 把当前脚本所在目录加到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.telemetry_parser import TelemetryParser

def test_telemetry_parser():
    parser = TelemetryParser()
    
    # 正常数据
    valid_json = '{"time":1234,"pitch":1.2,"roll":-0.5,"yaw":90.0,"alt":10.5,"batt":7.4}'
    print(f"Testing valid: {valid_json}")
    result = parser.parse(valid_json)
    assert len(result) > 0
    assert result[0]["pitch"] == 1.2
    
    # 带有串口脏数据前缀和后缀
    dirty_json = '\r\n\x00x {"time":5678,"pitch":8.8,"alt":100.1} \r\n'
    print(f"Testing dirty: {repr(dirty_json)}")
    result = parser.parse(dirty_json)
    assert len(result) > 0
    assert result[0]["alt"] == 100.1
    
    # 无效数据
    invalid_data = "Hello World"
    print(f"Testing invalid: {invalid_data}")
    result = parser.parse(invalid_data)
    assert result == []
    
    print("All tests passed!")

if __name__ == "__main__":
    test_telemetry_parser()
