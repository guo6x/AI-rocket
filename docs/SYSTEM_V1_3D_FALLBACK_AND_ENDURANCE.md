# SYSTEM-V1 desktop rendering & endurance follow-up

**Scope:** Issue #26; read-only Ground Station software only. No RF/hardware/control permissions changed.

## Verified baseline before this change

- Mainline exact SHA `e7af916a805f7cfc239b5b310f6ab6883f323046`, with a **real successful main push CI**: [run 40179892545](https://github.com/guo6x/AI-rocket/actions/runs/40179892545). This is the **pre-follow-up** baseline, not the new branch verification result.
- Windows runtime evidence at `engineering/offline-evidence/system_v1/runtime_v2/` reports `PARTIALLY_VERIFIED`, 4,500 frames in 260.164 wall seconds, `opengl.status=NOT_VERIFIED`. The previously observed OpenGL failure was GL error 1282; the specific driver, OpenGL profile/context cause has **not** been determined.
- A Qt context or a call to `paintGL` is **not** visible-frame proof: successful GL framebuffer capture and different displayed synthetic poses are required before declaring visible 3D. Qt explicitly distinguishes resource initialization from painting, so these are separate checks.

## Scoped implementation

Keep the existing GLViewWidget and the rest of the original Ground Station. A new `ui.attitude_fallback.AttitudeFallbackWidget` uses only Qt `QPainter` to render two schematic pitch/roll indicators if OpenGL fails. This is intentionally **2D**, and a simplification independent of unmeasured mounting axes, yaw, current mechanical CAD or transmitter identity.

Two fallback paths are guarded:

1. `paintGL` throws an exception: mark 3D `NOT_VERIFIED`, show the real QPainter widget and its description, defer hiding the GL child until the paint callback returns.
2. No usable GL frame appears for 1.5s while the attitude tab is visible: trigger the same fallback rather than leaving an empty tab. If importing/constructing OpenGL view fails, instantiate the QPainter indicator as the tab directly.

Any numerical `nan`, infinity or extreme overflow is rejected without changing displayed fallback attitude. Tests compare **actual rendered QImages** under distinct reported roll/pitch values. 2D fallback PASS is *not* 3D PASS, not a measurement validation, and not hardware qualification.

The runtime acceptance harness now attempts to capture nonempty fallback images for two synthetic poses, reports `fallback_2d.status` separately from `opengl.status`, and can run either the former 4500-sample finite smoke or an actual wall-clock duration. CI tests the existing application under a headless Qt runner and retains replay screenshots when available. A headless Linux CI result **cannot prove** the original Windows GPU/driver 3D path works.

## Duration-controlled soak (future target-host acceptance, **not yet executed here**)

Run from an isolated Windows development environment using the exact tested source:

```powershell
.\.venv\Scripts\python.exe -u scripts/system_v1_runtime.py --output engineering/offline-evidence/system_v1/endurance_new_run --soak-minutes 120
```

The script exercises real Qt event loop, original parser, panel plots and data logger, with serial/socket constructors blocked. It does not transmit UDP or touch devices. A QTimer tick records synthetic events at an attempted 20ms interval; **20ms is a synthetic input interval, not a measured firmware frequency nor a guaranteed Qt render frame rate**.

At least every 500 samples, the script prints/writes traced-Python memory, Windows RSS where available, plot/log/parser bounds and elapsed time. In wall-clock mode, a million rapid samples in five minutes do **not** satisfy the 2-hour gate. A completed run reports `duration_gate=OBSERVED_2H` only after at least 7200 seconds; otherwise it is `SHORT_OBSERVATION`. The code records slope in bytes per hour, **does not assume an arbitrary PASS leak threshold**, and does not interpret Windows working-set trimming as leak freedom.

A run must be independently checked for exit 0, complete data, source hash and stable cache ceiling; memory growth and runtime responsiveness require separate acceptance criteria. Do not assert `2H PASS` from unit tests or a short CI smoke.

## Remaining engineering status

- Existing original OpenGL 3D **NOT_VERIFIED** on the recorded Windows host; 2D Qt fallback can be tested independently.
- Real 2-hour Windows desktop observation **NOT_EVALUATED** until its output exists.
- Real RF, ESP, sensor provenance, control timing, motor, servo, recovery hardware and physical aircraft qualification **NOT_EVALUATED/BLOCKED** as before.
- CAD remains **NOT_STARTED** and old AI-generated model assets rejected. Do not merge deferred legacy purge PR #21 as part of this work.
