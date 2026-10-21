"""
Unit tests for Phase 3: Universal Bundled Packaging & VS Code Extension Auto-Installer.
1. Bundled extension assets discovery.
2. VSIX OPC package creation using zipfile.
3. Extension installation into IDE directory.
4. is_extension_installed detection.
5. CLI argument handling for install-extension / vscode.
"""

from pathlib import Path
import zipfile
import pytest

from app.extension.installer import (
    EXTENSION_ID,
    build_vsix_package,
    ensure_extension_installed,
    get_bundled_extension_path,
    get_target_extension_dirs,
    install_extension,
    is_extension_installed,
)
from app.cli.interactive import run
from app.cli.session import SessionState


def test_bundled_extension_assets_exist():
    bundled_dir = get_bundled_extension_path()
    assert bundled_dir.exists(), f"Bundled dir {bundled_dir} does not exist"
    assert (bundled_dir / "package.json").exists(), "package.json missing from bundled extension"
    assert (bundled_dir / "out").exists(), "out/ directory missing from bundled extension"
    assert (bundled_dir / "out" / "extension.js").exists(), "extension.js missing from out/"


def test_build_vsix_package(tmp_path):
    vsix_out = tmp_path / "test-extension.vsix"
    created = build_vsix_package(vsix_out)
    assert created.exists()
    assert created.stat().st_size > 0

    with zipfile.ZipFile(created, "r") as zf:
        namelist = zf.namelist()
        assert "[Content_Types].xml" in namelist
        assert "extension.vsixmanifest" in namelist
        assert "extension/package.json" in namelist
        assert "extension/out/extension.js" in namelist


def test_install_extension_to_custom_dir(tmp_path, monkeypatch):
    mock_ext_dir = tmp_path / ".vscode" / "extensions"
    monkeypatch.setattr(
        "app.extension.installer.get_target_extension_dirs",
        lambda: [mock_ext_dir],
    )

    # 1. Before install, should not be installed
    assert not is_extension_installed()

    # 2. Run installation
    res = install_extension(force=True)
    assert res["success"] is True
    assert len(res["locations"]) == 1

    installed_path = Path(res["locations"][0])
    assert installed_path.exists()
    assert (installed_path / "package.json").exists()
    assert (installed_path / "out" / "extension.js").exists()

    # 3. After install, is_extension_installed should return True
    assert is_extension_installed()

    # 4. ensure_extension_installed should report already_installed
    ensure_res = ensure_extension_installed()
    assert ensure_res.get("already_installed") is True


def test_cli_subcommand_install_extension(monkeypatch):
    called = []

    def mock_install_command():
        called.append(True)

    monkeypatch.setattr("app.cli.interactive.install_extension_command", mock_install_command)
    monkeypatch.setattr("sys.argv", ["edgemind", "install-extension"])

    run()
    assert called == [True]


def test_session_state_approval_default():
    session = SessionState()
    assert session.require_approval is True
