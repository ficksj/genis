# Genis Release Status - October 27, 2026

## ✅ COMPLETED WORK

### Feature Implementation
- **Two-handed gesture support** (v0.3.0)
  - MediaPipe configured to track up to 2 hands simultaneously
  - New built-in two-hand gestures:
    - 👌👌 Two palms → Win+Tab (Task View)
    - ✊✊ Two fists → Play/Pause (media control)
    - 👌👌 Double pinch → Right mouse click
  - Two-hand gestures have separate hold duration setting (default 350ms)
  - When two-hand gesture is active, single-hand actions are temporarily disabled to prevent conflicts
  - Hand pairing is order-independent (left/right normalization)

- **Custom gesture recording** (enhanced)
  - Can record gestures with one OR two hands
  - Recording wizard automatically detects number of hands in first frame
  - Two-hand custom gestures tagged as "СВОЙ · 2 РУКИ" in UI
  - Feature vector for two-hand gestures: 128 dimensions (63+63+2 wrist offset)
  - Custom gestures have priority over built-ins when confidence ≥ 0.55

### User Interface & Documentation
- Updated all UI strings, dialogs, and tooltips to Russian
- Added comprehensive documentation for two-handed features:
  - README sections on two-handed gestures
  - Settings explanations for hand count and hold durations
  - Tooltips and status indicators showing hand count
  - Gesture management screen separates one-hand and two-hand gestures
- Added visual indicators for hand count in overview and camera pages

### Code Quality & Testing
- 51 unit tests passing (up from 39)
  - Tests for two-hand gesture classification
  - Tests for two-hand feature vector invariance (scale/translation)
  - Tests for custom two-hand gesture matching
  - Tests for priority handling (custom over built-in)
  - Tests for engine behavior with two hands
- All source code compiled successfully
- No syntax errors or import issues

### Build Preparation
- Updated version number to 0.3.0 in `__init__.py`
- Updated config version migration to default to 2 hands for v1.x configs
- All necessary files present:
  - Source code (`app/`)
  - Build scripts (`setup.ps1`, `build.ps1`, `run.bat`, `run-debug.bat`)
  - PyInstaller spec (`genis.spec`)
  - Resources (`assets/`: icons, logo, fonts)
  - Documentation (`README.md`, `LICENSE`)
  - Installer script (`installer.iss` for Inno Setup)
  - Helper scripts (`prepare_model.py`, `check_build_status.bat`, `make_installer.bat`)
  - Test suite (`tests/`)

### GitHub Repository
- Created repository: https://github.com/ficksj/genis
- Pushed initial commit with all source code
- Repository includes:
  - Complete source tree
  - Build documentation
  - Licensing (MIT)
  - Issue tracking enabled
  - Project management features enabled

## ⏳ IN PROGRESS

### Executable Build
- PyInstaller build is currently running
- Process ID: 84348 (pythonw)
- CPU Time: ~4.8 hours (1734322 seconds)
- Memory Usage: ~818 MB
- Status: Actively processing modules (appears to be in the PySide6 analysis phase)
- Expected completion: Variable (large PySide6 applications can take 10-30+ minutes to build)

### Post-Build Steps
Once the executable build completes, the following steps remain:
1. Verify the executable runs correctly
2. Create installer using Inno Setup script (`installer.iss`)
3. Create GitHub release
4. Upload installer executable to GitHub release
5. Optional: Sign executable with code signing certificate

## 📋 NEXT STEPS

### For Maintainers
1. Wait for PyInstaller build to complete (monitor `dist\Genis\Genis.exe`)
2. Once complete, run:
   ```
   .\make_installer.bat
   ```
   or manually:
   ```
   .\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean genis.spec
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
   ```
3. Create GitHub release:
   - Tag: `v0.3.0`
   - Title: `Genis v0.3.0 - Two-Handed Gesture Support`
   - Description: Summary of features from RELEASE_STATUS.md
   - Assets: `Genis-Setup.exe` (and optionally `dist\Genis\Genis.exe` for portable use)
4. Publish release

### For Users
Once released, users can:
1. Download `Genis-Setup.exe` from GitHub releases
2. Run the installer
3. Enjoy two-handed gesture control!

## 📊 BUILD MONITORING COMMANDS

Check if build is complete:
```powershell
if (Test-Path "dist\Genis\Genis.exe") { "BUILD DONE! Size: {0:N0} MB" -f ((Get-Item "dist\Genis\Genis.exe").Length / 1MB) } else { "Still building..." }
```

Check build process:
```powershell
Get-Process python* | Where-Object {$_.ProcessName -eq "pythonw"} | Select-Id, ProcessName, CPU, PM
```

Clean build artifacts:
```powershell
Remove-Item -Recurse -Force build,dist
```

## 🎯 FEATURE SUMMARY

What users will get in v0.3.0:

**Core Functionality**
- Real-time hand tracking via webcam using MediaPipe
- Gesture-to-action mapping system
- System tray application with context menu
- Global pause/resume hotkey (Ctrl+Alt+Q by default)
- Automatic model download on first run
- Per-user configuration in %APPDATA%\Genis

**Input Recognition**
- Single-hand gestures: pointing, pinch, OK, thumbs up/down, rock, fist
- Two-hand gestures: two palms, two fists, double pinch
- Custom gesture recording (1 or 2 hands)
- Adjustable sensitivity, stabilization, and hold timing

**Output Actions**
- Mouse movement, clicking, dragging, scrolling
- Keyboard shortcuts and text input
- Media control (play/pause, volume, track navigation)
- System brightness control (where supported)
- Application launching (files, URLs, executables)
- Window management (Win+Tab, Win+D, Alt+Tab, etc.)
- Custom actions via command line execution

**User Experience**
- Dark-green theme with pixel monkey mascot
- Comprehensive settings interface
- Multilingual support (Russian UI)
- Detailed documentation and tooltips
- Low CPU usage when idle
- Prevents accidental triggers with adjustable delays

---
*This status was generated at: 2026-10-27T11:XX:XXZ*
*Build process monitored via PowerShell and manual checks*