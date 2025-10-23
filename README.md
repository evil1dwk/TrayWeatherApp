# TrayWeatherApp — Modular Full Version

This package contains the full unaltered logic of your TrayWeatherApp split into modules.

---

## 🚀 Running the App (Development Mode)

To run directly from source:

```bash
python -m TrayWeatherApp
```

This launches the tray-based weather app using your system Python installation.  
Themes should be located in the `themes/` folder beside your project root.

---

## ⚙️ Building the Executable (Windows)

To package TrayWeatherApp into a standalone Windows `.exe`, use the PowerShell build script.

### Prerequisites
- **Python 3.10+**
- **PyInstaller** installed:
  ```bash
  pip install pyinstaller
  ```
- (Optional) **Inno Setup** if you want to build an installer:
  [Download Inno Setup](https://jrsoftware.org/isinfo.php)

---

## 🧱 Build Script: `build.ps1`

The `build.ps1` script automates the entire packaging process.

Run this from **PowerShell** at the project root:
```powershell
.uild.ps1 -AppName TrayWeatherApp
```

### 🧩 What It Does
1. **Detects project paths** automatically — no hardcoding required.
2. **Cleans** old `build/`, `dist/`, and `.spec` files.
3. Runs **PyInstaller** with:
   ```powershell
   pyinstaller --noconfirm --onefile --windowed --name TrayWeatherApp --icon ..\TrayWeatherApp.ico main.py
   ```
4. **Moves** the finished EXE from  
   `TrayWeatherApp\dist\TrayWeatherApp.exe` → `C:\Projects\TrayWeatherApp\TrayWeatherApp.exe`
5. **Deletes** leftover build folders for a clean result.
6. **Returns** to the project root folder.
7. **Runs Inno Setup (ISCC)** automatically to build your Windows installer:
   ```powershell
   ISCC.exe .\TrayWeatherApp.iss
   ```
   (If you have `TrayWeatherApp.iss` present and `ISCC.exe` installed.)

---

## 📁 Folder Layout

```
C:\Projects\TrayWeatherApp\
│
├── TrayWeatherApp.exe          ← final compiled app
├── TrayWeatherApp.ico          ← app icon
├── TrayWeatherApp.iss          ← optional Inno Setup script
├── themes\                     ← external themes (not bundled)
│   ├── Dark.zip
│   ├── Light.zip
│   └── Beach.zip
└── TrayWeatherApp\             ← Python source package
    ├── main.py
    ├── app.py
    ├── windows.py
    ├── theme.py
    ├── config_utils.py
    ├── ...
```

---

## 🧩 Notes

- The resulting EXE is **portable** and reads themes from the external `themes` folder.
- You can adjust the icon path or app name by editing the PowerShell script.
- If `ISCC.exe` isn’t found, the script will warn you but still complete the EXE build.

---

### Example Output (Console)
```
========================================
   Building TrayWeatherApp Executable
========================================
[INFO] Running PyInstaller...
[INFO] Moving TrayWeatherApp.exe to root directory...
[INFO] Cleaning up build and dist folders...
[INFO] Running Inno Setup Compiler...
[SUCCESS] Build complete!
Final EXE location:
   C:\Projects\TrayWeatherApp\TrayWeatherApp.exe
========================================
```

---

This `build.ps1` script fully automates building, cleaning, and packaging TrayWeatherApp.
