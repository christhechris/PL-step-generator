import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.interpolate import make_interp_spline
import cadquery as cq
from cadquery import exporters
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QGroupBox, QFormLayout, QMessageBox,
                             QTabWidget)
from PyQt5.QtCore import Qt


def parse_float_list(text):
    """Parse a comma/space separated list of floats, ignoring blank/invalid tokens."""
    vals = []
    for tok in text.replace(',', ' ').split():
        try:
            vals.append(float(tok))
        except ValueError:
            pass
    return vals


def solve_z_for_diameter(z_arr, r_arr, target_d):
    """Find axial positions where the local diameter crosses target_d (mm).

    Linearly interpolates between samples and returns a sorted, de-duplicated
    list of z values. Searching the tapered portion only keeps this
    well-defined (the constant-radius cylinder would otherwise match along its
    whole length).
    """
    target_r = target_d / 2.0
    g = np.asarray(r_arr) - target_r
    zs = []
    for i in range(len(g) - 1):
        a, b = g[i], g[i + 1]
        if a == 0.0:
            zs.append(float(z_arr[i]))
        elif a * b < 0:  # sign change -> a crossing lies between the samples
            t = a / (a - b)
            zs.append(float(z_arr[i] + t * (z_arr[i + 1] - z_arr[i])))
    if len(g) and g[-1] == 0.0:
        zs.append(float(z_arr[-1]))
    out = []
    for z in sorted(zs):
        if not out or abs(z - out[-1]) > 1e-3:  # collapse near-coincident crossings
            out.append(z)
    return out


def make_reference_disk(z, local_r):
    """A circular planar face (a free surface body) normal to the Z axis at z.

    Exported alongside the solid as a separate body (never fused), so the solid
    is unchanged. In CAD tools it imports as a surface you can turn into a
    reference plane or section/mate against. Sized a little larger than the
    local wall so it is easy to select.
    """
    margin = max(0.5, 0.25 * local_r)  # mm beyond the wall, for selectability
    disk_r = local_r + margin
    wire = cq.Wire.makeCircle(disk_r, cq.Vector(0, 0, z), cq.Vector(0, 0, 1))
    return cq.Face.makeFromWires(wire)


class LanternStepMaker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lantern STEP File Generator")
        self.setGeometry(100, 100, 1000, 800)
        
        # Initialize data attributes
        self.excel_file = None
        self.df = None
        self.solid_combined = None
        self.z_raw = None
        self.r_raw = None
        
        self.setup_ui()
    
    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Input/Output Files")
        file_layout = QFormLayout()
        
        # Input file
        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(browse_button)
        file_layout.addRow("Excel File:", input_layout)
        
        # Output file
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        save_button = QPushButton("Select")
        save_button.clicked.connect(self.select_save_path)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(save_button)
        file_layout.addRow("STEP File:", output_layout)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Parameters
        param_group = QGroupBox("Processing Parameters")
        param_layout = QFormLayout()
        
        self.start_distance = QLineEdit("1")
        self.start_distance.textChanged.connect(self.update_range_plot)
        param_layout.addRow("Start Distance (mm):", self.start_distance)
        
        self.end_distance = QLineEdit("60")
        self.end_distance.textChanged.connect(self.update_range_plot)
        param_layout.addRow("End Distance (mm):", self.end_distance)
        
        self.final_diameter = QLineEdit("1.75")
        param_layout.addRow("Final Diameter (mm):", self.final_diameter)
        
        self.extension_length = QLineEdit("13")
        param_layout.addRow("Extension Length (mm):", self.extension_length)

        # Optional reference geometry: flat disks normal to the taper axis,
        # embedded in the STEP as separate surface bodies (the solid is unchanged).
        self.ref_diameters = QLineEdit("")
        self.ref_diameters.setPlaceholderText("e.g. 1.2, 0.5  (blank = none)")
        param_layout.addRow("Ref. Plane @ Diameter (mm):", self.ref_diameters)

        self.ref_positions = QLineEdit("")
        self.ref_positions.setPlaceholderText("e.g. 10, 30  (blank = none)")
        param_layout.addRow("Ref. Plane @ Position Z (mm):", self.ref_positions)

        param_group.setLayout(param_layout)
        main_layout.addWidget(param_group)
        
        # Tab widget for visualization and output
        tab_widget = QTabWidget()
        
        # Raw data tab
        self.raw_plot_widget = QWidget()
        raw_plot_layout = QVBoxLayout()
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        raw_plot_layout.addWidget(self.canvas)
        self.raw_plot_widget.setLayout(raw_plot_layout)
        tab_widget.addTab(self.raw_plot_widget, "Raw Data")
        
        # Model tab
        self.model_widget = QWidget()
        model_layout = QVBoxLayout()
        self.model_figure = Figure(figsize=(8, 6))
        self.model_canvas = FigureCanvas(self.model_figure)
        model_layout.addWidget(self.model_canvas)
        self.model_widget.setLayout(model_layout)
        tab_widget.addTab(self.model_widget, "Model Preview")
        
        # Summary tab
        summary_widget = QWidget()
        summary_layout = QVBoxLayout()
        self.summary_text = QLabel("Generate a model to see the summary")
        summary_layout.addWidget(self.summary_text)
        summary_widget.setLayout(summary_layout)
        tab_widget.addTab(summary_widget, "Summary")
        
        main_layout.addWidget(tab_widget)
        
        # Process button
        process_layout = QHBoxLayout()
        process_button = QPushButton("Generate STEP File")
        process_button.setMinimumHeight(40)
        process_button.clicked.connect(self.process_data)
        process_layout.addWidget(process_button)
        main_layout.addLayout(process_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_file = file_path
            self.input_path.setText(file_path)
            
            # Auto-generate output path
            base_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            default_output = os.path.join(base_dir, f"{file_name}_model.step")
            self.output_path.setText(default_output)
            
            # Load the data and update the plot and parameters
            try:
                # Load the data
                self.df = pd.read_excel(self.excel_file, sheet_name=0)
                # Select relevant columns and drop missing values
                self.df = self.df[['Left Z Motor  - Bottom Camera', 
                              'Fiber Diameter - Bottom Camera', 
                              'Fiber Diameter - Side Camera']].dropna()
                self.df.columns = ['Z', 'Diameter_X', 'Diameter_Y']
                # Normalize Z so that it starts at 0 (µm)
                self.df['Z'] = self.df['Z'] - self.df['Z'].min()
                
                # Compute the average diameter and corresponding radius (in µm)
                self.df['Diameter'] = (self.df['Diameter_X'] + self.df['Diameter_Y']) / 2
                self.df['Radius'] = self.df['Diameter'] / 2
                
                # Convert units from µm to mm (1 µm = 1e-3 mm)
                self.z_raw = self.df['Z'].values * 1e-3     # Z in mm
                self.r_raw = self.df['Radius'].values * 1e-3  # Radius in mm
                
                # Set start and end distances based on the data
                start_val = self.z_raw.min()
                end_val = self.z_raw.max()
                self.start_distance.setText(f"{start_val:.2f}")
                self.end_distance.setText(f"{end_val:.2f}")
                
                # Plot the raw data with range indicators
                start_val = float(self.start_distance.text())
                end_val = float(self.end_distance.text())
                self.plot_raw_data(self.z_raw, self.r_raw, start_val, end_val)
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not load Excel file: {str(e)}")
                return
    
    def select_save_path(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save STEP File", "", "STEP Files (*.step)"
        )
        if file_path:
            if not file_path.lower().endswith('.step'):
                file_path += '.step'
            self.output_path.setText(file_path)
    
    def process_data(self):
        # Validate inputs
        if not self.excel_file:
            QMessageBox.warning(self, "Missing Input", "Please select an Excel file")
            return
        
        if not self.output_path.text():
            QMessageBox.warning(self, "Missing Output", "Please select an output path")
            return
        
        try:
            start_distance = float(self.start_distance.text())
            end_distance = float(self.end_distance.text())
            final_diameter = float(self.final_diameter.text())
            extension_length = float(self.extension_length.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Parameters must be numeric values")
            return
        
        try:
            # Step 1: Load and Process Data
            self.df = pd.read_excel(self.excel_file, sheet_name=0)
            # Select relevant columns and drop missing values
            self.df = self.df[['Left Z Motor  - Bottom Camera', 
                          'Fiber Diameter - Bottom Camera', 
                          'Fiber Diameter - Side Camera']].dropna()
            self.df.columns = ['Z', 'Diameter_X', 'Diameter_Y']
            # Normalize Z so that it starts at 0 (µm)
            self.df['Z'] = self.df['Z'] - self.df['Z'].min()
            
            # Compute the average diameter and corresponding radius (in µm)
            self.df['Diameter'] = (self.df['Diameter_X'] + self.df['Diameter_Y']) / 2
            self.df['Radius'] = self.df['Diameter'] / 2
            
            # Convert units from µm to mm (1 µm = 1e-3 mm)
            z_raw = self.df['Z'].values * 1e-3     # Z in mm
            r_raw = self.df['Radius'].values * 1e-3  # Radius in mm
            
            # Step 2: Apply Cubic Spline Smoothing
            spline = make_interp_spline(z_raw, r_raw, k=3)
            num_points = 100  # resolution of the smoothed profile
            z_smooth = np.linspace(z_raw.min(), z_raw.max(), num_points)
            r_smooth = spline(z_smooth)
            
            # Step 3: Define Model Range Based on Distance from Start
            # Filter the smoothed data based on the specified range
            mask = (z_smooth >= start_distance) & (z_smooth <= end_distance)
            z_model = z_smooth[mask]
            r_model = r_smooth[mask]
            
            # Step 4: Extrapolate Final Measurement with Intermediate Points
            # Use final_diameter parameter for the end diameter
            radius_final = final_diameter / 2
            
            # Use the last 10 mm of data for a linear fit to extrapolate
            if z_model[-1] - 1 < z_model[0]:
                idx = np.arange(len(z_model))
            else:
                idx = np.where(z_model >= (z_model[-1] - 1))[0]
            
            # Linear regression: r = m*z + b
            m, b = np.polyfit(z_model[idx], r_model[idx], 1)
            
            # Calculate the extrapolated Z position for the final radius
            if np.abs(m) < 1e-6:
                z_extrapolated = z_model[-1]
            else:
                z_extrapolated = (radius_final - b) / m
            z_extrapolated = max(z_extrapolated, z_model[-1])  # ensure it doesn't go backwards
            
            # Generate several intermediate points between the last measured point and the extrapolated point
            num_extrap_points = 100  # number of intermediate points
            z_extrap_points = np.linspace(z_model[-1], z_extrapolated, num_extrap_points + 1)[1:]  # skip duplicate
            r_extrap_points = np.linspace(r_model[-1], radius_final, num_extrap_points + 1)[1:]     # skip duplicate
            
            # Extend the model arrays with the extrapolation points
            z_model_extended = np.concatenate([z_model, z_extrap_points])
            r_model_extended = np.concatenate([r_model, r_extrap_points])

            # Guard against spline overshoot producing non-physical (<= 0) radii,
            # which would create degenerate wires/faces. Floor at 1 µm (1e-3 mm).
            r_model_extended = np.clip(r_model_extended, 1e-3, None)

            # Step 5: Build a single closed (radius, z) profile and revolve it.
            #
            # The whole part - tapered wall, constant-radius cylinder extension,
            # and the flat end caps - is described by ONE closed profile that is
            # revolved 360 degrees about the central (Z) axis. A surface of
            # revolution from a closed face is always a single watertight solid,
            # so this avoids the previous loft + boolean-fuse approach whose
            # coincident-face union could silently fail and leave open shells
            # (which import as surfaces, not a solid).
            #
            # Profile is drawn on the XZ workplane: local (x, y) = (radius, z).
            z_cyl_end = z_extrapolated + extension_length  # end of cylinder (mm)

            profile_pts = [(0.0, z_model_extended[0])]  # on axis -> flat start cap
            # Tapered wall (measured + extrapolated transition), in axis order
            profile_pts += [
                (float(r), float(z))
                for z, r in zip(z_model_extended, r_model_extended)
            ]
            profile_pts.append((radius_final, z_cyl_end))  # constant-radius cylinder wall
            profile_pts.append((0.0, z_cyl_end))           # flat end cap back to axis

            # polyline().close() returns to the first point along the axis (radius 0),
            # closing the profile. Revolve about the Z axis (local Y of the XZ plane).
            self.solid_combined = (
                cq.Workplane("XZ")
                .polyline(profile_pts)
                .close()
                .revolve(360, (0, 0, 0), (0, 1, 0))
                .val()
            )

            # Step 6: Optional reference geometry (flat disks normal to the axis)
            # Each disk is a separate surface body bundled with the solid; the
            # solid itself is never modified.
            z_full = np.concatenate([z_model_extended, [z_cyl_end]])
            r_full = np.concatenate([r_model_extended, [radius_final]])

            ref_bodies = []
            ref_notes = []
            # Stations specified by target diameter (searched on the taper only)
            for d in parse_float_list(self.ref_diameters.text()):
                crossings = solve_z_for_diameter(z_model_extended, r_model_extended, d)
                if not crossings:
                    ref_notes.append(f"Ø{d:.3f} mm: not reached on taper - skipped")
                    continue
                for zc in crossings:
                    lr = float(np.interp(zc, z_full, r_full))
                    ref_bodies.append(make_reference_disk(zc, lr))
                    ref_notes.append(f"Ø{d:.3f} mm at z = {zc:.2f} mm")
            # Stations specified by axial position
            for zc in parse_float_list(self.ref_positions.text()):
                if zc < z_full[0] or zc > z_full[-1]:
                    ref_notes.append(f"z = {zc:.2f} mm: outside part - skipped")
                    continue
                lr = float(np.interp(zc, z_full, r_full))
                ref_bodies.append(make_reference_disk(zc, lr))
                ref_notes.append(f"z = {zc:.2f} mm (Ø{2 * lr:.3f} mm)")

            # Bundle the reference disks with the solid (or export the solid alone)
            if ref_bodies:
                export_shape = cq.Compound.makeCompound(
                    [self.solid_combined] + ref_bodies
                )
            else:
                export_shape = self.solid_combined

            # Step 7: Export the Final Solid as a STEP File
            output_path = self.output_path.text()
            exporters.export(export_shape, output_path)

            # Update the summary
            ref_html = ""
            if ref_notes:
                items = "".join(f"<li>{n}</li>" for n in ref_notes)
                ref_html = f"<p><b>Reference Planes:</b></p><ul>{items}</ul>"
            self.summary_text.setText(
                f"<h3>Model Created Successfully</h3>"
                f"<p><b>Input File:</b> {os.path.basename(self.excel_file)}</p>"
                f"<p><b>Output File:</b> {os.path.basename(output_path)}</p>"
                f"<p><b>Model Length:</b> {z_extrapolated + extension_length:.2f} mm</p>"
                f"<p><b>Initial Diameter:</b> {2 * r_model[0]:.2f} mm</p>"
                f"<p><b>Final Diameter:</b> {final_diameter:.2f} mm</p>"
                f"{ref_html}"
            )
            
            # Update the plot
            self.update_plot(z_model, r_model, z_extrap_points, r_extrap_points, 
                             z_extrapolated, radius_final, extension_length)
            
            QMessageBox.information(self, "Success", f"STEP file saved as {output_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            raise e
    
    def update_range_plot(self):
        """Update the plot when range parameters change"""
        if self.z_raw is None or self.r_raw is None:
            return  # No data to plot yet
        
        try:
            start_val = float(self.start_distance.text())
            end_val = float(self.end_distance.text())
            self.plot_raw_data(self.z_raw, self.r_raw, start_val, end_val)
            
            # Switch to the Raw Data tab to show the changes
            for i in range(self.centralWidget().findChild(QTabWidget).count()):
                if self.centralWidget().findChild(QTabWidget).tabText(i) == "Raw Data":
                    self.centralWidget().findChild(QTabWidget).setCurrentIndex(i)
                    break
        except ValueError:
            # Invalid numeric input, don't update the plot
            pass
    
    def plot_raw_data(self, z_raw, r_raw, start_val=None, end_val=None):
        """Plot the raw data from the Excel file
        
        Args:
            z_raw: Z position values in mm
            r_raw: Radius values in mm
            start_val: Start distance for highlighting the range
            end_val: End distance for highlighting the range
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot the raw data points
        ax.plot(z_raw, 2 * r_raw, 'ko', markersize=3, alpha=0.5, label='Raw Data Points')
        
        # If we have enough points, add a smoothed line
        if len(z_raw) > 3:
            # Apply simple smoothing
            try:
                spline = make_interp_spline(z_raw, r_raw, k=min(3, len(z_raw)-1))
                z_smooth = np.linspace(z_raw.min(), z_raw.max(), 100)
                r_smooth = spline(z_smooth)
                ax.plot(z_smooth, 2 * r_smooth, 'b-', label='Smoothed Data')
                
                # Highlight the selected range if provided
                if start_val is not None and end_val is not None:
                    # Filter smoothed data to the selected range
                    mask = (z_smooth >= start_val) & (z_smooth <= end_val)
                    if any(mask):  # Only if we have points in the range
                        z_selected = z_smooth[mask]
                        r_selected = r_smooth[mask]
                        ax.plot(z_selected, 2 * r_selected, 'r-', linewidth=3, alpha=0.7, 
                                label='Selected Range')
                        
                        # Add vertical lines at boundaries
                        if start_val >= z_raw.min() and start_val <= z_raw.max():
                            ax.axvline(x=start_val, color='r', linestyle='--', alpha=0.5)
                        if end_val >= z_raw.min() and end_val <= z_raw.max():
                            ax.axvline(x=end_val, color='r', linestyle='--', alpha=0.5)
            except Exception:
                # If spline fails, just connect the points
                ax.plot(z_raw, 2 * r_raw, 'b-', label='Data')
        
        ax.set_xlabel("Z (mm)")
        ax.set_ylabel("Diameter (mm)")
        ax.set_title("Raw Diameter Data from Excel")
        ax.legend()
        ax.grid(True)
        
        self.canvas.draw()
    
    def update_plot(self, z_model, r_model, z_extrap, r_extrap, z_final, r_final, ext_len):
        """Update plot with processed model data"""
        self.model_figure.clear()
        ax = self.model_figure.add_subplot(111)
        
        # Plot the raw data first if available
        if self.z_raw is not None and self.r_raw is not None:
            ax.plot(self.z_raw, 2 * self.r_raw, 'ko', markersize=2, alpha=0.3, label='Raw Data')
        
        # Plot the smoothed diameter (2*r) vs. Z for the original data
        ax.plot(z_model, 2 * r_model, 'b-', label='Smoothed Diameter')
        
        # Plot the extrapolated section with intermediate points
        ax.plot(z_extrap, 2 * r_extrap, 'm--', label='Extrapolated Transition')
        
        # Mark the final extrapolated point and extension
        ax.plot(z_final, 2 * r_final, 'ro')
        ax.plot([z_final, z_final + ext_len], [2 * r_final, 2 * r_final], 'r-', 
                label='Cylinder Extension')
        
        ax.set_xlabel("Z (mm)")
        ax.set_ylabel("Diameter (mm)")
        ax.set_title("Smoothed Diameter vs. Z with Extrapolation")
        ax.legend()
        ax.grid(True)
        
        self.model_canvas.draw()
        
        # Switch to the model tab
        for i in range(self.centralWidget().findChild(QTabWidget).count()):
            if self.centralWidget().findChild(QTabWidget).tabText(i) == "Model Preview":
                self.centralWidget().findChild(QTabWidget).setCurrentIndex(i)
                break

def main():
    app = QApplication(sys.argv)
    window = LanternStepMaker()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()