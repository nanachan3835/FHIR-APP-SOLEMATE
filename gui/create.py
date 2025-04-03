# --- START OF FILE gui/create.py ---

import sys
import os
import uuid # For generating unique IDs
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
                             QLineEdit, QFileDialog, QTextEdit, QHBoxLayout, QMessageBox, QGridLayout,
                             QFormLayout, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer # Added QTimer for status clear
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Assuming database and components are accessible relative to the main execution directory
# Adjust paths if your project structure is different
try:
    import database 
    from database.manager_mongodb_2 import MongoDBManager
    from components import archindex
    from components import serial # Import the serial reading function
except ImportError as e:
     print(f"Import Error in create.py: {e}. Make sure paths are correct.")
     # Handle case where modules aren't found, maybe show error and disable functionality
     sys.exit(1) # Exit if core components are missing


class CreatePatientPage(QWidget):
    def __init__(self, stacked_widget, db_manager: MongoDBManager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.db_manager = db_manager # Use the passed manager instance
        self.setWindowTitle("Tạo Hồ Sơ Bệnh Nhân Mới")
        self.setGeometry(100, 100, 950, 700) # Adjusted size

        self.current_data_matrix = None # Store the loaded 60x60 numpy array
        self.current_data_origin = None # Store where data came from ('csv' or 'sensor')
        self.temp_csv_path = None # Path if data from sensor needs temporary save

        main_layout = QHBoxLayout(self)

        # --- Left Panel: Form Inputs ---
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_widget.setMaximumWidth(350) # Constrain width of the form

        self.form_group = QFormLayout()
        self.name_input = QLineEdit()
        self.birthdate_input = QLineEdit()
        self.birthdate_input.setPlaceholderText("YYYY-MM-DD")
        self.gender_input = QLineEdit()
        self.gender_input.setPlaceholderText("male / female / other / unknown")
        self.phone_input = QLineEdit() # Added Phone Input
        self.phone_input.setPlaceholderText("Số điện thoại")
        self.address_input = QLineEdit() # Optional: Add address if needed
        self.address_input.setPlaceholderText("Địa chỉ (không bắt buộc)")
        self.serial_port_input = QLineEdit("COM3") # Added Serial Port Input (default COM3)

        self.form_group.addRow("Họ và tên (*):", self.name_input)
        self.form_group.addRow("Ngày sinh:", self.birthdate_input)
        self.form_group.addRow("Giới tính:", self.gender_input)
        self.form_group.addRow("Số điện thoại (*):", self.phone_input)
        self.form_group.addRow("Địa chỉ:", self.address_input)
        self.form_group.addRow("Cổng Serial:", self.serial_port_input)

        form_layout.addLayout(self.form_group)
        form_layout.addSpacing(20)

        # --- Action Buttons ---
        btn_layout = QGridLayout()
        self.btn_load_csv = QPushButton("1. Load từ CSV")
        self.btn_load_sensor = QPushButton("1. Load từ Cảm Biến")
        self.btn_calculate_ai = QPushButton("2. Tính Arch Index") # Button to explicitly calculate
        self.btn_save_patient = QPushButton("3. Lưu Bệnh Nhân") # Added Save Button
        self.btn_clear_form = QPushButton("Xóa Form")
        self.btn_back = QPushButton("⬅ Quay lại Home")

        btn_layout.addWidget(self.btn_load_csv, 0, 0)
        btn_layout.addWidget(self.btn_load_sensor, 0, 1)
        btn_layout.addWidget(self.btn_calculate_ai, 1, 0, 1, 2) # Span across 2 columns
        btn_layout.addWidget(self.btn_save_patient, 2, 0, 1, 2)
        btn_layout.addWidget(self.btn_clear_form, 3, 0)
        btn_layout.addWidget(self.btn_back, 3, 1)

        form_layout.addLayout(btn_layout)
        form_layout.addSpacing(20)

        # --- Status & Results ---
        self.ai_result_label = QLabel("Chỉ số Arch Index: Chưa tính")
        self.ai_result_label.setStyleSheet("font-weight: bold;")
        self.status_label = QLabel("Trạng thái: Sẵn sàng")
        self.status_label.setWordWrap(True)

        form_layout.addWidget(self.ai_result_label)
        form_layout.addWidget(self.status_label)
        form_layout.addStretch() # Push elements to the top

        main_layout.addWidget(form_widget)

        # --- Right Panel: Heatmap ---
        heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_widget)

        heatmap_layout.addWidget(QLabel("Heatmap Bàn Chân (Dữ liệu 60x60):"))
        self.figure, self.ax = plt.subplots(figsize=(6, 6))
        self.canvas = FigureCanvas(self.figure)
        # Initial empty plot
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.figure.tight_layout()
        self.canvas.draw()

        heatmap_layout.addWidget(self.canvas)
        main_layout.addWidget(heatmap_widget)

        # --- Connect Signals ---
        self.btn_load_csv.clicked.connect(self.load_csv_data)
        self.btn_load_sensor.clicked.connect(self.load_sensor_data)
        self.btn_calculate_ai.clicked.connect(self.calculate_and_display_arch_index)
        self.btn_save_patient.clicked.connect(self.save_patient)
        self.btn_clear_form.clicked.connect(self.clear_all)
        self.btn_back.clicked.connect(self.go_home)

        # Timer to clear status messages after a few seconds
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(lambda: self.status_label.setText("Trạng thái: Sẵn sàng"))

    def go_home(self):
        self.clear_all() # Clear data when leaving
        self.stacked_widget.setCurrentIndex(0) # Assuming Home is index 0

    def update_status(self, message, is_error=False, duration=5000):
        """Updates the status label and sets a timer to clear it."""
        print(f"Status Update: {message}") # Also print to console
        if is_error:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: green;")
        self.status_label.setText(f"Trạng thái: {message}")
        # Restart the timer
        self.status_timer.start(duration)

    def clear_all(self):
        """Clears form inputs, data, heatmap, and results."""
        self.name_input.clear()
        self.birthdate_input.clear()
        self.gender_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        # self.serial_port_input.clear() # Keep serial port potentially

        self.current_data_matrix = None
        self.current_data_origin = None
        self.temp_csv_path = None
        if self.temp_csv_path and os.path.exists(self.temp_csv_path):
             try: os.remove(self.temp_csv_path)
             except OSError as e: print(f"Could not remove temp file {self.temp_csv_path}: {e}")
        self.temp_csv_path = None

        self.ax.clear()
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.canvas.draw()

        self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính")
        self.status_label.setText("Trạng thái: Form đã xóa.")
        self.status_label.setStyleSheet("color: black;")


    def load_csv_data(self):
        """Loads data from a user-selected CSV file."""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV 60x60", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            try:
                # Use pandas for robust CSV reading, ensure no header is interpreted
                df = pd.read_csv(file_name, header=None)
                if df.shape == (60, 60):
                    self.current_data_matrix = df.values.astype(float) # Ensure numeric
                    self.current_data_origin = 'csv'
                    self.display_heatmap()
                    self.update_status(f"Tải thành công file CSV: {os.path.basename(file_name)}")
                    self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính (Nhấn nút 2)")
                else:
                    QMessageBox.warning(self, "Lỗi Kích Thước", f"File CSV phải có kích thước 60x60. File đã chọn có kích thước {df.shape}.")
                    self.current_data_matrix = None
                    self.current_data_origin = None
            except pd.errors.EmptyDataError:
                 QMessageBox.critical(self, "Lỗi Đọc File", "File CSV rỗng hoặc không hợp lệ.")
                 self.current_data_matrix = None
                 self.current_data_origin = None
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Đọc File", f"Không thể đọc file CSV: {e}")
                self.current_data_matrix = None
                self.current_data_origin = None

    def load_sensor_data(self):
        """Loads data from the serial port specified in the input field."""
        port = self.serial_port_input.text().strip()
        if not port:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng nhập tên cổng Serial.")
            return

        self.update_status(f"Đang đọc dữ liệu từ {port}...")
        QApplication.processEvents() # Allow UI to update

        # Call the serial reading function
        # Adjust baudrate/timeout if needed
        data, message = serial.read_sensor_data(port, baudrate=115200, timeout=5)

        if data is not None:
            self.current_data_matrix = data
            self.current_data_origin = 'sensor'
            self.display_heatmap()
            self.update_status(f"Đọc thành công dữ liệu từ {port}.")
            self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính (Nhấn nút 2)")
        else:
            self.current_data_matrix = None
            self.current_data_origin = None
            self.update_status(f"Lỗi đọc Serial: {message}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Đọc Serial", message)

    def display_heatmap(self):
        """Updates the matplotlib canvas with the current data matrix."""
        if self.current_data_matrix is not None:
            self.ax.clear()
            # Use 'jet' or 'viridis' colormap, add colorbar
            im = self.ax.imshow(self.current_data_matrix, cmap='jet', interpolation='nearest')
            # self.figure.colorbar(im, ax=self.ax) # Optional: Add colorbar back if needed
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.ax.set_title("Dữ liệu Cảm biến")
            self.figure.tight_layout() # Adjust layout
            self.canvas.draw()
        else:
             self.ax.clear()
             self.ax.set_xticks([])
             self.ax.set_yticks([])
             self.ax.set_title("Chưa có dữ liệu")
             self.canvas.draw()


    def calculate_and_display_arch_index(self):
        """Calculates and displays the Arch Index using the loaded data."""
        if self.current_data_matrix is None:
            QMessageBox.warning(self, "Thiếu Dữ Liệu", "Vui lòng tải dữ liệu (CSV hoặc Cảm biến) trước khi tính Arch Index.")
            return

        try:
            self.update_status("Đang xử lý và tính Arch Index...")
            QApplication.processEvents()

            # --- Arch Index Calculation Steps ---
            # 1. Check data validity (basic check)
            if not archindex.check_data(self.current_data_matrix):
                 self.update_status("Lỗi dữ liệu không hợp lệ (NaN, Inf).", is_error=True)
                 self.ai_result_label.setText("Chỉ số Arch Index: Lỗi dữ liệu")
                 return

            # 2. Convert values (Assuming sensor range is 0-5V or similar, mapping to 0-255)
            #    NOTE: Adjust the 'gia_tri' (5) if your sensor's max value is different!
            processed_matrix = archindex.convert_values(self.current_data_matrix, gia_tri=5) # <--- CHECK THIS VALUE

            # 3. Noise Removal (Isolated points)
            processed_matrix = archindex.Isolated_point_removal(processed_matrix)

            # 4. Toes Removal (Adjust threshold if needed)
            processed_matrix = archindex.toes_remove(processed_matrix, threshold=30) # <-- Check threshold
            processed_matrix = archindex.toes_remain_removes(processed_matrix) # Further refine toes removal

            # 5. Compute Arch Index
            AI, foot_type = archindex.compute_arch_index(processed_matrix)
            # --- End Calculation ---

            if AI is not None:
                result_text = f"Chỉ số Arch Index: {AI:.4f} ({foot_type})"
                self.ai_result_label.setText(result_text)
                self.update_status("Tính Arch Index thành công.")
                # Optionally display the processed image
                # self.ax.imshow(processed_matrix, cmap='gray') # Show processed image instead?
                # self.canvas.draw()
            else:
                 result_text = f"Chỉ số Arch Index: Không thể tính ({foot_type})" # e.g., No foot detected
                 self.ai_result_label.setText(result_text)
                 self.update_status(f"Không thể tính Arch Index: {foot_type}", is_error=True)

        except Exception as e:
            self.update_status(f"Lỗi trong quá trình tính Arch Index: {e}", is_error=True, duration=10000)
            self.ai_result_label.setText("Chỉ số Arch Index: Lỗi")
            QMessageBox.critical(self, "Lỗi Tính Toán", f"Đã xảy ra lỗi: {e}")


    def save_patient(self):
        """Gathers data, validates, saves patient and sensor data to MongoDB."""
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        birthdate = self.birthdate_input.text().strip() # Optional
        gender = self.gender_input.text().strip()       # Optional
        address = self.address_input.text().strip()     # Optional

        # --- Validation ---
        if not name:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng nhập Họ và tên bệnh nhân.")
            return
        if not phone:
             QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng nhập Số điện thoại bệnh nhân.")
             return
        if self.current_data_matrix is None:
            QMessageBox.warning(self, "Thiếu Dữ Liệu", "Vui lòng tải dữ liệu bàn chân (CSV hoặc Cảm biến) trước khi lưu.")
            return

        # --- Generate Patient ID ---
        # Simple unique ID, you could use other strategies
        patient_id = f"P{uuid.uuid4().hex[:10].upper()}"

        # --- Prepare Patient Data Structure ---
        patient_data = {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"use": "official", "text": name}],
            "phone": phone,
            # Optional fields, only add if they have values
            **({"gender": gender} if gender else {}),
            **({"birthDate": birthdate} if birthdate else {}),
            **({"address": address} if address else {}),
        }

        # --- Save Patient Demographics ---
        try:
             self.update_status(f"Đang lưu thông tin bệnh nhân ID: {patient_id}...")
             QApplication.processEvents()
             save_result = self.db_manager.save_patient(patient_data)

             if "thành công" not in save_result.lower(): # Check if save failed (duplicate or error)
                 self.update_status(f"Lỗi lưu thông tin: {save_result}", is_error=True, duration=10000)
                 QMessageBox.critical(self, "Lỗi Lưu Bệnh Nhân", save_result)
                 return
             else:
                 self.update_status(f"Lưu thông tin BN {patient_id} thành công. Đang lưu dữ liệu bàn chân...")
                 QApplication.processEvents()

        except Exception as e:
            self.update_status(f"Lỗi nghiêm trọng khi gọi save_patient: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Database", f"Lỗi kết nối hoặc lưu database: {e}")
            return

        # --- Save Sensor/CSV Data ---
        # The manager needs a CSV *file path*. If data is from sensor, save it temporarily.
        self.temp_csv_path = None
        try:
            if self.current_data_origin == 'sensor':
                # Create a temporary file path
                temp_dir = "temp_sensor_data"
                os.makedirs(temp_dir, exist_ok=True)
                self.temp_csv_path = os.path.join(temp_dir, f"data_{patient_id}.csv")
                # Save the numpy array to the temporary CSV
                np.savetxt(self.temp_csv_path, self.current_data_matrix, delimiter=',')
                data_file_to_save = self.temp_csv_path
                print(f"Saved sensor data temporarily to: {self.temp_csv_path}")
            elif self.current_data_origin == 'csv':
                # If loaded from CSV, we might have the path, but it's safer
                # to just save the current matrix to a temp file anyway
                # to ensure consistency and handle cases where the original file moved.
                # Let's stick to saving a temp file regardless.
                temp_dir = "temp_sensor_data"
                os.makedirs(temp_dir, exist_ok=True)
                self.temp_csv_path = os.path.join(temp_dir, f"data_{patient_id}.csv")
                np.savetxt(self.temp_csv_path, self.current_data_matrix, delimiter=',')
                data_file_to_save = self.temp_csv_path
                print(f"Saved loaded CSV data temporarily to: {self.temp_csv_path} for DB consistency")
            else:
                # Should not happen if initial check passed, but safeguard
                self.update_status("Lỗi: Không xác định nguồn gốc dữ liệu.", is_error=True)
                # Attempt to delete the patient record that might have been created
                self.db_manager.delete_patient(patient_id)
                return


            # Call the manager function to save the data from the (potentially temp) CSV
            data_save_result = self.db_manager.save_patient_csv_data(patient_id, data_file_to_save)

            if "thành công" in data_save_result.lower():
                self.update_status(f"Lưu bệnh nhân ({patient_id}) và dữ liệu thành công!", duration=8000)
                QMessageBox.information(self, "Thành Công", f"Đã lưu thành công bệnh nhân:\nTên: {name}\nID: {patient_id}\nvà dữ liệu bàn chân liên quan.")
                self.clear_all() # Clear form for next entry
            else:
                # Data saving failed, show error, maybe try to delete the patient record?
                self.update_status(f"Lỗi lưu dữ liệu CSV: {data_save_result}", is_error=True, duration=10000)
                QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Lưu thông tin bệnh nhân thành công, nhưng lưu dữ liệu CSV thất bại:\n{data_save_result}\n\nVui lòng thử lại việc tải và lưu dữ liệu cho bệnh nhân ID: {patient_id} sau.")
                # Don't clear form here, let user decide

            # --- Cleanup temporary file ---
            if self.temp_csv_path and os.path.exists(self.temp_csv_path):
                try:
                    os.remove(self.temp_csv_path)
                    print(f"Removed temporary file: {self.temp_csv_path}")
                    self.temp_csv_path = None # Reset path
                except OSError as e:
                    print(f"Warning: Could not remove temporary file {self.temp_csv_path}: {e}")
                    # Keep self.temp_csv_path set so clear_all might try again

        except Exception as e:
            self.update_status(f"Lỗi khi lưu dữ liệu CSV vào DB: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Đã xảy ra lỗi khi chuẩn bị hoặc lưu dữ liệu CSV: {e}")
            # Consider deleting the patient record if data saving fails critically
            # print(f"Attempting to rollback patient creation for {patient_id} due to data save error...")
            # rollback_msg = self.db_manager.delete_patient(patient_id)
            # print(f"Rollback result: {rollback_msg}")