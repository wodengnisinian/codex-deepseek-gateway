# Build Guide

## Prerequisites

- Python 3.11+
- pip

## Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run from Source

```powershell
python server.py
```

## Build EXE with PyInstaller

```powershell
pyinstaller CDGLauncher.spec
```

The output will be in `dist/CDG Launcher.exe`.

## CDGLauncher.spec Notes

- Bundles PySide6 GUI
- Includes app_icon.ico for the executable icon
- Hidden imports for httpx, socksio, and adapter modules

## Testing

```powershell
# Unit tests
python -m unittest discover -s tests

# Integration tests (gateway must be running)
.\scripts\test_health.ps1
.\scripts\test_models.ps1
```