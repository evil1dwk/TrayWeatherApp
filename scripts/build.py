#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Direct script invocation puts scripts/, rather than the checkout root, on sys.path.
sys.path.insert(0, str(PROJECT_ROOT))
from TrayWeatherApp._version import __version__

# ---------- Read the build.json ----------
def load_config(path):
    if not os.path.exists(path):
        print(f"❌ Config file not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if "AppName" not in config or "pyinstaller" not in config:
        print("❌ JSON must contain 'AppName' and 'pyinstaller' fields.")
        sys.exit(1)
    return config

def expand_placeholders_recursive(value, config, depth=0):
    if depth > 10:
        return value
    if isinstance(value, str):
        changed = True
        result = value
        while changed:
            changed = False
            for k, v in config.items():
                if isinstance(v, str) and f"${k}" in result:
                    result = result.replace(f"${k}", v)
                    changed = True
        return result
    elif isinstance(value, list):
        return [expand_placeholders_recursive(v, config, depth + 1) for v in value]
    elif isinstance(value, dict):
        return {k: expand_placeholders_recursive(v, config, depth + 1) for k, v in value.items()}
    else:
        return value

# ---------- Fix for PyInstaller add-data paths ----------
def fix_add_data_paths(py_args):
    fixed_args = []
    i = 0
    while i < len(py_args):
        arg = py_args[i]
        if arg == "--add-data" and i + 1 < len(py_args):
            val = py_args[i + 1]
            if os.name == "nt":
                val = val.replace(":", ";")
                fixed_args.append(f"--add-data={val}")
            else:
                val = val.replace(";", ":")
                fixed_args.append(f"--add-data={val}")
            i += 2
        else:
            fixed_args.append(arg)
            i += 1
    return fixed_args

# ---------- Cleanup utilities ----------
def remove_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path, ignore_errors=True)
        print(f"🧹 Removed folder: {folder_path}")

def remove_pycache_folders(base_dir):
    for root, dirs, _ in os.walk(base_dir):
        for d in dirs:
            if d == "__pycache__":
                folder = os.path.join(root, d)
                shutil.rmtree(folder, ignore_errors=True)
                print(f"🧹 Removed folder: {folder}")

def remove_spec_files(base_dir):
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".spec"):
                os.remove(os.path.join(root, f))
                print(f"🧹 Removed file: {os.path.join(root, f)}")

def clean_build_artifacts(app_dir):
    print("🧹 Performing post-build cleanup...")
    for path in ["build", "dist"]:
        remove_folder(os.path.join(app_dir, path))
    remove_spec_files(app_dir)
    remove_pycache_folders(app_dir)
    print("✅ Post-build cleanup complete.")

# ---------- Builders ----------
def run_pyinstaller(app_name, py_args, app_dir, project_root, icon_path=None, verbose=False):
    print(f"🚀 Building {app_name} with PyInstaller from {app_dir}")
    release_dir = os.path.join(project_root, "releases", "windows" if os.name == "nt" else "linux")
    os.makedirs(release_dir, exist_ok=True)

    if icon_path:
        icon_full = os.path.join(project_root, os.path.basename(icon_path))
        if not os.path.exists(icon_full):
            print(f"❌ Icon not found: {icon_full}")
            sys.exit(1)
        new_args = []
        skip_next = False
        for arg in py_args:
            if skip_next:
                skip_next = False
                continue
            if arg == "--icon":
                new_args.extend(["--icon", icon_full])
                skip_next = True
            else:
                new_args.append(arg)
        py_args = new_args
        print(f"💡 Using project root icon: {icon_full}")

    command = [sys.executable, "-m", "PyInstaller"] + py_args + ["--distpath", release_dir, "--workpath", os.path.join(project_root, ".build", "build"), "--specpath", os.path.join(project_root, ".build")]
    print(f"⚙️ Running PyInstaller... {'(verbose)' if verbose else '(silent)'}")
    try:
        subprocess.run(
            command,
            cwd=app_dir,
            check=True,
            stdout=None if verbose else subprocess.DEVNULL,
            stderr=None if verbose else subprocess.DEVNULL
        )
        print(f"✅ PyInstaller build complete: {release_dir}/{app_name}.exe")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed with exit code {e.returncode}")
        if not verbose:
            print("💡 Tip: Run with --verbose to see full PyInstaller output.")
        sys.exit(e.returncode)

def run_inno_setup(app_name, version, project_root, verbose=False):
    release_dir = os.path.join(project_root, "releases", "windows")
    iss_path = os.path.join(project_root, "build", "windows", f"{app_name}.iss")
    if not os.path.exists(iss_path):
        print(f"ℹ️ No Inno Setup script found at {iss_path}. Skipping installer build.")
        return

    print(f"📦 Running Inno Setup Compiler... {'(verbose)' if verbose else '(silent)'}")
    try:
        subprocess.run(
            ["iscc", f"/DMyAppVersion={version}", f"/O{release_dir}", iss_path],
            check=True,
            stdout=None if verbose else subprocess.DEVNULL,
            stderr=None if verbose else subprocess.DEVNULL
        )
        print("✅ Inno Setup installer built successfully.")
        standalone_exe = os.path.join(release_dir, f"{app_name}.exe")
        if os.path.exists(standalone_exe):
            os.remove(standalone_exe)
            print(f"🗑️ Deleted standalone executable: {standalone_exe}")
    except FileNotFoundError:
        print("⚠️ iscc.exe not found. Please ensure Inno Setup is installed and in PATH.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Inno Setup failed with exit code {e.returncode}")
        if not verbose:
            print("💡 Tip: Run with --verbose to see full Inno Setup output.")

# ---------- Main Entry ----------
def main():
    parser = argparse.ArgumentParser(description="Build an app using PyInstaller and optionally Inno Setup.")
    parser.add_argument("-c", "--config", default=None, help="Path to JSON config file (default depends on OS)")
    parser.add_argument("--verbose", action="store_true", help="Show full PyInstaller and Inno Setup output")
    args = parser.parse_args()

    if args.config:
        config_path = str(PROJECT_ROOT / args.config)
    else:
        config_path = os.path.join(PROJECT_ROOT, "build", "windows" if os.name == "nt" else "linux", "build.json")

    print(f"📄 Using config: {config_path}")
    config_raw = load_config(config_path)
    config_raw["Version"] = __version__
    config = expand_placeholders_recursive(config_raw, config_raw)

    app_name = config["AppName"]
    version = __version__
    icon_path = config.get("Icon")
    py_args = fix_add_data_paths(config["pyinstaller"])

    project_root = str(PROJECT_ROOT)
    app_dir = project_root
    if not os.path.exists(app_dir):
        print(f"❌ Application directory not found: {app_dir}")
        sys.exit(1)

    run_pyinstaller(app_name, py_args, app_dir, project_root, icon_path, args.verbose)

    if os.name == "nt":
        run_inno_setup(app_name, version, project_root, args.verbose)
    else:
        print("💡 Skipping Inno Setup — only runs on Windows.")

    clean_build_artifacts(os.path.join(project_root, ".build"))

if __name__ == "__main__":
    main()
