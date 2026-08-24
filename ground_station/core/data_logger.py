import os
import time
from datetime import datetime

class DataLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.current_log_file = None
        self.file_handle = None
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)

    def start_logging(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join(self.log_dir, f"telemetry_{timestamp}.csv")
        self.file_handle = open(self.current_log_file, "a", encoding="utf-8")
        # Optional: Write CSV header if we decide on a fixed format
        # self.file_handle.write("timestamp,source_type,data...\n")

    def log(self, data):
        """
        Logs data to the current log file.
        Handles both raw strings and dictionaries.
        Robust against missing fields in dictionaries.
        """
        if not self.file_handle or self.file_handle.closed:
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            if isinstance(data, dict):
                # If data is a dictionary, log it as a comma-separated line
                # We prioritize some common fields but allow any data
                # We can also just log the JSON representation for maximum info
                import json
                json_data = json.dumps(data)
                self.file_handle.write(f"{timestamp},DICT,{json_data}\n")
            else:
                # Fallback for strings or other types
                self.file_handle.write(f"{timestamp},RAW,{data}\n")
                
            self.file_handle.flush()
        except Exception as e:
            # Graceful failure: don't crash the ground station if logging fails
            print(f"Logging error: {e}")

    def stop_logging(self):
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
        self.file_handle = None
