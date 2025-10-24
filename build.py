#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys


# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def load_config(path):
    """Load and validate the JSON configuration."""
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
    """Recursively expand placeholders like $AppName or $Icon in strings, lists, and dicts."""
    if depth > 10:
        return value  # Prevent recursion loops

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


# ------------------------------------------------------------
# Safe cleanup utilities
# ------------------------------------------------------------

def remove_folder(folder_path):
    """Delete a folder if it exists."""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path, ignore_errors=True)
        print(f"🧹 Removed folder: {folder_path}")


def remove_pycache_folders(base_dir):
    """Recursively remove all __pycache__ folders under base_dir."""
    for root, dirs, _ in os.walk(base_dir):
        for d in dirs:
            if d == "__pycache__":
                folder = os.path.join(root, d)
                shutil.rmtree(folder, ignore_errors=True)
                print(f"🧹 Removed folder: {folder}")


def remove_spec_files(base_dir):
    """Recursively remove .spec files under base_dir."""
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".spec"):
                os.remove(os.path.join(root, f))
                print(f"🧹 Removed file: {os.path.join(root, f)}")


def clean_build_artifacts(app_dir):
    """
    Remove build/, dist/, __pycache__, and .spec files
    inside the application directory ONLY (never touches project root).
    """
    print("\n🧹 Performing post-build cleanup (safe mode)...\n")

    # Remove build/dist folders inside the application folder
    for path in ["build", "dist"]:
        remove_folder(os.path.join(app_dir, path))

    # Remove .spec files in the app folder
    remove_spec_files(app_dir)

    # Remove __pycache__ folders inside the app folder
    remove_pycache_folders(app_dir)

    print("✅ Post-build cleanup complete (root untouched).\n")


# ------------------------------------------------------------
# Build helpers
# ------------------------------------------------------------

def run_pyinstaller(app_name, py_args, app_dir, project_root, icon_path=None, verbose=False):
    """Run PyInstaller from app directory, with optional verbose output."""
    print(f"🚀 Building {app_name} with PyInstaller from {app_dir}\n")

    if icon_path:
        icon_full = os.path.join(project_root, os.path.basename(icon_path))
        if not os.path.exists(icon_full):
            print(f"❌ Icon not found: {icon_full}")
            sys.exit(1)

        # Replace --icon argument with the correct full path
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

    command = ["pyinstaller"] + py_args + ["--distpath", ".", "--workpath", "build"]
    print(f"⚙️ Running PyInstaller... {'(verbose)' if verbose else '(silent)'}")

    try:
        subprocess.run(
            command,
            cwd=app_dir,
            check=True,
            stdout=None if verbose else subprocess.DEVNULL,
            stderr=None if verbose else subprocess.DEVNULL
        )
        exe_path = os.path.join(app_dir, f"{app_name}.exe")
        if os.path.exists(exe_path):
            shutil.move(exe_path, project_root)
        print(f"✅ PyInstaller build complete: .\\{app_name}.exe\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed with exit code {e.returncode}")
        if not verbose:
            print("💡 Tip: Run with --verbose to see full PyInstaller output.")
        sys.exit(e.returncode)


def update_inno_setup_version(iss_path, version):
    """Update #define MyAppVersion in the .iss file."""
    print(f"⚙️ Updating version in Inno Setup script: {iss_path}")
    with open(iss_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("#define MyAppVersion"):
            lines[i] = f'#define MyAppVersion "{version}"\n'
            updated = True
            break
    if not updated:
        lines.insert(0, f'#define MyAppVersion "{version}"\n')

    with open(iss_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"✅ Updated version to {version}\n")


def run_inno_setup(app_name, version, project_root, verbose=False):
    """Run Inno Setup silently or verbose, move installer, delete standalone exe."""
    iss_path = os.path.join(project_root, "build", "windows", f"{app_name}.iss")
    if not os.path.exists(iss_path):
        print(f"ℹ️ No Inno Setup script found at {iss_path}. Skipping installer build.\n")
        return

    update_inno_setup_version(iss_path, version)
    print(f"📦 Running Inno Setup Compiler... {'(verbose)' if verbose else '(silent)'}")

    try:
        subprocess.run(
            ["iscc", iss_path],
            check=True,
            stdout=None if verbose else subprocess.DEVNULL,
            stderr=None if verbose else subprocess.DEVNULL
        )
        print("✅ Inno Setup installer built successfully.\n")

        # Move setup.exe to project root
        output_dir = os.path.dirname(iss_path)
        setup_exe = None
        for file in os.listdir(output_dir):
            if file.lower().endswith(".exe") and "setup" in file.lower():
                setup_exe = os.path.join(output_dir, file)
                break

        if setup_exe and os.path.exists(setup_exe):
            dest_exe = os.path.join(project_root, os.path.basename(setup_exe))
            shutil.move(setup_exe, dest_exe)
            print(f"📦 Moved installer to project root: {dest_exe}")

        # Always delete standalone PyInstaller exe after Inno completes
        standalone_exe = os.path.join(project_root, f"{app_name}.exe")
        if os.path.exists(standalone_exe):
            os.remove(standalone_exe)
            print(f"🗑️ Deleted standalone executable: {standalone_exe}")

    except FileNotFoundError:
        print("⚠️ iscc.exe not found. Please ensure Inno Setup is installed and in PATH.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Inno Setup failed with exit code {e.returncode}")
        if not verbose:
            print("💡 Tip: Run with --verbose to see full Inno Setup output.")


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build an app using PyInstaller and optionally Inno Setup.")
    parser.add_argument(
        "-c", "--config",
        default="build.json",
        help="Path to JSON config file (default: build.json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full PyInstaller and Inno Setup output"
    )
    args = parser.parse_args()

    # Load and expand placeholders fully
    config_raw = load_config(args.config)
    config = expand_placeholders_recursive(config_raw, config_raw)

    app_name = config["AppName"]
    version = config.get("Version", "1.0.0.0")
    icon_path = config.get("Icon")
    py_args = config["pyinstaller"]

    project_root = os.getcwd()
    app_dir = os.path.join(project_root, app_name)

    if not os.path.exists(app_dir):
        print(f"❌ Application directory not found: {app_dir}")
        sys.exit(1)

    # Run build steps
    run_pyinstaller(app_name, py_args, app_dir, project_root, icon_path, args.verbose)
    run_inno_setup(app_name, version, project_root, args.verbose)

    # Final cleanup
    clean_build_artifacts(app_dir)


if __name__ == "__main__":
    main()
