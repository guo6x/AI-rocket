"""Keep Qt's opt-in Windows software GL and PyOpenGL on the same DLL.

Call before importing pyqtgraph.opengl or any OpenGL entry points. This only
selects a dispatcher; it does not create a context or prove visible rendering.
"""

import ctypes
from importlib import import_module
import os
from pathlib import Path
import sys


class OpenGLBackendError(RuntimeError):
    """The launcher can report this error and retain its 2D fallback."""


def _has_gl_entry_points(name):
    return any(
        name == prefix or name.startswith(prefix + ".")
        for prefix in ("OpenGL.GL", "OpenGL.GLU", "OpenGL.raw.GL", "pyqtgraph.opengl")
    )


def _matches_path(name, path):
    if not isinstance(name, str):
        return False
    try:
        candidate = Path(name)
        return candidate.is_absolute() and candidate.resolve() == path
    except (OSError, ValueError):
        return False


def configure_pyopengl_backend() -> str:
    """Configure explicit software GL, refusing any unsafe late DLL switch.

    Desktop/non-Windows paths are untouched. No global error-checking flags,
    installed packages, driver files, or environment variables are modified.
    """
    if sys.platform != "win32" or os.environ.get("QT_OPENGL", "").strip().lower() != "software":
        return "platform-default"

    try:
        package = import_module("PySide6")
        dll_path = (Path(package.__file__).resolve().parent / "opengl32sw.dll").resolve()
    except (ImportError, AttributeError, TypeError, OSError) as error:
        raise OpenGLBackendError(f"Cannot locate the PySide6 software OpenGL DLL: {error}") from error
    if not dll_path.is_file():
        raise OpenGLBackendError(
            f"Missing {dll_path}; repair the existing PySide6 installation or use the 2D fallback."
        )

    configured = os.environ.get("QT_OPENGL_DLL", "").strip()
    if configured and not _matches_path(configured, dll_path):
        raise OpenGLBackendError(
            f"QT_OPENGL_DLL must be the absolute bundled DLL path {dll_path}; "
            "unset the conflicting override and restart, or use the 2D fallback."
        )

    try:
        platform = import_module("OpenGL.platform")
        selected = f"qt-software:{dll_path}"
        if _matches_path(getattr(platform.PLATFORM.GL, "_name", None), dll_path):
            return selected
        if any(_has_gl_entry_points(name) for name in tuple(sys.modules)):
            raise OpenGLBackendError(
                "Configure Qt software OpenGL before importing OpenGL/pyqtgraph.opengl; "
                "restart the application to avoid hot-switching cached GL entry points."
            )

        # A fresh platform avoids stale lazy GetCurrentContext, OpenGL and
        # wglGetProcAddress properties captured from the system opengl32.dll.
        replacement = import_module("OpenGL.platform.win32").Win32Platform()
        replacement.GL = ctypes.WinDLL(str(dll_path))
        replacement.install(platform.__dict__)
        return selected
    except (ImportError, AttributeError, OSError, KeyError) as error:
        raise OpenGLBackendError(f"Cannot load the bundled software OpenGL backend: {error}") from error
