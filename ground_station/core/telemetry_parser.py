import json

class TelemetryParser:
    """
    Highly robust parser for telemetry data.
    Can extract multiple JSON objects from a messy or fragmented string buffer.
    """
    MAX_BUFFER_CHARS = 16384

    def __init__(self):
        self.buffer = ""
        self.overlong_buffers_rejected = 0

    def parse(self, raw_string):
        """
        Extracts valid JSON objects from raw_string.
        Handles partial transmissions by using a persistent buffer.
        Returns a list of parsed dictionaries.
        """
        if not raw_string:
            return []

        self.buffer += raw_string
        if len(self.buffer) > self.MAX_BUFFER_CHARS:
            # Production JSON is a few hundred characters. Never retain an
            # unbounded incomplete object across a long receive session.
            self.buffer = ""
            self.overlong_buffers_rejected += 1
            return []
        parsed_objects = []

        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(self.buffer):
            char = self.buffer[pos]
            if char.isspace():
                pos += 1
                continue

            # Decode complete top-level JSON values, rather than searching for
            # every '{'.  Searching inside an array or quoted string would
            # incorrectly promote nested objects to telemetry frames.
            if char not in '{["-0123456789tfn':
                pos += 1
                continue

            try:
                obj, end_idx = decoder.raw_decode(self.buffer, pos)
            except (json.JSONDecodeError, ValueError, RecursionError):
                # A structural value that cannot be decoded may simply be a
                # fragmented value.  Preserve it from its true top-level
                # boundary and wait for the next receive chunk.  In
                # particular, do not scan into an incomplete array/string.
                if char in '{["':
                    self.buffer = self.buffer[pos:]
                    return parsed_objects
                pos += 1
                continue

            if isinstance(obj, dict):
                parsed_objects.append(obj)
            pos = end_idx

        # If we finished the loop successfully
        if pos >= len(self.buffer):
            self.buffer = ""
        else:
            self.buffer = self.buffer[pos:]

        return parsed_objects
