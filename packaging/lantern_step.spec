# PyInstaller spec for Lantern STEP (onedir). Build on each target OS:
#   python -m PyInstaller --noconfirm --clean packaging/lantern_step.spec
import os
import sys

from PyInstaller.utils.hooks import collect_all

# SPECPATH is injected by PyInstaller; resolve paths relative to the repo root.
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
ENTRY = os.path.join(SRC, "lantern_step", "__main__.py")

datas, binaries, hiddenimports = [], [], []
# Collect the heavy native packages and their data files / dynamic libs.
for pkg in ("OCP", "cadquery", "matplotlib", "vtkmodules"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        # vtkmodules may be absent depending on the cadquery build; skip if so.
        pass

a = Analysis(
    [ENTRY],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LanternStep",
    console=False,          # windowed app (no console)
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="LanternStep",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LanternStep.app",
        bundle_identifier="com.chrisbetters.lanternstep",
    )
