"""Strict, read-only JSON <-> R3 telemetry conversion for offline use.

This module deliberately sits outside the flight computer, ESP relay and
Ground Station production paths.  It reuses the existing R3 decoder/encoder
and sequence window, but adds an application-payload schema and a stricter
session policy for an offline conversion boundary.

The R3 CRC and session label are not authentication.  No function in this
module returns command data or grants control authority.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math
from typing import Any

from rf_lab.telemetry_frame import (
    FrameError,
    ReceiptStatus,
    TelemetryFrame,
    TelemetrySequenceWindow,
    decode_telemetry,
    encode_telemetry,
)


SCHEMA = "AA-JSON-R3-TELEMETRY"
SCHEMA_VERSION = 1
SOURCE_MODES = {"PHYSICAL", "SIMULATION", "OFFLINE_REPLAY"}

# Compact keys keep the application payload below the existing R3.0 160-byte
# software budget for ordinary flight JSON while the mapping remains explicit
# in the contract document.
INPUT_TO_PAYLOAD = {
    "time": "t",                       # sender/emission millis
    "sample_time_ms": "s",             # sensor acquisition millis
    "sensor_valid": "ok",
    "source_mode": "m",
    "pitch_raw": "p",                  # degrees
    "pitch_flt": "pf",                 # degrees
    "roll_raw": "r",                   # degrees
    "roll_flt": "rf",                  # degrees
    "yaw": "y",                        # gyro yaw rate, degrees/second
    "alt": "h",                        # metres
    "batt": "b",                       # volts; source may be a placeholder
    "auto": "u",
    "control_state": "cs",
    "chute": "c",
    "fstate": "f",
    "sensor_fault": "e",
    "sensor_fault_latched": "l",
    "sensor_io_budget_expired": "q",
    "imu_address": "ia",
    "imu_id": "ii",
    "bmp_address": "ba",
    "bmp_id": "bi",
}
PAYLOAD_TO_INPUT = {value: key for key, value in INPUT_TO_PAYLOAD.items()}
KNOWN_INPUT_FIELDS = set(INPUT_TO_PAYLOAD)
FORBIDDEN_INPUT_FIELDS = {
    "command",
    "command_name",
    "action",
    "servo_pitch",
    "servo_roll",
    "deploy_chute",
    "arm",
    "auto_on",
    "auto_off",
    "estop",
    "reset",
}


class ContractError(ValueError):
    """Stable reason-bearing error for the offline contract boundary."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _finite_number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{field}_must_be_number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(f"{field}_must_be_finite")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(f"{field}_must_be_nonnegative_integer")
    return value


def _flag(value: Any, field: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if type(value) is int and value in (0, 1):
        return value
    raise ContractError(f"{field}_must_be_0_or_1")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 32:
        raise ContractError(f"{field}_must_be_short_text")
    return value


def _validate_input(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ContractError("json_record_must_be_object")
    keys = set(record)
    forbidden = sorted(keys & FORBIDDEN_INPUT_FIELDS)
    if forbidden:
        raise ContractError("control_field_forbidden:" + ",".join(forbidden))
    unknown = sorted(keys - KNOWN_INPUT_FIELDS)
    if unknown:
        raise ContractError("unknown_field:" + unknown[0])
    for required in ("time", "sensor_valid", "source_mode"):
        if required not in record:
            raise ContractError("missing_required_field:" + required)

    result = dict(record)
    result["time"] = _nonnegative_int(record["time"], "time")
    result["sensor_valid"] = _flag(record["sensor_valid"], "sensor_valid")
    result["source_mode"] = _text(record["source_mode"], "source_mode")
    if result["source_mode"] not in SOURCE_MODES:
        raise ContractError("unsupported_source_mode")

    if result["sensor_valid"]:
        required_valid = (
            "sample_time_ms", "pitch_raw", "pitch_flt", "roll_raw",
            "roll_flt", "yaw", "alt",
        )
        for required in required_valid:
            if required not in record:
                raise ContractError("missing_valid_sample_field:" + required)
        result["sample_time_ms"] = _nonnegative_int(
            record["sample_time_ms"], "sample_time_ms"
        )
    elif "sensor_fault" not in record:
        raise ContractError("missing_invalid_sample_fault")
    elif "sample_time_ms" in record and record["sample_time_ms"] is not None:
        result["sample_time_ms"] = _nonnegative_int(
            record["sample_time_ms"], "sample_time_ms"
        )
    if not result["sensor_valid"]:
        for field in ("pitch_raw", "pitch_flt", "roll_raw", "roll_flt", "yaw", "alt"):
            if field in record:
                raise ContractError("invalid_sample_must_omit:" + field)

    numeric_fields = {
        "pitch_raw", "pitch_flt", "roll_raw", "roll_flt", "yaw", "alt", "batt"
    }
    for field in numeric_fields & keys:
        result[field] = _finite_number(record[field], field)
    for field in {"auto", "chute", "sensor_fault_latched", "sensor_io_budget_expired"} & keys:
        result[field] = _flag(record[field], field)
    for field in {"control_state", "fstate", "sensor_fault"} & keys:
        result[field] = _text(record[field], field)
    for field in {"imu_address", "imu_id", "bmp_address", "bmp_id"} & keys:
        value = _nonnegative_int(record[field], field)
        if value > 255:
            raise ContractError(field + "_out_of_range")
        result[field] = value
    return result


def _payload_from_record(record: Mapping[str, Any]) -> bytes:
    normalized = _validate_input(record)
    payload: dict[str, Any] = {"v": SCHEMA_VERSION}
    for field, compact in INPUT_TO_PAYLOAD.items():
        if field in normalized:
            payload[compact] = normalized[field]
    # Canonical JSON is deterministic and deliberately contains no commands.
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("ascii")
    if len(encoded) > 160:
        raise ContractError("application_payload_exceeds_r3_budget")
    return encoded


def encode_json_telemetry(record: Mapping[str, Any], *, session_id: int,
                          sequence: int) -> bytes:
    """Encode one explicitly declared flight JSON sample as an R3 datagram."""
    payload = _payload_from_record(record)
    return encode_telemetry(TelemetryFrame(session_id, sequence, payload))


def _record_from_payload(payload: bytes, *, session_id: int, sequence: int,
                         receive_time_ms: int | None,
                         replay_time_ms: int | None) -> dict[str, Any]:
    try:
        decoded = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("application_payload_not_canonical_json") from exc
    if not isinstance(decoded, dict) or decoded.get("v") != SCHEMA_VERSION:
        raise ContractError("unsupported_application_schema")
    canonical = json.dumps(
        decoded, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    if canonical != payload:
        raise ContractError("application_payload_not_canonical_json")
    unknown = sorted(set(decoded) - {"v"} - set(PAYLOAD_TO_INPUT))
    if unknown:
        raise ContractError("unknown_application_field:" + unknown[0])
    required = {"t", "ok", "m"}
    missing = sorted(required - set(decoded))
    if missing:
        raise ContractError("missing_application_field:" + missing[0])
    source_mode = decoded["m"]
    if not isinstance(source_mode, str) or source_mode not in SOURCE_MODES:
        raise ContractError("unsupported_source_mode")
    sensor_valid = _flag(decoded["ok"], "sensor_valid")
    sample_time: int | None = None
    if "s" in decoded:
        if decoded["s"] is not None:
            sample_time = _nonnegative_int(decoded["s"], "sample_time_ms")
    if sensor_valid:
        for compact in ("s", "p", "pf", "r", "rf", "y", "h"):
            if compact not in decoded:
                raise ContractError("missing_valid_sample_field:" + PAYLOAD_TO_INPUT[compact])
        if sample_time is None:
            raise ContractError("missing_valid_sample_field:sample_time_ms")
    elif "e" not in decoded:
        raise ContractError("missing_invalid_sample_fault")
    for compact in ("p", "pf", "r", "rf", "y", "h"):
        if not sensor_valid and compact in decoded:
            raise ContractError("invalid_sample_must_omit:" + PAYLOAD_TO_INPUT[compact])
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "sequence": sequence,
        "source_mode": source_mode,
        "source_identity": "UNAUTHENTICATED",
        "authentication": "NONE",
        "flight_control_authority": False,
        "timing": {
            "sample_time_ms": sample_time,
            "send_time_ms": _nonnegative_int(decoded["t"], "time"),
            "receive_time_ms": receive_time_ms,
            "replay_time_ms": replay_time_ms,
        },
        "sensor_valid": bool(sensor_valid),
    }
    for compact, field in PAYLOAD_TO_INPUT.items():
        if compact in decoded and field not in {"time", "sample_time_ms", "sensor_valid", "source_mode"}:
            value = decoded[compact]
            if field in {"pitch_raw", "pitch_flt", "roll_raw", "roll_flt", "yaw", "alt", "batt"}:
                value = _finite_number(value, field)
            elif field in {"auto", "chute", "sensor_fault_latched", "sensor_io_budget_expired"}:
                value = _flag(value, field)
            elif field in {"control_state", "fstate", "sensor_fault"}:
                value = _text(value, field)
            elif field in {"imu_address", "imu_id", "bmp_address", "bmp_id"}:
                value = _nonnegative_int(value, field)
                if value > 255:
                    raise ContractError(field + "_out_of_range")
            record[field] = value
    if sensor_valid:
        record["sample_time_ms"] = sample_time
    else:
        record["sample_time_ms"] = sample_time
    record["missing_optional_fields"] = sorted(
        field for field in KNOWN_INPUT_FIELDS
        if field not in {"time", "sample_time_ms", "sensor_valid", "source_mode"}
        and field not in record
    )
    return record


def decode_json_telemetry(datagram: bytes, *, receive_time_ms: int | None = None,
                          replay_time_ms: int | None = None) -> dict[str, Any]:
    """Decode one R3 frame without changing a sequence window."""
    for value, field in ((receive_time_ms, "receive_time_ms"),
                         (replay_time_ms, "replay_time_ms")):
        if value is not None:
            _nonnegative_int(value, field)
    frame = decode_telemetry(datagram)
    return _record_from_payload(
        frame.payload,
        session_id=frame.session_id,
        sequence=frame.sequence,
        receive_time_ms=receive_time_ms,
        replay_time_ms=replay_time_ms,
    )


class OfflineJsonR3Receiver:
    """Strict read-only receiver policy layered over the existing R3 window.

    The first valid frame binds an unauthenticated session label.  A different
    session (including a purported new or old session) is rejected without
    mutating the window.  This is intentionally stricter than the raw R3
    exploratory window, which reports SESSION_CHANGED and resets itself.
    """

    def __init__(self) -> None:
        self.window = TelemetrySequenceWindow()

    def ingest(self, datagram: bytes, *, receive_time_ms: int | None = None,
               replay_time_ms: int | None = None) -> dict[str, Any]:
        try:
            record = decode_json_telemetry(
                datagram,
                receive_time_ms=receive_time_ms,
                replay_time_ms=replay_time_ms,
            )
            frame = decode_telemetry(datagram)
        except (FrameError, TypeError, ContractError) as error:
            reason = error.reason if isinstance(error, (FrameError, ContractError)) else "datagram_must_be_bytes"
            return {
                "status": "REJECT_" + reason,
                "record": None,
                "flight_control_authority": False,
            }

        if self.window.session_id is not None and frame.session_id != self.window.session_id:
            return {
                "status": "REJECT_SESSION_CHANGED_UNTRUSTED",
                "record": None,
                "session_id": frame.session_id,
                "sequence": frame.sequence,
                "flight_control_authority": False,
            }
        receipt = self.window.ingest(frame)
        if receipt.status == ReceiptStatus.ACCEPT:
            record["unobserved_sequence_count"] = receipt.unobserved_sequence_count
            return {
                "status": "ACCEPT_UNAUTHENTICATED",
                "record": record,
                "flight_control_authority": False,
            }
        if receipt.status == ReceiptStatus.DUPLICATE:
            status = "REJECT_DUPLICATE"
        else:
            status = "REJECT_STALE_OR_OUT_OF_ORDER"
        return {
            "status": status,
            "record": None,
            "session_id": frame.session_id,
            "sequence": frame.sequence,
            "flight_control_authority": False,
        }
