import pytest
from core.serial_reader import SerialReader
from core.telemetry_parser import TelemetryParser

def test_basic_parsing():
    parser = TelemetryParser()
    data = '{"time": 100, "alt": 10.5}'
    result = parser.parse(data)
    assert len(result) == 1
    assert result[0]["time"] == 100
    assert result[0]["alt"] == 10.5

def test_multiple_jsons():
    parser = TelemetryParser()
    data = '{"a": 1}{"b": 2}'
    result = parser.parse(data)
    assert len(result) == 2
    assert result[0] == {"a": 1}
    assert result[1] == {"b": 2}

def test_corrupted_data():
    parser = TelemetryParser()
    data = 'junk{"a": 1}morejunk{"b": 2}tail'
    result = parser.parse(data)
    assert len(result) == 2
    assert result[0] == {"a": 1}
    assert result[1] == {"b": 2}

def test_partial_transmission():
    parser = TelemetryParser()
    res1 = parser.parse('{"a":')
    assert len(res1) == 0
    res2 = parser.parse(' 1}')
    assert len(res2) == 1
    assert res2[0] == {"a": 1}

def test_nested_json():
    # Robustness against nested braces if possible, though telemetry is usually flat
    parser = TelemetryParser()
    data = '{"a": {"inner": 1}, "b": 2}'
    result = parser.parse(data)
    assert len(result) == 1
    assert result[0]["a"]["inner"] == 1

def test_empty_and_invalid():
    parser = TelemetryParser()
    assert parser.parse("") == []
    assert parser.parse("invalid") == []
    assert parser.parse("{invalid}") == []


def test_non_object_json_is_ignored_at_telemetry_boundary():
    parser = TelemetryParser()
    assert parser.parse('[1, 2, 3]"text"true') == []


def test_flight_serial_prefix_yields_top_level_telemetry_object():
    parser = TelemetryParser()
    result = parser.parse('[FLIGHT] {"time":1000,"alt":12.3}')
    assert result == [{"time": 1000, "alt": 12.3}]


def test_sensor_log_and_startup_banner_do_not_poison_following_telemetry():
    parser = TelemetryParser()
    assert parser.parse('[SENSOR] imu_identity=MPU6500') == []
    assert parser.parse('--- Ad Astra v5: booting ---') == []
    assert parser.parse('{"time":1001,"alt":12.4}') == [{"time": 1001, "alt": 12.4}]


def test_complete_malformed_serial_line_does_not_poison_next_telemetry():
    parser = TelemetryParser()
    assert parser.parse('{invalid}') == []
    assert parser.parse('{"time":1002,"alt":12.5}') == [{"time": 1002, "alt": 12.5}]


def test_serial_reader_normalizes_only_known_framing_and_preserves_commands():
    assert SerialReader.normalize_line('[FLIGHT] {"time":1003}') == '{"time":1003}'
    assert SerialReader.normalize_line('[SENSOR] imu_identity=MPU6500') is None
    assert SerialReader.normalize_line('--- Ad Astra boot ---') is None
    assert SerialReader.normalize_line('{invalid}') is None
    assert SerialReader.normalize_line('[{"time":1003}]') is None
    assert SerialReader.normalize_line('ACK arm') == 'ACK arm'


def test_top_level_array_objects_are_not_extracted_as_telemetry():
    parser = TelemetryParser()
    assert parser.parse('[{"time": 100, "alt": 10.5}]') == []


def test_split_top_level_array_is_buffered_as_one_non_telemetry_value():
    parser = TelemetryParser()
    assert parser.parse('[{"time":') == []
    assert parser.parse('100}]') == []
    assert parser.buffer == ''


def test_braces_inside_top_level_string_are_not_object_starts():
    parser = TelemetryParser()
    assert parser.parse('"not telemetry {still a string}"') == []
    assert parser.buffer == ''


def test_contiguous_json_objects_still_parse_after_non_object_values():
    parser = TelemetryParser()
    data = '[{"ignored": true}]"{also ignored}"{"a": 1}{"b": 2}'
    assert parser.parse(data) == [{"a": 1}, {"b": 2}]
