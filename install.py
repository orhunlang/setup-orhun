#!/usr/bin/env python3
"""Cross-platform installer for setup-orhun GitHub Action."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
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
    print(f"::set-output name={name}::{value}")


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
        if "arm" in machine or "aarch64" in machine:
            return "macos-arm64"
        return "macos-arm64"  # Default / Rosetta
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()


def resolve_version(requested: str, token: str | None = None) -> tuple[str, str]:
    """Returns (version_string, release_tag)."""
    clean = requested.strip().lstrip("v")
    if not clean or clean.lower() == "latest":
        url = "https://api.github.com/repos/orhunlang/orhun/releases/latest"
        try:
            data = fetch_json(url, token)
            tag = data.get("tag_name", "v0.9.0")
            return tag.lstrip("v"), tag
        except Exception:
            # Fallback to listing releases (v0.9.0 is prerelease)
            url = "https://api.github.com/repos/orhunlang/orhun/releases"
            releases = fetch_json(url, token)
            if releases:
                tag = releases[0]["tag_name"]
                return tag.lstrip("v"), tag
            return "0.9.0", "v0.9.0"
    tag = f"v{clean}" if not requested.startswith("v") else requested
    return clean, tag


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Orhun Language in CI")
    parser.add_argument("--version", default="0.9.0", help="Orhun version")
    parser.add_argument("--artifact", default="compiler", choices=["compiler", "runtime"])
    parser.add_argument("--token", default=None, help="GitHub token")
    args = parser.parse_args()

    version, tag = resolve_version(args.version, args.token)
    plat = detect_platform()
    ext = "zip" if "windows" in plat else "tar.gz"
    archive_name = f"orhun-{args.artifact}-{version}-{plat}.{ext}"
    checksum_name = f"{archive_name}.sha256"

    log(f"Installing Orhun {version} ({args.artifact}) for {plat}...")

    # Destination directories
    runner_temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    work_dir = runner_temp / f"setup-orhun-{version}"
    work_dir.mkdir(parents=True, exist_ok=True)

    archive_path = work_dir / archive_name
    checksum_path = work_dir / checksum_name

    base_url = f"https://github.com/orhunlang/orhun/releases/download/{tag}"
    download_url = f"{base_url}/{archive_name}"
    checksum_url = f"{base_url}/{checksum_name}"

    log(f"Downloading {download_url}...")
    try:
        download_file(download_url, archive_path, args.token)
    except Exception as e:
        error(f"Failed to download Orhun release asset: {e}")
        return 1

    log(f"Downloading checksum {checksum_url}...")
    try:
        download_file(checksum_url, checksum_path, args.token)
        expected_sha = checksum_path.read_text(encoding="ascii").strip().split()[0].lower()
        actual_sha = sha256_file(archive_path)
        if expected_sha != actual_sha:
            error(f"SHA-256 verification failed! Expected {expected_sha}, got {actual_sha}")
            return 1
        log(f"SHA-256 verified successfully: {actual_sha}")
    except Exception as e:
        log(f"Checksum verification note: {e}")

    # Extract
    install_dir = work_dir / "installed"
    install_dir.mkdir(parents=True, exist_ok=True)
    log(f"Extracting to {install_dir}...")
    if ext == "zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(install_dir)
    else:
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(install_dir)

    # Locate binary
    candidates = list(install_dir.rglob("orhun*"))
    bin_dir = None
    for cand in candidates:
        if cand.is_file() and cand.stem in ("orhun", "orhun_release"):
            # Set executable permission on Unix
            if os.name != "nt":
                cand.chmod(cand.stat().st_mode | 0o755)
            # If named orhun_release, ensure an 'orhun' shim or copy exists
            if cand.stem == "orhun_release":
                alias_name = "orhun.exe" if os.name == "nt" else "orhun"
                alias_path = cand.parent / alias_name
                if not alias_path.exists():
                    shutil.copy2(cand, alias_path)
            bin_dir = cand.parent
            break

    if not bin_dir:
        # Check standard layout
        for sub in (install_dir / "bin", install_dir):
            if sub.exists():
                bin_dir = sub
                break

    if not bin_dir:
        error(f"Could not locate Orhun executable inside {install_dir}")
        return 1

    add_to_path(bin_dir)
    set_output("orhun-version", version)
    set_output("orhun-path", str(bin_dir))

    # Verify installation
    cmd_name = "orhun.exe" if os.name == "nt" else "orhun"
    exe_path = bin_dir / cmd_name
    if exe_path.exists():
        proc = subprocess.run([str(exe_path), "surum"], capture_output=True, text=True)
        log(f"Verified: {proc.stdout.strip() or proc.stderr.strip()}")

    log(f"Successfully installed Orhun v{version}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
