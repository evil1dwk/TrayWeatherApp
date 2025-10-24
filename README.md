# 🌦️ TrayWeatherApp

A lightweight **system tray weather monitor** for Windows and Linux built with **Python 3.11+** and **PyQt6**.  
TrayWeatherApp provides real-time weather updates, quick forecasts, and customizable themes — all from your system tray.

---

## 🧭 Features

- 🌡️ **Live weather data** for multiple cities  
- 🎨 **Customizable themes** (Dark, Light, Beach, etc.)  
- ⚙️ **Settings persistence** — city, units, theme, and window layout are saved  
- 📍 **Tray icon controls** — right-click for menu options:
  - *Refresh Weather*
  - *Change City*
  - *Switch Theme*
  - *Quit*
- 💾 **Local configuration** saved under your user profile
- 🖥️ **Cross-platform support** — works on both Windows and Linux

---

## 📂 Project Structure

```
TrayWeatherApp/
├── build.py                       # cross-platform build automation script
├── build/
│   ├── windows/
│   │   ├── build.json              # Windows build configuration
│   │   └── TrayWeatherApp.iss      # optional Inno Setup installer script
│   └── linux/
│       └── build.json              # Linux build configuration
│
├── releases/
│   ├── windows/                    # built executables (Windows)
│   └── linux/                      # built executables (Linux)
│
├── TrayWeatherApp/
│   ├── __init__.py
│   ├── main.py                     # main entry point (used by PyInstaller)
│   ├── app.py                      # QApplication + system tray logic
│   ├── weather_api.py              # handles API requests and responses
│   ├── theme.py                    # theme management
│   ├── config_utils.py             # configuration management
│   ├── windows.py                  # UI logic and window behavior
│   └── icons/                      # weather and UI icons
│
├── themes/                         # optional external theme files
│   ├── Dark.zip
│   ├── Light.zip
│   └── Beach.zip
│
├── TrayWeatherApp.ico              # app icon
├── requirements.txt                # dependency list
└── README.md
```

---

## ⚙️ Requirements

- Python **3.11+**
- [PyQt6](https://pypi.org/project/PyQt6/)
- [requests](https://pypi.org/project/requests/)
- [PyInstaller](https://pypi.org/project/pyinstaller/)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## ▶️ Running in Development

Run directly from source:

```bash
python -m TrayWeatherApp
```
or
```bash
python TrayWeatherApp/main.py
```

---

## 🧰 Building the Executable (Cross-Platform)

To package **TrayWeatherApp** into a standalone executable, use the `build.py` script.

### Prerequisites

- Python 3.10+  
- PyInstaller (installed via `requirements.txt`)  
- *(Windows only)* Inno Setup for building an installer:  
  [Download Inno Setup](https://jrsoftware.org/isinfo.php)

If Inno Setup isn’t installed, a standalone executable will still be created.

---

## 🧩 Build Config Files

There are now **platform-specific** build configuration files:

- **Windows:** `build/windows/build.json`
- **Linux:** `build/linux/build.json`

Example `build.json`:

```json
{
  "AppName": "TrayWeatherApp",
  "Version": "2.1.4",
  "Icon": "$AppName.ico",
  "pyinstaller": [
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--add-data", "$AppName/icons;icons",
    "--name", "$AppName",
    "--icon", "$Icon",
    "main.py"
  ]
}
```

---

## 🛠️ Build Script: `build.py`

Automates the entire build and packaging process.

Run this from the project root:
```bash
python build.py
```

### 🧾 What It Does

1. Detects your OS and loads the proper build configuration file:  
   - `build/windows/build.json` on Windows  
   - `build/linux/build.json` on Linux  
2. Runs **PyInstaller** with the specified parameters.  
3. Outputs the executable to:  
   - `releases/windows/` on Windows  
   - `releases/linux/` on Linux  
4. *(Windows only)* Runs **Inno Setup** if available:  
   ```
   build\windows\TrayWeatherApp.iss
   ```  
5. If Inno Setup completes successfully:  
   - Deletes the standalone executable from `releases/windows`  
   - Keeps only the generated installer there  
6. If Inno Setup fails or isn’t found, the standalone executable remains in `releases/windows`.  
7. Performs post-build cleanup — removes:  
   - `build/`  
   - `dist/`  
   - `.spec` files  
   - `__pycache__/` folders

✅ **Notes**
- The final installer or executable appears in the **`releases/<os>/`** folder.  
- No project root folders are ever deleted.  
- Configuration and logs are stored in:  
  ```
  C:\Users\<YourName>\.TrayWeatherApp\  (Windows)
  ~/.TrayWeatherApp/                       (Linux)
  ```

---

## ⚙️ Configuration File

TrayWeatherApp saves user settings in a JSON file:
```json
{
  "cities": ["New York"],
  "units": "imperial",
  "window_pos": [722, 575],
  "window_size": [1195, 425],
  "debug": false,
  "time_format_24h": false,
  "theme": "Dark"
}
```
You can delete this file to reset settings.

---

## 💡 Building Tips

- Always run `python build.py` from the **project root**
- Ensure the `.ico` file exists in the root (e.g., `TrayWeatherApp.ico`)
- Keep your theme files outside the executable for easy swapping
- To debug build issues:
  ```bash
  python build.py --verbose
  ```
- You can modify `build.json` to add or adjust PyInstaller options

---

## ☀️ Summary

| Action | Command |
|--------|----------|
| 🧪 Run app from source | `python -m TrayWeatherApp` |
| 🏗️ Build standalone executable | `python build.py` |
| 🧱 Build with full logs | `python build.py --verbose` |
| 💾 Output | `releases/<os>/` (windows or linux) |
| 🧹 Cleanup | Automatic, safe (no root deletion) |
