import sys
import os

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.interpolate import make_interp_spline
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QGroupBox, QFormLayout, QMessageBox,
                             QTabWidget)

from .core import (
    ModelParams,
    build_taper_model,
    export_step,
    load_profile,
    make_solid,
)
from .references import build_reference_bodies


def parse_float_list(text):
    """Parse a comma/space separated list of floats, ignoring blank/invalid tokens."""
    vals = []
    for tok in text.replace(",", " ").split():
        try:
            vals.append(float(tok))
        except ValueError:
            pass
    return vals


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
                profile = load_profile(self.excel_file)
                self.z_raw = profile.z_raw
                self.r_raw = profile.r_raw
                start_val = self.z_raw.min()
                end_val = self.z_raw.max()
                self.start_distance.setText(f"{start_val:.2f}")
                self.end_distance.setText(f"{end_val:.2f}")
                self.plot_raw_data(self.z_raw, self.r_raw,
                                   float(self.start_distance.text()),
                                   float(self.end_distance.text()))
            except Exception as e:
                QMessageBox.warning(self, "Error",
                                    f"Could not load Excel file: {str(e)}")
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
            # Load + model via the pure core pipeline
            profile = load_profile(self.excel_file)
            params = ModelParams(start_distance, end_distance,
                                 final_diameter, extension_length)
            model = build_taper_model(profile, params)
            solid = make_solid(model)

            # Optional reference planes from the two input fields
            ref_diameters = parse_float_list(self.ref_diameters.text())
            ref_positions = parse_float_list(self.ref_positions.text())
            ref_bodies, ref_notes = build_reference_bodies(
                model, ref_diameters, ref_positions
            )

            output_path = self.output_path.text()
            export_step(solid, ref_bodies, output_path)

            # Keep references for any later use / preview
            self.solid_combined = solid

            ref_html = ""
            if ref_notes:
                items = "".join(f"<li>{n}</li>" for n in ref_notes)
                ref_html = f"<p><b>Reference Planes:</b></p><ul>{items}</ul>"
            self.summary_text.setText(
                f"<h3>Model Created Successfully</h3>"
                f"<p><b>Input File:</b> {os.path.basename(self.excel_file)}</p>"
                f"<p><b>Output File:</b> {os.path.basename(output_path)}</p>"
                f"<p><b>Model Length:</b> {model.z_cyl_end:.2f} mm</p>"
                f"<p><b>Initial Diameter:</b> {2 * model.r_model[0]:.2f} mm</p>"
                f"<p><b>Final Diameter:</b> {final_diameter:.2f} mm</p>"
                f"{ref_html}"
            )

            self.update_plot(model.z_model, model.r_model,
                             model.z_extrap_points, model.r_extrap_points,
                             model.z_extrapolated, model.radius_final,
                             extension_length)

            QMessageBox.information(self, "Success",
                                    f"STEP file saved as {output_path}")

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

def _run_selftest():
    """Headless check for frozen-app CI smoke tests.

    Reaching this function already proves the frozen entry point imported this
    module (and therefore PyQt5) successfully - that import is exactly what broke
    a frozen build before. We additionally exercise cadquery/OCCT so a broken
    OCP bundle also fails. Exits 0 on success, non-zero on any failure, WITHOUT
    opening a window (so it is reliable on a headless CI runner).
    """
    import cadquery as cq

    from . import core, references  # noqa: F401  (import-graph check)

    box = cq.Workplane("XY").box(1.0, 1.0, 1.0).val()
    assert box.Volume() > 0, "OCCT kernel produced a degenerate solid"
    print("LANTERN_STEP_SELFTEST OK: GUI + core + OCCT imports functional")
    return 0


def main():
    # CI / smoke-test hook: run a headless self-check and exit instead of
    # opening the GUI. Set LANTERN_STEP_SELFTEST=1 to enable.
    if os.environ.get("LANTERN_STEP_SELFTEST"):
        raise SystemExit(_run_selftest())

    app = QApplication(sys.argv)
    window = LanternStepMaker()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()