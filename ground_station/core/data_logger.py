import os
import csv
from datetime import datetime

class DataLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.current_log_file = None
        self.file_handle = None

        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)

    def start_logging(self):
        self.stop_logging()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.current_log_file = os.path.join(self.log_dir, f"telemetry_{timestamp}.csv")
        self.file_handle = open(self.current_log_file, "x", encoding="utf-8", newline="")
        # Preserve the three-field, headerless session format. newline=""
        # prevents platform newline translation from changing CSV records.

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
                # CSV quoting keeps the complete JSON payload in one field.
                import json
                json_data = json.dumps(data)
                csv.writer(self.file_handle, lineterminator="\r\n").writerow((timestamp, "DICT", json_data))
            else:
                # Fallback for strings or other types
                csv.writer(self.file_handle, lineterminator="\r\n").writerow((timestamp, "RAW", str(data)))

            self.file_handle.flush()
        except Exception as e:
            # Graceful failure: don't crash the ground station if logging fails
            print(f"Logging error: {e}")

    def stop_logging(self):
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
        self.file_handle = None

