# Lantern STEP Generator

A GUI application for generating STEP files from fiber diameter measurements.

## Features

- Load fiber measurement data from Excel files
- Visualize raw measurement data
- Interactive range selection with real-time visual updates
- Automatically detect start and end points
- Apply cubic spline smoothing to create a smooth profile
- Add cylindrical extension for mounting
- Generate and export STEP files for 3D printing or machining
- Preview the model profile before generating

## Install

```bash
pip install -e .          # runtime + GUI + CLI
pip install -e ".[dev]"   # + pytest/flake8/mypy
```

## Use

- GUI: `lantern-step`  (or `python -m lantern_step`)
- CLI: `lantern-step-cli INPUT.xlsx -o OUT.step --start 5 --end 65 --final-d 1.2 --ext 13 --ref-d 1.2 0.5 --ref-z 10 30`
- Library:

```python
from lantern_step import load_profile, build_taper_model, make_solid, export_step, ModelParams
from lantern_step import build_reference_bodies

profile = load_profile("PROFILE.xlsx")
model = build_taper_model(profile, ModelParams(5, 65, 1.2, 13))
solid = make_solid(model)
bodies, notes = build_reference_bodies(model, diameters=[1.2], positions=[10, 30])
export_step(solid, bodies, "OUT.step")
```

## Build standalone apps

- macOS: `bash packaging/build_macos.sh`  -> `dist/LanternStep.app`
- Windows: `packaging\build_windows.bat`  -> `dist\LanternStep\LanternStep.exe`

## File Format

The input Excel file should contain fiber measurement data with the following columns:
- 'Left Z Motor - Bottom Camera': Z-position measurements (μm)
- 'Fiber Diameter - Bottom Camera': X-diameter measurements (μm)
- 'Fiber Diameter - Side Camera': Y-diameter measurements (μm)

## About

This application was developed to facilitate the creation of tapered cylinder models from fiber diameter measurements for lantern fabrication.
