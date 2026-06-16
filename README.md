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

## Installation

### Using pip

```bash
pip install -r requirements.txt
```

### Required Dependencies

- pandas: Data handling
- numpy: Numerical operations
- scipy: Spline interpolation
- matplotlib: Visualization
- cadquery: 3D modeling
- PyQt5: GUI framework

## Usage

1. Run the application:
   ```bash
   python lantern_step_gui.py
   ```

2. Click "Browse" to select an Excel file with fiber measurements
   - The file should contain columns: 'Left Z Motor - Bottom Camera', 'Fiber Diameter - Bottom Camera', 'Fiber Diameter - Side Camera'

3. The raw data will be automatically plotted and start/end distances set based on the data

4. Adjust parameters as needed:
   - Start Distance: Where to begin the model (mm)
   - End Distance: Where to end the model (mm)
   - Final Diameter: Diameter at the end of the taper (mm)
   - Extension Length: Length of the cylindrical extension (mm)

5. Click "Generate STEP File" to create and save the 3D model

## File Format

The input Excel file should contain fiber measurement data with the following columns:
- 'Left Z Motor - Bottom Camera': Z-position measurements (μm)
- 'Fiber Diameter - Bottom Camera': X-diameter measurements (μm)
- 'Fiber Diameter - Side Camera': Y-diameter measurements (μm)

## About

This application was developed to facilitate the creation of tapered cylinder models from fiber diameter measurements for lantern fabrication.