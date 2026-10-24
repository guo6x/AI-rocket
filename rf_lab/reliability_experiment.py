"""Deterministic, read-only synthetic telemetry reliability experiment.

This module exercises only the R3.0 telemetry codec and freshness window.
It has no radio, socket, UART, command, actuator, or flight-control interface.
All drop/delay/corruption events are synthetic software fixtures. Receiver
sequence gaps are reported separately as unobserved sequence numbers; neither
metric describes a real RF link.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import platform
import random
import shutil
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

from rf_lab.telemetry_frame import (
    HEADER,
    FrameError,
    ReceiptStatus,
    TelemetryFrame,
    TelemetrySequenceWindow,
    decode_telemetry,
    encode_telemetry,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_SEED = 0x5231
SEEDED_FRAME_COUNT = 512
MAX_FRAMES_PER_SCENARIO = 512
MAX_DELIVERIES_PER_SCENARIO = 1024
MAX_HOST_RUNTIME_SECONDS = 10.0
MAX_TRACEMALLOC_PEAK_BYTES = 8 * 1024 * 1024
DELAY_SLOTS = 2  # abstract generator slots only; not elapsed time
SOURCE_PATHS = (
    "engineering/rf-reliability-contract.yaml",
    "docs/R3_RF_OFFLINE_PROTOCOL.md",
    "docs/R3_1_RF_RELIABILITY_EXPERIMENT.md",
    "rf_lab/telemetry_frame.py",
    "rf_lab/offline_link_replay.py",
    "rf_lab/reliability_experiment.py",
    "rf_lab/tests/test_telemetry_frame.py",
    "rf_lab/tests/test_offline_link_replay.py",
    "rf_lab/tests/test_reliability_experiment.py",
    "scripts/check.py",
)

STATUS_KEYS = (
    ReceiptStatus.ACCEPT.value,
    ReceiptStatus.DUPLICATE.value,
    ReceiptStatus.STALE_OR_OUT_OF_ORDER.value,
    ReceiptStatus.SESSION_CHANGED.value,
)


@dataclass(frozen=True)
class GeneratedFrame:
    ordinal: int
    session_id: int
    sequence: int
    datagram: bytes


@dataclass(frozen=True)
class Delivery:
    source_ordinal: int
    generator_label: str
    datagram: bytes
    release_slot: int


@dataclass(frozen=True)
class Scenario:
    name: str
    generated: tuple[GeneratedFrame, ...]
    known_drops: tuple[GeneratedFrame, ...]
    deliveries: tuple[Delivery, ...]
    injected_fault_counts: dict[str, int]
    maximum_pending_delays: int = 0


def _encode(session_id: int, sequence: int) -> bytes:
    payload = f"synthetic-telemetry:{session_id}:{sequence}".encode("ascii")
    return encode_telemetry(TelemetryFrame(session_id, sequence, payload))


def _generated(session_id: int, sequences: list[int]) -> tuple[GeneratedFrame, ...]:
    return tuple(
        GeneratedFrame(i, session_id, sequence, _encode(session_id, sequence))
        for i, sequence in enumerate(sequences)
    )


def _delivery(frame: GeneratedFrame, label: str = "normal", *, release_slot: int | None = None,
              datagram: bytes | None = None) -> Delivery:
    return Delivery(
        frame.ordinal,
        label,
        frame.datagram if datagram is None else datagram,
        frame.ordinal if release_slot is None else release_slot,
    )


def _scenario_inputs() -> tuple[Scenario, ...]:
    scenarios: list[Scenario] = []

    frames = _generated(10, list(range(8)))
    scenarios.append(Scenario(
        "normal_ordered", frames, (), tuple(_delivery(frame) for frame in frames), {},
    ))

    frames = _generated(11, list(range(16)))
    independent_drop_sequences = {2, 7, 13}
    dropped = tuple(frame for frame in frames if frame.sequence in independent_drop_sequences)
    scenarios.append(Scenario(
        "independent_synthetic_drops", frames, dropped,
        tuple(_delivery(frame) for frame in frames if frame not in dropped),
        {"independent_drop": len(dropped)},
    ))

    frames = _generated(12, list(range(20)))
    burst_drop_sequences = {5, 6, 7, 8}
    dropped = tuple(frame for frame in frames if frame.sequence in burst_drop_sequences)
    scenarios.append(Scenario(
        "contiguous_synthetic_burst", frames, dropped,
        tuple(_delivery(frame) for frame in frames if frame not in dropped),
        {"contiguous_drop": len(dropped)},
    ))

    frames = _generated(13, list(range(8)))
    duplicate_events: list[Delivery] = []
    for frame in frames:
        duplicate_events.append(_delivery(frame))
        if frame.sequence == 3:
            duplicate_events.append(_delivery(frame, "duplicate_copy"))
    scenarios.append(Scenario(
        "duplicate_delivery", frames, (), tuple(duplicate_events), {"duplicate": 1},
    ))

    frames = _generated(14, list(range(8)))
    delayed_order = (0, 1, 4, 5, 2, 3, 6, 7)
    release_slots = {0: 0, 1: 1, 4: 4, 5: 5, 2: 6, 3: 6, 6: 6, 7: 7}
    delayed = {2, 3}
    # Delivery list order is the stable tie-break for equal abstract slots.
    # Every packet is released no earlier than its generation ordinal; seq 2/3
    # are explicitly delayed until after seq 4/5 have arrived.
    scenarios.append(Scenario(
        "delayed_out_of_order", frames, (),
        tuple(_delivery(
            frames[index],
            "delayed_delivery" if index in delayed else "normal",
            release_slot=release_slots[index],
        ) for index in delayed_order),
        {"delayed": len(delayed)},
        maximum_pending_delays=len(delayed),
    ))

    frames = _generated(15, list(range(6)))
    damaged = bytearray(frames[2].datagram)
    damaged[HEADER.size] ^= 0x80
    scenarios.append(Scenario(
        "crc_corruption", frames, (), tuple(
            _delivery(frame, "crc_corrupted", datagram=bytes(damaged))
            if frame.sequence == 2 else _delivery(frame)
            for frame in frames
        ), {"crc_corruption": 1},
    ))

    frames = _generated(16, [0, 1])
    truncated_header = frames[1].datagram[:6]
    truncated_payload = frames[1].datagram[:-1]
    malformed_length = bytearray(frames[1].datagram)
    malformed_length[HEADER.size - 2:HEADER.size] = b"\x00\x00"
    scenarios.append(Scenario(
        "truncation_and_length_anomalies", frames, (), (
            _delivery(frames[0]),
            _delivery(frames[1], "truncated_header", datagram=truncated_header),
            _delivery(frames[1], "truncated_payload", datagram=truncated_payload),
            _delivery(frames[1], "invalid_declared_length", datagram=bytes(malformed_length)),
            _delivery(frames[1]),
        ),
        {"truncated_header": 1, "truncated_payload": 1, "invalid_length": 1},
    ))

    boundary_sequences = [0, 32767, 65535, 65534, 65535, 0, 32768]
    frames = _generated(17, boundary_sequences)
    scenarios.append(Scenario(
        "uint16_large_gap_half_range_and_wrap", frames, (),
        tuple(_delivery(frame) for frame in frames), {},
    ))

    frames = (
        GeneratedFrame(0, 18, 100, _encode(18, 100)),
        GeneratedFrame(1, 18, 99, _encode(18, 99)),
        GeneratedFrame(2, 0xBAD01234, 1, _encode(0xBAD01234, 1)),
        GeneratedFrame(3, 18, 101, _encode(18, 101)),
    )
    scenarios.append(Scenario(
        "untrusted_session_churn", frames, (), (
            _delivery(frames[0]),
            _delivery(frames[0], "duplicate_copy"),
            _delivery(frames[1], "old_same_session_frame"),
            _delivery(frames[2], "spoofable_session_label"),
            _delivery(frames[3], "previous_session_label_reentry"),
        ),
        {"duplicate": 1, "old_frame_replay": 1, "session_label_changes_untrusted": 2},
    ))

    scenarios.append(_seeded_bounded_scenario())
    return tuple(scenarios)


def _seeded_bounded_scenario() -> Scenario:
    count = SEEDED_FRAME_COUNT
    frames = _generated(19, [(3000 + i) & 0xFFFF for i in range(count)])
    categories = (
        ["normal"] * 352
        + ["drop"] * 32
        + ["duplicate"] * 32
        + ["crc_corruption"] * 32
        + ["truncation"] * 32
        + ["delay"] * 32
    )
    rng = random.Random(SCENARIO_SEED)
    rng.shuffle(categories)

    drops: list[GeneratedFrame] = []
    scheduled: list[tuple[int, int, int, Delivery]] = []
    delays_by_slot: Counter[int] = Counter()
    faults: Counter[str] = Counter()
    for frame, action in zip(frames, categories, strict=True):
        faults[action] += 1
        if action == "drop":
            drops.append(frame)
            continue
        if action == "crc_corruption":
            altered = bytearray(frame.datagram)
            altered[HEADER.size] ^= 0x01
            scheduled.append((frame.ordinal, frame.ordinal, 0,
                              _delivery(frame, action, datagram=bytes(altered))))
        elif action == "truncation":
            scheduled.append((frame.ordinal, frame.ordinal, 0,
                              _delivery(frame, action, datagram=frame.datagram[:6])))
        elif action == "delay":
            release = frame.ordinal + DELAY_SLOTS
            delays_by_slot[frame.ordinal] += 1
            scheduled.append((release, frame.ordinal, 0,
                              _delivery(frame, action, release_slot=release)))
        elif action == "duplicate":
            scheduled.append((frame.ordinal, frame.ordinal, 0, _delivery(frame)))
            scheduled.append((frame.ordinal, frame.ordinal, 1,
                              _delivery(frame, "duplicate_copy")))
        else:
            scheduled.append((frame.ordinal, frame.ordinal, 0, _delivery(frame)))

    scheduled.sort(key=lambda item: (item[0], item[1], item[2]))
    peak_pending = 0
    pending = 0
    for slot in range(count + DELAY_SLOTS + 1):
        # Define same-slot ordering explicitly: newly generated delays enter
        # before deliveries released in this slot leave the pending queue.
        pending += delays_by_slot[slot]
        peak_pending = max(peak_pending, pending)
        pending -= sum(
            1 for release, source_index, _, _ in scheduled
            if release == slot and categories[source_index] == "delay"
        )
        if pending < 0:
            raise AssertionError("delay queue released more frames than were pending")

    return Scenario(
        "seeded_bounded_fault_mix", frames, tuple(drops),
        tuple(item[3] for item in scheduled), dict(sorted(faults.items())), peak_pending,
    )


class ReadOnlyTelemetryReceiver:
    """Synthetic receiver with no command or actuator dispatch method."""

    def __init__(self) -> None:
        self.window = TelemetrySequenceWindow()
        self.status_counts: Counter[str] = Counter()
        self.rejected_by_reason: Counter[str] = Counter()
        self.unobserved_gap_total = 0
        self.maximum_unobserved_gap = 0
        self.untrusted_session_changes: list[dict[str, int | None]] = []
        self.invalid_window_mutations = 0
        self.replay_window_mutations = 0

    def _window_state(self) -> tuple[int | None, int | None]:
        return self.window.session_id, self.window.last_sequence

    def offer(self, datagram: bytes) -> dict[str, Any]:
        before = self._window_state()
        try:
            frame = decode_telemetry(datagram)
        except (FrameError, TypeError) as exc:
            reason = exc.reason if isinstance(exc, FrameError) else "datagram_must_be_bytes"
            self.rejected_by_reason[reason] += 1
            unchanged = self._window_state() == before
            if not unchanged:
                self.invalid_window_mutations += 1
            return {
                "status": "REJECT_" + reason,
                "reason": reason,
                "session_id": None,
                "sequence": None,
                "unobserved_sequence_gap_count": 0,
                "window_unchanged": unchanged,
                "flight_control_authority_granted": False,
            }

        receipt = self.window.ingest(frame)
        status = receipt.status.value
        self.status_counts[status] += 1
        self.unobserved_gap_total += receipt.unobserved_sequence_count
        self.maximum_unobserved_gap = max(
            self.maximum_unobserved_gap, receipt.unobserved_sequence_count
        )
        unchanged = self._window_state() == before
        if status in (ReceiptStatus.DUPLICATE.value, ReceiptStatus.STALE_OR_OUT_OF_ORDER.value):
            if not unchanged:
                self.replay_window_mutations += 1
        if status == ReceiptStatus.SESSION_CHANGED.value:
            self.untrusted_session_changes.append({
                "previous_session_label": before[0],
                "new_session_label": frame.session_id,
            })
        return {
            "status": status,
            "reason": None,
            "session_id": frame.session_id,
            "sequence": frame.sequence,
            "unobserved_sequence_gap_count": receipt.unobserved_sequence_count,
            "window_unchanged": unchanged,
            "flight_control_authority_granted": False,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "status_counts": {key: self.status_counts[key] for key in STATUS_KEYS},
            "rejected_by_reason": dict(sorted(self.rejected_by_reason.items())),
            "unobserved_forward_sequence_gap_count": self.unobserved_gap_total,
            "maximum_unobserved_forward_gap_in_one_accept": self.maximum_unobserved_gap,
            "session_changes_observed_untrusted": self.untrusted_session_changes,
            "session_identity_authenticated": False,
            "invalid_datagram_window_mutations": self.invalid_window_mutations,
            "duplicate_or_stale_window_mutations": self.replay_window_mutations,
            "flight_command_dispatches": 0,
            "flight_control_authority_grants": 0,
            "control_or_actuator_channel_connected": False,
        }


def _run_scenario(scenario: Scenario) -> dict[str, Any]:
    if len(scenario.generated) > MAX_FRAMES_PER_SCENARIO:
        raise ValueError("scenario exceeds fixed generated-frame bound")
    if len(scenario.deliveries) > MAX_DELIVERIES_PER_SCENARIO:
        raise ValueError("scenario exceeds fixed delivery bound")

    receiver = ReadOnlyTelemetryReceiver()
    observations: list[dict[str, Any]] = []
    for delivery_index, delivery in enumerate(scenario.deliveries):
        outcome = receiver.offer(delivery.datagram)
        observations.append({
            "delivery_index": delivery_index,
            "source_generation_ordinal": delivery.source_ordinal,
            "generator_label": delivery.generator_label,
            "release_slot": delivery.release_slot,
            **outcome,
        })

    receiver_metrics = receiver.summary()
    if receiver_metrics["invalid_datagram_window_mutations"] != 0:
        raise AssertionError(f"invalid datagram changed window in {scenario.name}")
    if receiver_metrics["duplicate_or_stale_window_mutations"] != 0:
        raise AssertionError(f"duplicate/stale input changed window in {scenario.name}")
    if receiver_metrics["flight_control_authority_grants"] != 0:
        raise AssertionError("read-only receiver granted flight-control authority")
    if receiver_metrics["flight_command_dispatches"] != 0:
        raise AssertionError("read-only receiver dispatched a flight command")

    return {
        "scenario": scenario.name,
        "generator": {
            "unique_frames_generated": len(scenario.generated),
            "known_synthetic_drop_count": len(scenario.known_drops),
            "known_synthetic_drop_events": [
                {"generation_ordinal": frame.ordinal,
                 "session_label": frame.session_id,
                 "sequence": frame.sequence}
                for frame in scenario.known_drops
            ],
            "synthetic_fault_injection_counts": dict(sorted(scenario.injected_fault_counts.items())),
            "datagrams_offered_to_receiver": len(scenario.deliveries),
            "maximum_pending_synthetic_delayed_datagrams": scenario.maximum_pending_delays,
        },
        "receiver": receiver_metrics,
        "permission_boundary": {
            "payload_interpreted_as_command": False,
            "flight_command_channel_connected": False,
            "actuator_channel_connected": False,
            "authority_grants": 0,
        },
        "observations": observations,
    }


def run_deterministic_experiment() -> dict[str, Any]:
    scenarios = [_run_scenario(scenario) for scenario in _scenario_inputs()]
    total_generated = sum(row["generator"]["unique_frames_generated"] for row in scenarios)
    total_known_drops = sum(row["generator"]["known_synthetic_drop_count"] for row in scenarios)
    total_offered = sum(row["generator"]["datagrams_offered_to_receiver"] for row in scenarios)
    total_gaps = sum(row["receiver"]["unobserved_forward_sequence_gap_count"] for row in scenarios)
    all_statuses: Counter[str] = Counter()
    all_rejections: Counter[str] = Counter()
    for row in scenarios:
        all_statuses.update(row["receiver"]["status_counts"])
        all_rejections.update(row["receiver"]["rejected_by_reason"])
    return {
        "schema_version": 1,
        "experiment": "r3_1_read_only_telemetry_reliability_v1",
        "contract_id": "AA-RF-OFFLINE-RELIABILITY-001",
        "evidence_ceiling": "TESTED_SOFTWARE",
        "synthetic_only": True,
        "real_radio_metrics": "NOT_MEASURED",
        "session_identity": "UNAUTHENTICATED_LABEL",
        "crc_authentication": False,
        "fault_metric_definitions": {
            "known_synthetic_drop_count": "Generated frames intentionally withheld by this software fixture.",
            "unobserved_forward_sequence_gap_count": "Sequence numbers skipped by the receiver freshness window; not measured RF loss.",
            "datagrams_offered_to_receiver": "Synthetic datagram deliveries, including duplicates and invalid bytes.",
            "time_units": "No physical time units; delay uses abstract generator slots only.",
        },
        "summary": {
            "scenario_count": len(scenarios),
            "unique_frames_generated": total_generated,
            "known_synthetic_drops": total_known_drops,
            "datagrams_offered_to_receiver": total_offered,
            "receiver_status_counts": dict(sorted(all_statuses.items())),
            "receiver_rejected_by_reason": dict(sorted(all_rejections.items())),
            "unobserved_forward_sequence_gap_count": total_gaps,
            "flight_commands_dispatched": 0,
            "flight_control_authority_granted": 0,
        },
        "scenarios": scenarios,
        "warning": (
            "Synthetic generator events and receiver-inferred sequence gaps are separate. "
            "Neither is a measured RF loss rate, radio timing, range, throughput, or hardware result."
        ),
    }


def run_experiment() -> dict[str, Any]:
    started_tracing_here = not tracemalloc.is_tracing()
    if started_tracing_here:
        tracemalloc.start()
    started = time.perf_counter()
    try:
        report = run_deterministic_experiment()
        elapsed = time.perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        if started_tracing_here:
            tracemalloc.stop()
    report["software_resource_observation"] = {
        "scope": "This Python process and these bounded synthetic fixtures only; not an RF or embedded measurement.",
        "host_elapsed_seconds": elapsed,
        "python_tracemalloc_peak_bytes": peak_bytes,
        "maximum_pending_delay_queue_observed": max(
            row["generator"]["maximum_pending_synthetic_delayed_datagrams"]
            for row in report["scenarios"]
        ),
        "maximum_generated_frames_per_scenario": MAX_FRAMES_PER_SCENARIO,
        "maximum_offered_datagrams_per_scenario": MAX_DELIVERIES_PER_SCENARIO,
        "host_runtime_guard_seconds": MAX_HOST_RUNTIME_SECONDS,
        "python_tracemalloc_guard_bytes": MAX_TRACEMALLOC_PEAK_BYTES,
        "delay_queue_bound_frames": MAX_FRAMES_PER_SCENARIO,
    }
    return report


def _input_trace() -> dict[str, Any]:
    trace_scenarios = []
    for scenario in _scenario_inputs():
        trace_scenarios.append({
            "scenario": scenario.name,
            "generated_frames": [
                {"generation_ordinal": frame.ordinal,
                 "session_label": frame.session_id,
                 "sequence": frame.sequence,
                 "datagram_hex": frame.datagram.hex()}
                for frame in scenario.generated
            ],
            "known_synthetic_drop_events": [
                {"generation_ordinal": frame.ordinal,
                 "session_label": frame.session_id,
                 "sequence": frame.sequence}
                for frame in scenario.known_drops
            ],
            "injected_fault_counts": scenario.injected_fault_counts,
            "maximum_pending_synthetic_delayed_datagrams": scenario.maximum_pending_delays,
            "receiver_delivery_trace": [
                {"source_generation_ordinal": event.source_ordinal,
                 "generator_label": event.generator_label,
                 "release_slot": event.release_slot,
                 "datagram_hex": event.datagram.hex()}
                for event in scenario.deliveries
            ],
        })
    return {
        "seed": SCENARIO_SEED,
        "bounded_seeded_frame_count": SEEDED_FRAME_COUNT,
        "delay_slots": DELAY_SLOTS,
        "delay_slot_units": "abstract ordering slots, not elapsed time",
        "scenarios": trace_scenarios,
    }


def _canonical_sha256(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _source_worktree_changes() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to inspect source worktree state")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def _tool_version(command_name: str, args: list[str]) -> str:
    executable = shutil.which(command_name)
    if executable is None:
        return "NOT_FOUND"
    return _command_version([executable, *args])


def _command_version(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "NOT_AVAILABLE"
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else f"EXIT_{result.returncode}_NO_VERSION_OUTPUT"


@lru_cache(maxsize=1)
def _platformio_compiler_versions() -> dict[str, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "platformio", "system", "info", "--json-output"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is None or result.returncode != 0:
        return {key: "NOT_AVAILABLE" for key in (
            "arm_none_eabi_g++", "xtensa_lx106_g++", "native_host_g++"
        )}
    try:
        core_dir = Path(json.loads(result.stdout)["core_dir"]["value"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return {key: "NOT_AVAILABLE" for key in (
            "arm_none_eabi_g++", "xtensa_lx106_g++", "native_host_g++"
        )}

    compiler_paths = {
        "arm_none_eabi_g++": core_dir / "packages" / "toolchain-gccarmnoneeabi" / "bin" / "arm-none-eabi-g++",
        "xtensa_lx106_g++": core_dir / "packages" / "toolchain-xtensa" / "bin" / "xtensa-lx106-elf-g++",
        "native_host_g++": core_dir / "packages" / "toolchain-gccmingw32" / "bin" / "g++",
    }
    suffix = ".exe" if sys.platform == "win32" else ""
    versions: dict[str, str] = {}
    for name, base_path in compiler_paths.items():
        compiler = base_path.with_name(base_path.name + suffix)
        versions[name] = (
            _command_version([str(compiler), "--version"])
            if compiler.is_file() else "NOT_INSTALLED"
        )
    return versions


def evidence(command: str, artifact_path: str) -> dict[str, Any]:
    report = run_experiment()
    stable_report = {key: value for key, value in report.items()
                     if key != "software_resource_observation"}
    changes = _source_worktree_changes()
    source_hashes = {path: _file_sha256(ROOT / path) for path in SOURCE_PATHS}
    trace = _input_trace()
    return {
        "schema_version": 1,
        "experiment": report["experiment"],
        "source_git_sha": _git_sha(),
        "source_worktree_clean": not changes,
        "source_worktree_changes": changes,
        "source_sha256": source_hashes,
        "input_trace_sha256": _canonical_sha256(trace),
        "deterministic_result_sha256": _canonical_sha256(stable_report),
        "input_seed": SCENARIO_SEED,
        "input_trace": trace,
        "command": command,
        "reproduction_command": command,
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "platformio_core": _command_version([sys.executable, "-m", "platformio", "--version"]),
            "platformio_cli": (
                _tool_version("platformio", ["--version"])
                if shutil.which("platformio") else _tool_version("pio", ["--version"])
            ),
            "platformio_compiler_versions": _platformio_compiler_versions(),
        },
        "dependencies": "Python standard library only",
        "artifact_path": artifact_path,
        "evidence_ceiling": "TESTED_SOFTWARE",
        "synthetic_only": True,
        "physical_hardware": False,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "crc_is_authentication": False,
        "metrics_and_observations": report,
    }


def check_invariants(report: dict[str, Any]) -> list[str]:
    scenarios = report["scenarios"]
    if len(scenarios) != 10:
        raise AssertionError(f"expected 10 deterministic scenarios, got {len(scenarios)}")
    for row in scenarios:
        if row["generator"]["unique_frames_generated"] > MAX_FRAMES_PER_SCENARIO:
            raise AssertionError(f"frame bound exceeded in {row['scenario']}")
        if row["generator"]["datagrams_offered_to_receiver"] > MAX_DELIVERIES_PER_SCENARIO:
            raise AssertionError(f"delivery bound exceeded in {row['scenario']}")
        receiver = row["receiver"]
        if receiver["invalid_datagram_window_mutations"] != 0:
            raise AssertionError(f"invalid input mutated freshness window in {row['scenario']}")
        if receiver["duplicate_or_stale_window_mutations"] != 0:
            raise AssertionError(f"duplicate/stale input mutated window in {row['scenario']}")
        if receiver["flight_command_dispatches"] != 0 or receiver["flight_control_authority_grants"] != 0:
            raise AssertionError(f"control boundary violated in {row['scenario']}")
        if row["generator"]["datagrams_offered_to_receiver"] != len(row["observations"]):
            raise AssertionError(f"offered/observed count mismatch in {row['scenario']}")
        if row["generator"]["maximum_pending_synthetic_delayed_datagrams"] > MAX_FRAMES_PER_SCENARIO:
            raise AssertionError(f"delay queue bound exceeded in {row['scenario']}")
    resource = report.get("software_resource_observation")
    if resource is not None:
        if resource["host_elapsed_seconds"] > MAX_HOST_RUNTIME_SECONDS:
            raise AssertionError("bounded software experiment exceeded host runtime guard")
        if resource["python_tracemalloc_peak_bytes"] > MAX_TRACEMALLOC_PEAK_BYTES:
            raise AssertionError("bounded software experiment exceeded tracemalloc guard")
    return [
        "generator drops and receiver sequence gaps are independently counted",
        "malformed datagrams do not mutate receiver freshness state",
        "duplicate and stale datagrams do not mutate receiver freshness state",
        "session labels remain explicitly unauthenticated",
        "no flight command dispatch or control authority exists in the harness",
        "all streams stay within fixed frame and delivery bounds",
        "observed host runtime and Python allocation stay inside software-only guardrails",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="run invariant checks and print summary")
    group.add_argument("--write-evidence", type=Path, help="write a new evidence JSON without overwriting")
    args = parser.parse_args(argv)

    if args.write_evidence is not None:
        output = args.write_evidence
        artifact_path = output.as_posix()
        command = (
            "py -3 -m rf_lab.reliability_experiment --write-evidence "
            + "'" + artifact_path.replace("'", "''") + "'"
        )
        record = evidence(command, artifact_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
        print(json.dumps({
            "evidence": "WRITTEN",
            "artifact_path": artifact_path,
            "artifact_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "source_git_sha": record["source_git_sha"],
            "input_trace_sha256": record["input_trace_sha256"],
            "deterministic_result_sha256": record["deterministic_result_sha256"],
            "source_worktree_clean": record["source_worktree_clean"],
        }, ensure_ascii=False, sort_keys=True))
        return 0

    report = run_experiment()
    checks = check_invariants(report)
    if args.check:
        print(json.dumps({
            "result": "PASS",
            "experiment": report["experiment"],
            "summary": report["summary"],
            "scenario_names": [row["scenario"] for row in report["scenarios"]],
            "invariants": checks,
            "software_resource_observation": report["software_resource_observation"],
            "warning": report["warning"],
        }, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
