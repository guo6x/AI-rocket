"""The software-GL dispatcher is selected without creating Qt/UI/GL objects."""

from types import SimpleNamespace

import pytest

from ground_station.core import opengl_backend as backend


@pytest.fixture
def software_backend(monkeypatch, tmp_path):
    package = tmp_path / "PySide6"
    package.mkdir()
    software_dll = package / "opengl32sw.dll"
    software_dll.touch()
    old = SimpleNamespace(GL=SimpleNamespace(_name="opengl32.dll"))
    platform = SimpleNamespace(PLATFORM=old)
    calls = {"imports": [], "loads": [], "installs": []}

    class Win32Platform:
        def install(self, namespace):
            calls["installs"].append(self)
            namespace["PLATFORM"] = self

    modules = {
        "PySide6": SimpleNamespace(__file__=str(package / "__init__.py")),
        "OpenGL.platform": platform,
        "OpenGL.platform.win32": SimpleNamespace(Win32Platform=Win32Platform),
    }

    def import_module(name):
        calls["imports"].append(name)
        if name not in modules:
            raise ImportError(name)
        return modules[name]

    def load_dll(path):
        calls["loads"].append(path)
        return SimpleNamespace(_name=path)

    monkeypatch.setattr(backend.sys, "platform", "win32")
    monkeypatch.setenv("QT_OPENGL", "software")
    monkeypatch.delenv("QT_OPENGL_DLL", raising=False)
    monkeypatch.setattr(backend, "import_module", import_module)
    monkeypatch.setattr(backend.ctypes, "WinDLL", load_dll, raising=False)
    for name in tuple(backend.sys.modules):
        if backend._has_gl_entry_points(name):
            monkeypatch.delitem(backend.sys.modules, name)
    return SimpleNamespace(
        path=software_dll, old=old, platform=platform, calls=calls, modules=modules,
    )


@pytest.mark.parametrize("platform,mode", [
    ("win32", "desktop"), ("win32", ""), ("linux", "software"),
    ("darwin", "software"),
])
def test_other_backends_do_not_import_or_change_opengl(monkeypatch, platform, mode):
    monkeypatch.setattr(backend.sys, "platform", platform)
    monkeypatch.setenv("QT_OPENGL", mode)
    monkeypatch.setattr(backend, "import_module", lambda _: pytest.fail("unexpected import"))

    assert backend.configure_pyopengl_backend() == "platform-default"


def test_software_uses_new_platform_and_exact_package_dll(software_backend):
    fixture = software_backend

    selected = backend.configure_pyopengl_backend()

    assert selected == f"qt-software:{fixture.path.resolve()}"
    assert fixture.calls["loads"] == [str(fixture.path.resolve())]
    assert fixture.calls["installs"] == [fixture.platform.PLATFORM]
    assert fixture.platform.PLATFORM is not fixture.old
    assert fixture.platform.PLATFORM.GL._name == str(fixture.path.resolve())
    assert fixture.old.GL._name == "opengl32.dll"
    assert not any(backend._has_gl_entry_points(name) for name in fixture.calls["imports"])


def test_matching_platform_is_idempotent_after_gl_import(software_backend, monkeypatch):
    fixture = software_backend
    selected = backend.configure_pyopengl_backend()
    installed = fixture.platform.PLATFORM
    monkeypatch.setitem(backend.sys.modules, "OpenGL.raw.GL._errors", SimpleNamespace())

    assert backend.configure_pyopengl_backend() == selected
    assert fixture.platform.PLATFORM is installed
    assert len(fixture.calls["loads"]) == len(fixture.calls["installs"]) == 1


@pytest.mark.parametrize("module", [
    "OpenGL.GL", "OpenGL.raw.GL._errors", "OpenGL.GLU", "pyqtgraph.opengl",
])
def test_mismatched_loaded_entry_points_cannot_be_hot_switched(software_backend, monkeypatch, module):
    fixture = software_backend
    monkeypatch.setitem(backend.sys.modules, module, SimpleNamespace())

    with pytest.raises(RuntimeError, match="before.*OpenGL.*restart"):
        backend.configure_pyopengl_backend()

    assert fixture.platform.PLATFORM is fixture.old
    assert fixture.calls["loads"] == fixture.calls["installs"] == []


def test_missing_bundled_dll_has_actionable_error(software_backend):
    fixture = software_backend
    fixture.path.unlink()

    with pytest.raises(RuntimeError, match="opengl32sw.dll.*repair.*PySide6"):
        backend.configure_pyopengl_backend()

    assert fixture.calls["loads"] == fixture.calls["installs"] == []


def test_loader_failure_does_not_replace_the_platform(software_backend, monkeypatch):
    fixture = software_backend

    def fail_loading(_path):
        raise OSError("incompatible DLL")

    monkeypatch.setattr(backend.ctypes, "WinDLL", fail_loading)
    with pytest.raises(RuntimeError, match="Cannot load.*incompatible DLL"):
        backend.configure_pyopengl_backend()

    assert fixture.platform.PLATFORM is fixture.old
    assert fixture.calls["installs"] == []


@pytest.mark.parametrize("configured", ["opengl32sw.dll", "other/opengl32sw.dll", "C:\\invalid|path.dll"])
def test_qt_dll_override_cannot_select_an_unverified_search_path(software_backend, monkeypatch, configured):
    fixture = software_backend
    monkeypatch.setenv("QT_OPENGL_DLL", configured)

    with pytest.raises(RuntimeError, match="QT_OPENGL_DLL.*absolute.*bundled"):
        backend.configure_pyopengl_backend()

    assert fixture.calls["loads"] == fixture.calls["installs"] == []


def test_conflicting_absolute_qt_dll_override_is_rejected(software_backend, monkeypatch):
    fixture = software_backend
    monkeypatch.setenv("QT_OPENGL_DLL", str(fixture.path.parent / "different.dll"))

    with pytest.raises(RuntimeError, match="QT_OPENGL_DLL.*absolute.*bundled"):
        backend.configure_pyopengl_backend()

    assert fixture.calls["loads"] == fixture.calls["installs"] == []


def test_matching_explicit_qt_dll_override_is_allowed(software_backend, monkeypatch):
    fixture = software_backend
    monkeypatch.setenv("QT_OPENGL_DLL", str(fixture.path.resolve()))

    assert backend.configure_pyopengl_backend() == f"qt-software:{fixture.path.resolve()}"
    assert len(fixture.calls["installs"]) == 1


def test_unavailable_pyside_has_actionable_error(software_backend):
    software_backend.modules.pop("PySide6")

    with pytest.raises(RuntimeError, match="locate.*PySide6"):
        backend.configure_pyopengl_backend()

    assert software_backend.calls["loads"] == software_backend.calls["installs"] == []
