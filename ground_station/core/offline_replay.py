"""Deterministic, telemetry-only input. No transport or command capability."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from PySide6.QtCore import QObject, QTimer, Signal


FIXTURE = Path(__file__).resolve().parents[1] / "replay" / "system_v1.json"
SOURCE = "SIMULATION / OFFLINE REPLAY"


def load_timeline(path=FIXTURE):
    raw = Path(path).read_bytes()
    document = json.loads(raw)
    if document["source"] != SOURCE:
        raise ValueError("replay must explicitly identify synthetic input")
    previous = -1
    for event in document["events"]:
        offset = event["at_ms"]
        if type(offset) is not int or offset <= previous or offset < 0:
            raise ValueError("replay offsets must be increasing nonnegative integer ms")
        previous = offset
        if event["kind"] == "sample":
            if not isinstance(event["telemetry"], dict):
                raise ValueError("replay samples must be telemetry dictionaries, not commands")
        elif event["kind"] != "gap":
            raise ValueError("unknown replay event")
    if not document["events"]:
        raise ValueError("empty replay")
    return document, hashlib.sha256(raw).hexdigest()


class OfflineReplay(QObject):
    data_received = Signal(str)
    state_changed = Signal(str)
    gap_started = Signal()

    def __init__(self, parent=None, *, clock=time.monotonic, path=FIXTURE):
        super().__init__(parent)
        self.document, self.input_sha256 = load_timeline(path)
        self.clock = clock
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self._tick)
        self.state = "STOPPED"
        self.position = 0
        self.elapsed_ms = 0
        self._anchor = None

    def _set_state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def start(self):
        if self.state == "PAUSED":
            self._anchor = self.clock() - self.elapsed_ms / 1000
        elif self.state != "RUNNING":
            self.position = 0
            self.elapsed_ms = 0
            self._anchor = self.clock()
        else:
            return
        self._set_state("RUNNING")
        self.timer.start()
        self._tick()

    def pause(self):
        if self.state == "RUNNING":
            self._tick()
            if self.state == "RUNNING":
                self.timer.stop()
                self._set_state("PAUSED")

    def stop(self):
        self.timer.stop()
        self._set_state("STOPPED")

    def _tick(self):
        if self.state != "RUNNING":
            return
        self.elapsed_ms = max(self.elapsed_ms, int(round((self.clock() - self._anchor) * 1000)))
        events = self.document["events"]
        while self.position < len(events) and events[self.position]["at_ms"] <= self.elapsed_ms:
            event = events[self.position]
            self.position += 1
            if event["kind"] == "gap":
                self.gap_started.emit()
            else:
                # Provenance is supplied by this input boundary, never inferred
                # from a producer's PHYSICAL/CRC/session tag.
                sample = dict(event["telemetry"])
                sample["source_mode"] = SOURCE
                sample["replay_time_ms"] = event["at_ms"]
                self.data_received.emit(json.dumps(sample, sort_keys=True, allow_nan=False))
        if self.position == len(events):
            self.timer.stop()
            self._set_state("FINISHED")
