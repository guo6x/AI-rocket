import pytest
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
