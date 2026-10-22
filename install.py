#!/usr/bin/env python3
"""Cross-platform installer for setup-orhun GitHub Action."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def log(msg: str) -> None:
    print(f"::notice::[setup-orhun] {msg}", flush=True)


def error(msg: str) -> None:
    print(f"::error::[setup-orhun] {msg}", file=sys.stderr, flush=True)


def set_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def add_to_path(path: Path) -> None:
    path_str = str(path.resolve())
    github_path = os.environ.get("GITHUB_PATH")
    if github_path:
        with open(github_path, "a", encoding="utf-8") as f:
            f.write(f"{path_str}\n")
    os.environ["PATH"] = path_str + os.pathsep + os.environ.get("PATH", "")
    log(f"Added {path_str} to GITHUB_PATH")


def detect_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return "windows-x64"
    elif system == "linux":
        return "linux-x64"
    elif system == "darwin":
        return "macos-arm64"
    raise RuntimeError(f"Unsupported platform: {system} {machine}")


def fetch_json(url: str, token: str | None = None) -> dict:
    headers = {"User-Agent": "setup-orhun-action"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: Path, token: str | None = None) -> None:
    headers = {"User-Agent": "setup-orhun-action"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def resolve_version(requested: str, token: str | None = None) -> tuple[str, str]:
    clean = requested.strip().lstrip("v")
    if not clean or clean.lower() == "latest":
        url = "https://api.github.com/repos/orhunlang/orhun/releases"
        try:
            releases = fetch_json(url, token)
            if releases:
                tag = releases[0]["tag_name"]
                return tag.lstrip("v"), tag
        except Exception:
            pass
        return "0.9.0", "v0.9.0"
    tag = f"v{clean}" if not requested.startswith("v") else requested
    return clean, tag


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Orhun Language in CI")
    parser.add_argument("--version", default="0.9.0", help="Orhun version")
    parser.add_argument(
        "--artifact",
        default="all",
        choices=["all", "compiler", "runtime"],
        help="Artifact flavor",
    )
    parser.add_argument("--token", default=None, help="GitHub token")
    args = parser.parse_args()

    version, tag = resolve_version(args.version, args.token)
    plat = detect_platform()
    ext = "zip" if plat.startswith("windows") else "tar.gz"

    runner_temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    work_dir = runner_temp / f"setup-orhun-{version}"
    work_dir.mkdir(parents=True, exist_ok=True)

    install_root = runner_temp / "orhun-install"
    bin_dir = runner_temp / "orhun-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"https://github.com/orhunlang/orhun/releases/download/{tag}"

    # Download official install_release.py
    installer_script = work_dir / "install_release.py"
    log(f"Downloading official Orhun installer from {base_url}/install_release.py...")
    download_file(f"{base_url}/install_release.py", installer_script, args.token)

    # Determine artifacts
    artifacts = ["runtime", "compiler"] if args.artifact in ("all", "compiler") else ["runtime"]

    for art in artifacts:
        archive_name = f"orhun-{art}-{version}-{plat}.{ext}"
        checksum_name = f"{archive_name}.sha256"

        archive_path = work_dir / archive_name
        checksum_path = work_dir / checksum_name

        log(f"Downloading {archive_name}...")
        download_file(f"{base_url}/{archive_name}", archive_path, args.token)
        download_file(f"{base_url}/{checksum_name}", checksum_path, args.token)

        log(f"Installing {archive_name} via install_release.py...")
        cmd = [
            sys.executable,
            str(installer_script),
            str(archive_path),
            "--checksum",
            str(checksum_path),
            "--install-root",
            str(install_root / art),
            "--bin-dir",
            str(bin_dir),
            "--force",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            error(f"Failed to install {art}:\n{proc.stdout}\n{proc.stderr}")
            return 1
        log(f"Successfully installed {art}: {proc.stdout.strip()}")

    # On Windows, also copy native .exe binaries directly into bin_dir
    # so Git Bash (bash.exe) can execute 'orhun' as well as CMD/PowerShell.
    for exe in install_root.rglob("*.exe"):
        dest = bin_dir / exe.name
        if not dest.exists():
            shutil.copy2(exe, dest)
            log(f"Copied native binary to bin: {dest.name}")

    add_to_path(bin_dir)
    set_output("orhun-version", version)
    set_output("orhun-path", str(bin_dir))

    # Verify installation
    log(f"Verifying Orhun in {bin_dir}...")
    orhun_cmd = "orhun"
    proc = subprocess.run(
        [orhun_cmd, "surum"],
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),
    )
    if proc.returncode == 0:
        log(f"Verified installation: {proc.stdout.strip()}")
    else:
        log(f"Installation note: {proc.stderr.strip() or proc.stdout.strip()}")

    log(f"Orhun v{version} setup successfully completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
