#!/usr/bin/env python3
"""Build standalone executables and release archives on Windows or Linux."""
import argparse
import json
from pathlib import Path
import platform as host_platform
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from TrayWeatherApp._version import __version__


def build_command(platform, config=None):
    if platform not in ("windows", "linux"):
        raise ValueError(f"Unsupported platform: {platform}")
    config_path = ROOT / config if config else ROOT / "packaging" / platform / "build.json"
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    command = [sys.executable, "-m", "PyInstaller", *settings["pyinstaller"],
               "--name", settings["AppName"],
               "--distpath", str(ROOT / "dist"),
               "--workpath", str(ROOT / "build" / platform),
               "--specpath", str(ROOT / "build"),
               "--paths", str(ROOT),
               "--add-data", str(ROOT / "TrayWeatherApp" / "themes") +
               (";" if platform == "windows" else ":") + "TrayWeatherApp/themes"]
    if platform == "windows":
        command += ["--icon", str(ROOT / "TrayWeatherApp.ico")]
    command.append(str(ROOT / "TrayWeatherApp" / "main.py"))
    return command


def normalized_architecture():
    arch = host_platform.machine().lower()
    return {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(arch, arch)


def package_release(platform, project_root=ROOT):
    if platform not in ("windows", "linux"):
        raise ValueError(f"Unsupported platform: {platform}")
    root = Path(project_root).resolve()
    output = root / "dist"
    binary = output / ("TrayWeatherApp.exe" if platform == "windows" else "TrayWeatherApp")
    if not binary.is_file():
        raise FileNotFoundError(f"Executable missing: {binary}")
    name = f"TrayWeatherApp-{__version__}-{platform}-{normalized_architecture()}"
    # Optional portable themes go beside the binary when the archive is extracted.
    files = [(binary, binary.name)]
    files += [(p, f"themes/{p.name}") for p in sorted((root / "themes").glob("*.zip"))]
    if platform == "windows":
        archive = output / f"{name}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for path, member in files:
                package.write(path, arcname=member)
    else:
        archive = output / f"{name}.tar.gz"
        with tarfile.open(archive, "w:gz") as package:
            for path, member in files:
                package.add(path, arcname=member)
    return archive


def main():
    parser = argparse.ArgumentParser(description="Build TrayWeatherApp on the current OS.")
    parser.add_argument("-c", "--config", help="Optional build JSON path (relative to the project root)")
    parser.add_argument("--verbose", action="store_true", help="Show full build output (default)")
    args = parser.parse_args()
    platform = {"win32": "windows", "linux": "linux"}.get(sys.platform)
    if platform is None:
        parser.error("Executable packaging is supported on Windows and Linux.")
    print(f"Building TrayWeatherApp {__version__} for {platform}")
    (ROOT / "build").mkdir(exist_ok=True)
    subprocess.run(build_command(platform, args.config), cwd=ROOT, check=True)
    print(f"Release archive: {package_release(platform)}")


if __name__ == "__main__":
    main()
