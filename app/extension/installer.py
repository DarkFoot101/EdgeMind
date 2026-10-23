"""
EdgeMind Universal VS Code & Cursor Extension Installer.

Automatically bundles and deploys the EdgeMind VS Code extension directly
into local IDE environments (~/.vscode/extensions, ~/.cursor/extensions)
or builds and installs via the `code` / `cursor` CLI.
"""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import zipfile

from app import __version__

EXTENSION_ID = f"edgemind.edgemind-vscode-{__version__}"
CONFIG_DIR = Path.home() / ".edgemind"


def get_bundled_extension_path() -> Path:
    """Return the path to the bundled extension directory containing package.json and out/."""
    bundled_dir = Path(__file__).parent / "bundled"
    if bundled_dir.exists() and (bundled_dir / "package.json").exists():
        return bundled_dir

    # Fallback to repo root if running from source checkout
    repo_root = Path(__file__).resolve().parent.parent.parent
    if (repo_root / "package.json").exists() and (repo_root / "out").exists():
        return repo_root

    return bundled_dir


def get_target_extension_dirs() -> List[Path]:
    """
    Return candidate directories where VS Code, Antigravity IDE, Cursor, and VSCodium store user extensions.
    Includes ~/.vscode/extensions by default so fresh environments are supported.
    """
    home = Path.home()
    candidates = [
        home / ".antigravity-ide" / "extensions",
        home / ".antigravity" / "extensions",
        home / ".vscode" / "extensions",
        home / ".cursor" / "extensions",
        home / ".windsurf" / "extensions",
        home / ".vscode-insiders" / "extensions",
        home / ".vscode-oss" / "extensions",
    ]

    existing = [p for p in candidates if p.parent.exists()]
    if not existing:
        existing = [home / ".vscode" / "extensions"]

    return existing


def is_extension_installed() -> bool:
    """Check if the EdgeMind extension is already installed in any supported IDE."""
    for ext_dir in get_target_extension_dirs():
        target = ext_dir / EXTENSION_ID
        if target.exists() and (target / "package.json").exists() and (target / "out").exists():
            return True
    return False


def build_vsix_package(output_path: Optional[Path] = None) -> Path:
    """
    Build a standard Open Packaging Conventions (.vsix) archive containing the extension.
    Uses pure Python standard library zipfile with zero external node dependencies.
    """
    source_dir = get_bundled_extension_path()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out_file = output_path or (CONFIG_DIR / f"edgemind-vscode-{__version__}.vsix")

    content_types_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="json" ContentType="application/json"/>\n'
        '  <Default Extension="js" ContentType="application/javascript"/>\n'
        '  <Default Extension="map" ContentType="application/json"/>\n'
        '  <Default Extension="xml" ContentType="text/xml"/>\n'
        '  <Default Extension="vsixmanifest" ContentType="text/xml"/>\n'
        '</Types>'
    )

    vsix_manifest_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<PackageManifest Version="{__version__}" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">\n'
        '  <Metadata>\n'
        f'    <Identity Id="edgemind-vscode" Version="{__version__}" Publisher="edgemind"/>\n'
        '    <DisplayName>EdgeMind AI</DisplayName>\n'
        '    <Description>Local Resource-Aware AI Coding Assistant for VS Code</Description>\n'
        '  </Metadata>\n'
        '  <Installation>\n'
        '    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>\n'
        '  </Installation>\n'
        '  <Dependencies/>\n'
        '  <Assets>\n'
        '    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>\n'
        '  </Assets>\n'
        '</PackageManifest>'
    )

    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("extension.vsixmanifest", vsix_manifest_xml)

        pkg_json = source_dir / "package.json"
        if pkg_json.exists():
            zf.write(pkg_json, arcname="extension/package.json")

        out_dir = source_dir / "out"
        if out_dir.exists():
            for f in out_dir.rglob("*"):
                if f.is_file():
                    arc_path = f"extension/out/{f.relative_to(out_dir)}"
                    zf.write(f, arcname=arc_path)

    return out_file


def install_extension(force: bool = True) -> Dict[str, Any]:
    """
    Install the EdgeMind extension into local editors.
    Deploys directly to extension directories and generates a standalone .vsix file.
    """
    source_dir = get_bundled_extension_path()
    if not source_dir.exists() or not (source_dir / "package.json").exists():
        return {
            "success": False,
            "error": f"Bundled extension assets not found at {source_dir}",
            "locations": [],
        }

    installed_locations: List[str] = []
    target_dirs = get_target_extension_dirs()

    for base_dir in target_dirs:
        try:
            dest = base_dir / EXTENSION_ID
            if dest.exists() and not force:
                installed_locations.append(str(dest))
                continue

            base_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)

            dest.mkdir(parents=True, exist_ok=True)

            # Copy package.json
            src_pkg = source_dir / "package.json"
            if src_pkg.exists():
                shutil.copy2(src_pkg, dest / "package.json")

            # Copy out directory
            src_out = source_dir / "out"
            if src_out.exists():
                dest_out = dest / "out"
                if dest_out.exists():
                    shutil.rmtree(dest_out, ignore_errors=True)
                shutil.copytree(src_out, dest_out)

            installed_locations.append(str(dest))
        except Exception:
            continue

    # Build standalone VSIX
    vsix_path = None
    try:
        vsix_path = build_vsix_package()
    except Exception:
        pass

    # Attempt CLI install if code or cursor is available in PATH
    for cli_cmd in ["code", "cursor", "vscodium"]:
        cli_bin = shutil.which(cli_cmd)
        if cli_bin and vsix_path and vsix_path.exists():
            try:
                subprocess.run(
                    [cli_bin, "--install-extension", str(vsix_path), "--force"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    check=False,
                )
            except Exception:
                pass

    return {
        "success": len(installed_locations) > 0,
        "locations": installed_locations,
        "vsix_path": str(vsix_path) if vsix_path else None,
    }


def ensure_extension_installed() -> Dict[str, Any]:
    """Ensure extension is installed on startup; installs automatically if missing."""
    if is_extension_installed():
        return {"success": True, "already_installed": True}
    return install_extension(force=True)
