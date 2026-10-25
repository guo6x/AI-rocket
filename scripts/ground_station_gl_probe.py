"""Bounded, device-free native Qt/OpenGL diagnostic for Issue #26.

This opens the existing Ground Station, not a substitute renderer. PNGs are
actual Qt window/framebuffer captures. A non-null context alone never passes.
Optional format overrides are experiments, not changes to application defaults.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ground_station"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def format_info(fmt):
    return {"version": list(fmt.version()), "profile": fmt.profile().name,
            "renderable_type": fmt.renderableType().name,
            "options": fmt.options().value, "depth_bits": fmt.depthBufferSize(),
            "samples": fmt.samples()}


def image_pixels(image):
    from PySide6.QtGui import QImage
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = np.frombuffer(rgba.constBits(), np.uint8).reshape(
        rgba.height(), rgba.bytesPerLine() // 4, 4
    )[:, :rgba.width()].copy()
    return pixels


def projected_box_evidence(view, pose, pixels):
    """Check actual blue box edges against an independent Euler rotation.

    Camera/projection are the current display settings, not physical parameters.
    The rotation is Rz(yaw) @ Ry(pitch) @ Rx(roll), independently using numpy.
    """
    roll, pitch, yaw = map(math.radians, pose)
    cr, sr, cp, sp, cy, sy = (math.cos(roll), math.sin(roll), math.cos(pitch),
                             math.sin(pitch), math.cos(yaw), math.sin(yaw))
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    corners = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-6, 6)])
    rotated = corners @ (rz @ ry @ rx).T
    camera = np.array(view.viewMatrix().copyDataTo()).reshape(4, 4)
    viewport = (0, 0, view.width(), view.height())
    projection = np.array(view.projectionMatrix(viewport, viewport).copyDataTo()).reshape(4, 4)
    clip = (projection @ camera @ np.c_[rotated, np.ones(8)].T).T
    ndc = clip[:, :3] / clip[:, 3:4]
    height, width = pixels.shape[:2]
    points = np.c_[(ndc[:, 0] + 1) * width / 2, (1 - ndc[:, 1]) * height / 2]
    rgb = pixels[:, :, :3].astype(int)
    blue = (rgb[:, :, 2] > rgb[:, :, 0] + 45) & (rgb[:, :, 2] > rgb[:, :, 1] + 20)
    hit, samples = 0, 0
    for i in range(8):
        for j in range(i + 1, 8):
            if np.count_nonzero(corners[i] != corners[j]) != 1:
                continue
            for t in np.linspace(0.1, 0.9, 9):
                x, y = np.rint(points[i] * (1-t) + points[j] * t).astype(int)
                samples += 1
                if 0 <= x < width and 0 <= y < height:
                    hit += int(blue[max(0, y-3):y+4, max(0, x-3):x+4].any())
    return {"reference": "independent numpy Rz @ Ry @ Rx; arbitrary-unit box, not CAD",
            "all_corners_inside": bool((abs(ndc[:, :2]) < 1).all()),
            "projected_corners_px": points.round(3).tolist(),
            "edge_samples": samples, "blue_edge_hit_fraction": hit / samples}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--format", choices=("production", "compat33", "core33"), default="production")
    parser.add_argument("--software-dispatch", action="store_true",
                        help="select QT_OPENGL=software; use the production backend bootstrap")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output must be new or empty; preserve previous evidence")
    output.mkdir(parents=True, exist_ok=True)
    poses = [(0.0, 0.0, 0.0), (32.0, -24.0, 0.0)]
    input_bytes = (json.dumps({"poses_roll_pitch_yaw_deg": poses,
                              "source_mode": "SIMULATION / OFFLINE REPLAY"},
                             sort_keys=True, separators=(",", ":")) + "\n").encode()
    (output / "synthetic_poses.json").write_bytes(input_bytes)
    result = {"status": "NOT_VERIFIED", "poses": [], "qt_messages": [],
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "input": {"path": "synthetic_poses.json",
                        "sha256": hashlib.sha256(input_bytes).hexdigest()},
              "boundary": {"synthetic_only": True, "hardware_connections": 0,
                           "control_sends": 0, "radio_transmissions": 0,
                           "hardware_verified": False, "source_authenticated": False}}
    result["source_git_sha"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["source_git_status"] = subprocess.check_output(
        ["git", "status", "--short"], cwd=ROOT, text=True).splitlines()
    result["source_sha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
        for path in (ROOT / "ground_station/main.py", ROOT / "ground_station/ui/view3d_widget.py",
                     ROOT / "ground_station/ui/main_window.py", Path(__file__))}
    backend_source = ROOT / "ground_station/core/opengl_backend.py"
    if backend_source.is_file():
        result["source_sha256"]["ground_station/core/opengl_backend.py"] = sha256(backend_source)
    result["environment"] = {"python": sys.version, "executable": sys.executable,
        "platform": platform.platform(),
        "dependencies": {name: importlib.metadata.version(name)
            for name in ("PySide6", "shiboken6", "pyqtgraph", "PyOpenGL", "numpy")},
        "qt_env": {key: value for key, value in os.environ.items()
                   if key.startswith(("QT_", "PYOPENGL"))}}
    result["command"] = subprocess.list2cmdline([sys.executable, *sys.argv])
    result["format_experiment"] = args.format
    if args.software_dispatch:
        if sys.platform != "win32":
            parser.error("software-dispatch experiment requires Windows")
        os.environ["QT_OPENGL"] = "software"

    import main as launcher
    from PySide6.QtCore import QTimer, qInstallMessageHandler
    from PySide6.QtGui import QSurfaceFormat
    from ui.main_window import MainWindow

    def message_handler(kind, context, message):
        result["qt_messages"].append({"type": kind.name, "message": message})
        print(f"Qt {kind.name}: {message}", flush=True)

    old_handler = qInstallMessageHandler(message_handler)

    def deny_io(*_args, **_kwargs):
        raise AssertionError("OpenGL probe prohibits device/socket I/O")

    frames = []
    with patch("serial.Serial", deny_io), patch("socket.socket", deny_io), \
            patch("ui.main_window.get_available_ports", lambda: []):
        if args.format != "production":
            fmt = QSurfaceFormat()
            fmt.setVersion(3, 3)
            fmt.setProfile(QSurfaceFormat.CompatibilityProfile if args.format == "compat33"
                           else QSurfaceFormat.CoreProfile)
            original_set_format = QSurfaceFormat.setDefaultFormat
            format_override = patch.object(QSurfaceFormat, "setDefaultFormat",
                side_effect=lambda _requested: original_set_format(fmt))
        else:
            format_override = nullcontext()
        with format_override:
            app = launcher.create_application(["Ground Station native GL probe — SYNTHETIC ONLY"])
        result["production_backend"] = app.property("opengl_backend")
        result["backend_error"] = app.property("opengl_backend_error")
        result["environment"]["qt_env_effective"] = {key: value for key, value in os.environ.items()
            if key.startswith(("QT_", "PYOPENGL"))}
        result["requested_format"] = format_info(QSurfaceFormat.defaultFormat())
        result["qt_platform"] = app.platformName()
        result["screens"] = [{"name": s.name(), "size": [s.size().width(), s.size().height()],
                              "device_pixel_ratio": s.devicePixelRatio()}
                             for s in app.screens()]
        window = MainWindow()
        window.resize(1360, 980)
        window.mode_combo.setCurrentIndex(2)
        window.connection_mode = "offline"
        window.replay_status_label.setText("GL PROBE — two fixed synthetic poses; no transport")
        window.show()
        panel = window.view3d_panel
        window.tab_widget.setCurrentWidget(panel)
        gl_view = getattr(panel, "gl_view", None)

        def capture(index, pose):
            try:
                window.poll_link_and_command_state()
                shot = output / f"window_pose_{index}.png"
                assert window.grab().save(str(shot))
                record = {"pose_roll_pitch_yaw_deg": pose, "window": shot.name,
                          "window_sha256": sha256(shot),
                          "ui_status": window.view3d_status_label.text()}
                result["poses"].append(record)
                if gl_view is None:
                    raise RuntimeError("OpenGL widget unavailable; existing fallback retained")
                record.update(context_valid=gl_view.isValid(), successful_paint=gl_view.render_ok,
                              render_error=gl_view.render_error, visible=gl_view.isVisible())
                ctx = gl_view.context()
                if ctx:
                    record["actual_format"] = format_info(ctx.format())
                    record["is_gles"] = ctx.isOpenGLES()
                if gl_view.isValid():
                    gl_view.makeCurrent()
                    from OpenGL import GL, platform as ogl_platform
                    from PySide6.QtGui import QOpenGLContext
                    result["current_context_matches_widget"] = QOpenGLContext.currentContext() == ctx
                    result["pyopengl_current_context"] = int(ogl_platform.GetCurrentContext() or 0)
                    result["pyopengl_dll"] = str(ogl_platform.PLATFORM.GL._name)
                    dll_path = Path(result["pyopengl_dll"])
                    if dll_path.is_absolute() and dll_path.is_file():
                        result["pyopengl_dll_sha256"] = sha256(dll_path)
                    result["gl_error_before_diagnostic"] = int(GL.glGetError())
                    result["gl_strings"] = {name: (GL.glGetString(enum) or b"").decode(errors="replace")
                        for name, enum in (("vendor", GL.GL_VENDOR), ("renderer", GL.GL_RENDERER),
                                           ("version", GL.GL_VERSION), ("glsl", GL.GL_SHADING_LANGUAGE_VERSION))}
                    gl_view.doneCurrent()
                if not gl_view.isValid() or gl_view.render_error:
                    raise RuntimeError(gl_view.render_error or "no valid OpenGL widget context")
                image = gl_view.grabFramebuffer()
                if image.isNull() or gl_view.render_error:
                    raise RuntimeError(gl_view.render_error or "null framebuffer")
                path = output / f"gl_pose_{index}.png"
                assert image.save(str(path))
                pixels = image_pixels(image)
                rgb = pixels[:, :, :3].astype(int)
                blue = (rgb[:, :, 2] > rgb[:, :, 0] + 45) & (rgb[:, :, 2] > rgb[:, :, 1] + 20)
                record.update(framebuffer=path.name, framebuffer_sha256=sha256(path),
                    size=[image.width(), image.height()], blue_pixels=int(blue.sum()),
                    nonbackground_pixels=int(np.any(abs(rgb - 24) > 8, axis=2).sum()))
                record["geometry"] = projected_box_evidence(gl_view, pose, pixels)
                frames.append(pixels)
            except Exception as error:
                result.setdefault("errors", []).append(repr(error))
                print(repr(error), flush=True)

        def set_pose(pose):
            # Existing production parser -> dashboard -> existing 3D transform.
            sample = {"source_mode": "SIMULATION / OFFLINE REPLAY", "replay_time_ms": 0,
                      "time": 0, "sensor_valid": 1, "roll_flt": pose[0],
                      "pitch_flt": pose[1], "roll_raw": pose[0], "pitch_raw": pose[1],
                      "yaw": pose[2], "alt": 0, "auto": 0, "fstate": "IDLE"}
            window.on_data_received(json.dumps(sample))

        set_pose(poses[0])
        QTimer.singleShot(1200, lambda: capture(0, poses[0]))
        QTimer.singleShot(1600, lambda: set_pose(poses[1]))
        QTimer.singleShot(2600, lambda: capture(1, poses[1]))
        QTimer.singleShot(3200, app.quit)
        result["qt_exit_code"] = app.exec()
        window.close()
    qInstallMessageHandler(old_handler)
    if len(frames) == 2 and frames[0].shape == frames[1].shape:
        result["changed_pixels"] = int(np.any(frames[0][:, :, :3] != frames[1][:, :, :3], axis=2).sum())
        # Necessary pixel evidence only; inspect saved screenshots and verify
        # projected geometry before independently accepting 3D_RENDER_PASS.
        if (result["qt_exit_code"] == 0 and result["changed_pixels"] > 50 and not result.get("errors")
                and all(p.get("blue_pixels", 0) > 50 and p["geometry"]["all_corners_inside"]
                        and p["geometry"]["blue_edge_hit_fraction"] >= 0.75 for p in result["poses"])):
            result["status"] = "PIXEL_CANDIDATE_REQUIRES_REVIEW"
    result["wall_seconds"] = round(time.monotonic() - started, 3)
    result["process_exit_code"] = 0 if result["status"] == "PIXEL_CANDIDATE_REQUIRES_REVIEW" else 2
    (output / "probe_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result["process_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
