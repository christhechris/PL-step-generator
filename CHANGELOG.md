# Changelog

## v0.4.1 - 2026-06-17

### Fixed
- Frozen apps (PyInstaller) crashed on launch with `ImportError: attempted relative
  import with no known parent package` before showing any UI. The entry module
  `__main__.py` used a relative import (`from .gui import main`), which fails when
  PyInstaller runs it as a top-level script. Switched to an absolute import
  (`from lantern_step.gui import main`), which works both as the frozen entry point
  and via `python -m lantern_step`.

## v0.4.0 - 2026-06-16

### Changed
- Restructured into an installable `lantern_step` package (src layout) with a pure,
  testable `core` (no Qt), a `references` module, a PyQt5 GUI, and a headless CLI.
- GUI and notebook moved into the package / `examples/`; launch via `lantern-step`,
  `lantern-step-cli`, or `python -m lantern_step`.

### Added
- Headless CLI (`lantern-step-cli`) for batch generation.
- pytest suite covering the geometry pipeline and reference planes.
- PyInstaller build scripts for standalone macOS (`.app`) and Windows (`.exe`) apps.

## v0.3.0 - 2026-06-16

### Added
- Optional reference planes embedded in the STEP output. Specify stations by
  target diameter (the position where the taper reaches that diameter is solved
  from the profile) and/or by axial position z. Each is written as a flat
  circular surface body normal to the axis, bundled alongside the solid without
  modifying it. In CAD tools (e.g. SolidWorks) these import as surface bodies
  that can be converted to reference planes or used to section/mate.

### Fixed
- STEP files now export as a single watertight solid instead of occasionally
  importing as open surfaces (a hollow, one-end-capped cylinder) in CAD tools
  such as SolidWorks. The geometry is now built by revolving one closed
  profile (taper wall + cylinder extension + flat end caps) about the central
  axis, replacing the previous loft-of-circles + boolean-fuse-cylinder
  approach whose coincident-face union could silently leave separate shells.

### Changed
- Spline radii are floored at 1 µm before modeling to guard against cubic-spline
  overshoot producing non-physical (<= 0) radii and degenerate faces.

## v0.2.0 - 2025-04-30

### Added
- Interactive range selection with real-time plot updates
- Visual indicators for selected range on raw data plot
- Separate tabs for raw data and model preview
- Improved error handling for invalid inputs

### Changed
- Raw data plot now highlights the selected range with vertical boundary markers
- Automatically switch to relevant tab when making changes
- Improved documentation and code comments

## v0.1.0 - 2025-04-30

### Added
- Initial GUI implementation
- Excel file loading and visualization
- STEP file generation
- Basic parameter controls
- Model visualization
- Data smoothing with cubic splines
- Automatic transition to standard diameter
- Cylindrical extension generation