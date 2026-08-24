import json

class TelemetryParser:
    """
    Highly robust parser for telemetry data.
    Can extract multiple JSON objects from a messy or fragmented string buffer.
    """
    def __init__(self):
        self.buffer = ""

    def parse(self, raw_string):
        """
        Extracts valid JSON objects from raw_string.
        Handles partial transmissions by using a persistent buffer.
        Returns a list of parsed dictionaries.
        """
        if not raw_string:
            return []
            
        self.buffer += raw_string
        parsed_objects = []
        
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(self.buffer):
            # Find the first occurrence of '{'
            start_idx = self.buffer.find('{', pos)
            if start_idx == -1:
                # No more possible JSON objects, clear junk from buffer
                self.buffer = ""
                break
            
            # Move pos to start_idx for potential re-parsing or skipping
            pos = start_idx
            
            try:
                # Try to decode from this position
                # raw_decode reads one JSON object and returns it + end position
                obj, end_idx_relative = decoder.raw_decode(self.buffer[start_idx:])
                parsed_objects.append(obj)
                # end_idx_relative is relative to buffer[start_idx:]
                pos = start_idx + end_idx_relative
                # Continue searching after this object
            except json.JSONDecodeError:
                # Not a valid JSON starting at this '{'
                # Check if there's another '{' further down
                next_start = self.buffer.find('{', start_idx + 1)
                if next_start != -1:
                    # Yes, there is another brace, so the current start_idx was junk
                    pos = next_start
                else:
                    # No more braces. The current buffer from start_idx might be a partial JSON.
                    # Keep it in buffer and wait for more data.
                    self.buffer = self.buffer[start_idx:]
                    return parsed_objects
        
        # If we finished the loop successfully
        if pos >= len(self.buffer):
            self.buffer = ""
        else:
            self.buffer = self.buffer[pos:]
            
        return parsed_objects
