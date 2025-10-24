# 🌦️ TrayWeatherApp

A lightweight **system tray weather monitor** for Windows built with **Python 3.11+** and **PyQt6**.  
TrayWeatherApp provides real-time weather updates, quick forecasts, and customizable themes — all from your Windows tray.

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

---

## 📂 Project Structure

```
TrayWeatherApp/
├── build.py                 # Python build automation script
├── build.json               # build configuration file
│
├── TrayWeatherApp/
│   ├── __init__.py
│   ├── main.py              # main entry point (used by PyInstaller)
│   ├── app.py               # QApplication + system tray logic
│   ├── weather_api.py       # handles API requests and responses
│   ├── theme.py             # handles theme management
│   ├── config_utils.py      # configuration file management
│   ├── windows.py           # UI logic and window behavior
│   └── icons/               # weather and UI icons
│
├── build/
│   └── windows/
│       └── TrayWeatherApp.iss    # Inno Setup installer script
│
├── release/
│   └── windows/
│       └── TrayWeatherApp-Install.exe  # optional prebuilt installer
│
├── themes/                  # optional external theme files
│   ├── Dark.zip
│   ├── Light.zip
│   └── Beach.zip
│
├── TrayWeatherApp.ico       # app icon
├── requirements.txt         # dependency list
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

Run directly from source (development mode):

**Option 1 (recommended):**
```bash
python -m TrayWeatherApp
```

**Option 2:**
```bash
python TrayWeatherApp/main.py
```

---

## 🧰 Building the Executable (Windows)

To package **TrayWeatherApp** into a standalone Windows EXE, use the `build.py` script.

### Prerequisites
- Python 3.10+
- PyInstaller (installed from `requirements.txt`)
- (Optional) Inno Setup for building an installer:

  👉 [Download Inno Setup](https://jrsoftware.org/isinfo.php)

If Inno Setup isn’t installed, `build.py` will still produce a standalone EXE file.

---

## 🧩 Build JSON: `build.json`

The `build.json` defines how your EXE is packaged with PyInstaller:

```json
{
  "AppName": "TrayWeatherApp",
  "Version": "2.1.4",
  "Icon": "$AppName.ico",
  "pyinstaller": [
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--add-data", "$AppName\\icons;icons",
    "--name", "$AppName",
    "--icon", "$Icon",
    "main.py"
  ]
}
```

---

## 🛠️ Build Script: `build.py`

Automates the full build and packaging process.

Run this from the project root:
```bash
python build.py
```

### 🧾 What It Does
1. Reads `build.json` and expands `$AppName` and `$Icon` placeholders  
2. Runs **PyInstaller** with the provided arguments  
3. Moves the built EXE to the project root  
4. Runs **Inno Setup** (if available):  
   ```
   build\windows\TrayWeatherApp.iss
   ```
5. If Inno Setup completes successfully:  
   - Deletes the standalone EXE file from the root  
   - Moves the generated installer to the root  
6. If Inno Setup fails or isn’t found, the standalone EXE remains  
7. Performs post-build cleanup — removes:
   - `build/`
   - `dist/`
   - `.spec` files
   - `__pycache__/`

✅ **Notes**
- The final installer or EXE appears in your **project root**
- No root-level folders (like `.venv` or `build/`) are ever deleted
- Logs and configuration are stored in:
  ```
  C:\Users\<YourName>\.TrayWeatherApp\
  ```

---

## ⚙️ Configuration File

TrayWeatherApp saves user settings in a JSON file:
```json
{
  "cities": ["New York"],
  "units": "imperial",
  "theme": "Carbon Fiber",
  "window_pos": [800, 600],
  "window_size": [1200, 500],
  "time_format_24h": false,
  "debug": false
}
```

You can safely delete this file to reset the app’s settings.

---

## 💡 Building Tips

- Always run the build command from the **project root**
- Ensure your `.ico` file exists in the root (e.g., `TrayWeatherApp.ico`)
- Keep your theme files outside the executable for easy swapping
- If debugging build issues, run:
  ```bash
  python build.py --verbose
  ```
- You can modify `build.json` to add extra PyInstaller options as needed

---

## ☀️ Summary

| Action | Command |
|--------|----------|
| 🧪 Run app from source | `python -m TrayWeatherApp` |
| 🏗️ Build standalone EXE | `python build.py` |
| 🧱 Build with full logs | `python build.py --verbose` |
| 💾 Output | EXE or installer saved in project root |
| 🧹 Cleanup | Automatic (safe mode, no root deletion) |
