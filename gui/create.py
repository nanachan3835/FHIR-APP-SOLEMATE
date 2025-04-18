# --- START OF FILE gui/create.py ---

import sys
import os
import uuid
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
                             QLineEdit, QFileDialog, QTextEdit, QHBoxLayout, QMessageBox, QGridLayout,
                             QFormLayout, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# --- THÊM IMPORT CỬA SỔ HEATMAP MỚI ---
from gui.serial_heatmap import SerialHeatmapWindow # Đảm bảo đường dẫn đúng

try:
    from database.manager_mongodb_2 import MongoDBManager
    from components import archindex
    # Bỏ import serial ở đây nếu không dùng trực tiếp nữa
    # from components import serial
except ImportError as e:
     print(f"Import Error in create.py: {e}. Make sure paths are correct.")
     sys.exit(1)


class CreatePatientPage(QWidget):
    def __init__(self, stacked_widget, db_manager: MongoDBManager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.db_manager = db_manager
        self.setWindowTitle("Tạo Hồ Sơ Bệnh Nhân Mới")
        self.setGeometry(100, 100, 950, 700)

    # --- THÊM DÒNG NÀY ---
        self.setStyleSheet("""
            QLabel { color: white; }
            QTableWidget { color: white; } /* Chữ trong ô bảng màu trắng */
            QHeaderView::section { /* Giữ lại style header cho dễ đọc */
                background-color: #e0e0e0;
                color: black;
                padding: 4px;
                border: 1px solid #cccccc;
                font-weight: bold;
            }
        """)
        # ------

        self.expected_rows = 60 # Cho CSV
        self.expected_cols = 60 # Cho CSV
        self.sensor_rows = 60   # Kích thước dữ liệu cảm biến mong đợi từ cửa sổ heatmap
        self.sensor_cols = 60

        self.current_data_matrix = None
        self.current_data_is_compatible = False # Chỉ True nếu là 60x60 từ CSV
        self.current_data_origin = None
        self.temp_csv_path = None

        # --- THÊM: Lưu tham chiếu tới cửa sổ heatmap ---
        self.heatmap_window = None
        # --- KẾT THÚC THÊM ---

        main_layout = QHBoxLayout(self)

        # --- Left Panel: Form Inputs ---
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_widget.setMaximumWidth(350)

        self.form_group = QFormLayout()
        self.name_input = QLineEdit()
        self.birthdate_input = QLineEdit()
        self.birthdate_input.setPlaceholderText("YYYY-MM-DD")
        self.gender_input = QLineEdit()
        self.gender_input.setPlaceholderText("male / female / other / unknown")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Số điện thoại")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Địa chỉ (không bắt buộc)")
        # --- BỎ Ô NHẬP SERIAL/BAUDRATE Ở ĐÂY VÌ CHỌN Ở CỬA SỔ KHÁC ---
        # self.serial_port_input = QLineEdit("/dev/ttyUSB0")
        # self.serial_baudrate_input = QLineEdit("115200")

        self.form_group.addRow("Họ và tên (*):", self.name_input)
        self.form_group.addRow("Ngày sinh:", self.birthdate_input)
        self.form_group.addRow("Giới tính:", self.gender_input)
        self.form_group.addRow("Số điện thoại (*):", self.phone_input)
        self.form_group.addRow("Địa chỉ:", self.address_input)
        # --- BỎ ROW SERIAL/BAUDRATE ---
        # self.form_group.addRow("Cổng Serial:", self.serial_port_input)
        # self.form_group.addRow("Baudrate:", self.serial_baudrate_input)

        form_layout.addLayout(self.form_group)
        form_layout.addSpacing(20)

        # --- Action Buttons ---
        btn_layout = QGridLayout()
        self.btn_load_csv = QPushButton("1. Load CSV (60x60)")
        # --- SỬA TÊN NÚT LOAD CẢM BIẾN ---
        self.btn_load_sensor = QPushButton(f"1. Mở Cửa Sổ Cảm Biến ({self.sensor_rows}x{self.sensor_cols})")
        self.btn_calculate_ai = QPushButton("2. Tính Arch Index (Yêu cầu 60x60)")
        self.btn_save_patient = QPushButton("3. Lưu Bệnh Nhân (Yêu cầu 60x60)")
        self.btn_clear_form = QPushButton("Xóa Form")
        self.btn_back = QPushButton("⬅ Quay lại Home")

        btn_layout.addWidget(self.btn_load_csv, 0, 0)
        btn_layout.addWidget(self.btn_load_sensor, 0, 1)
        btn_layout.addWidget(self.btn_calculate_ai, 1, 0, 1, 2)
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
        form_layout.addStretch()

        main_layout.addWidget(form_widget)

        # --- Right Panel: Heatmap ---
        heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_widget)

        self.heatmap_title = QLabel("Heatmap Dữ liệu:")
        heatmap_layout.addWidget(self.heatmap_title)

        self.figure, self.ax = plt.subplots(figsize=(6, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.figure.tight_layout()
        self.canvas.draw()

        heatmap_layout.addWidget(self.canvas)
        main_layout.addWidget(heatmap_widget)

        # --- Connect Signals ---
        self.btn_load_csv.clicked.connect(self.load_csv_data)
        # --- SỬA KẾT NỐI NÚT CẢM BIẾN ---
        self.btn_load_sensor.clicked.connect(self.open_sensor_window)
        self.btn_calculate_ai.clicked.connect(self.calculate_and_display_arch_index)
        self.btn_save_patient.clicked.connect(self.save_patient)
        self.btn_clear_form.clicked.connect(self.clear_all)
        self.btn_back.clicked.connect(self.go_home)

        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(lambda: self.status_label.setText("Trạng thái: Sẵn sàng"))

        self.btn_calculate_ai.setEnabled(False)
        self.btn_save_patient.setEnabled(False)

    def go_home(self):
        # --- THÊM: Đóng cửa sổ heatmap nếu đang mở ---
        if self.heatmap_window and self.heatmap_window.isVisible():
            self.heatmap_window.close()
        # --- KẾT THÚC THÊM ---
        self.clear_all()
        self.stacked_widget.setCurrentIndex(0)

    def update_status(self, message, is_error=False, duration=5000):
        print(f"Status Update: {message}")
        if is_error:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: green;")
        self.status_label.setText(f"Trạng thái: {message}")
        if duration > 0:
            self.status_timer.start(duration)

    def clear_all(self):
        self.name_input.clear()
        self.birthdate_input.clear()
        self.gender_input.clear()
        self.phone_input.clear()
        self.address_input.clear()

        self.current_data_matrix = None
        self.current_data_origin = None
        self.current_data_is_compatible = False
        if self.temp_csv_path and os.path.exists(self.temp_csv_path):
             try: os.remove(self.temp_csv_path)
             except OSError as e: print(f"Could not remove temp file {self.temp_csv_path}: {e}")
        self.temp_csv_path = None

        self.ax.clear()
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.heatmap_title.setText("Heatmap Dữ liệu:")
        self.canvas.draw()

        self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính")
        self.status_label.setText("Trạng thái: Form đã xóa.")
        self.status_label.setStyleSheet("color: black;")

        self.btn_calculate_ai.setEnabled(False)
        self.btn_save_patient.setEnabled(False)

    def load_csv_data(self):
        """Loads data from CSV (60x60)."""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV 60x60", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            try:
                df = pd.read_csv(file_name, header=None)
                if df.shape == (self.expected_rows, self.expected_cols):
                    self.current_data_matrix = df.values.astype(float)
                    self.current_data_origin = 'csv'
                    self.current_data_is_compatible = True # Dữ liệu CSV 60x60 là tương thích
                    self.display_heatmap()
                    self.update_status(f"Tải thành công file CSV ({self.expected_rows}x{self.expected_cols}): {os.path.basename(file_name)}")
                    self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính (Nhấn nút 2)")
                    self.btn_calculate_ai.setEnabled(True)
                    self.btn_save_patient.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Lỗi Kích Thước", f"File CSV phải có kích thước {self.expected_rows}x{self.expected_cols}. File đã chọn có kích thước {df.shape}.")
                    self.current_data_matrix = None
                    self.current_data_origin = None
                    self.current_data_is_compatible = False
                    self.btn_calculate_ai.setEnabled(False)
                    self.btn_save_patient.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Đọc File", f"Không thể đọc file CSV: {e}")
                self.current_data_matrix = None
                self.current_data_origin = None
                self.current_data_is_compatible = False
                self.btn_calculate_ai.setEnabled(False)
                self.btn_save_patient.setEnabled(False)

    # --- THAY THẾ HÀM load_sensor_data CŨ ---
    def open_sensor_window(self):
        """Mở cửa sổ hiển thị heatmap trực tiếp từ cảm biến."""
        # Kiểm tra xem cửa sổ đã mở chưa để tránh mở nhiều lần
        if self.heatmap_window is None or not self.heatmap_window.isVisible():
            self.heatmap_window = SerialHeatmapWindow()
            # Kết nối tín hiệu từ cửa sổ heatmap tới slot xử lý ở đây
            self.heatmap_window.data_captured.connect(self.handle_sensor_data_captured)
            self.heatmap_window.show()
            self.update_status("Đã mở cửa sổ cảm biến. Vui lòng chọn cổng và kết nối.", duration=0) # Không tự xóa status này
        else:
            # Nếu cửa sổ đã mở, chỉ cần đưa nó lên phía trước
            self.heatmap_window.raise_()
            self.heatmap_window.activateWindow()

    # --- THÊM SLOT MỚI ĐỂ NHẬN DỮ LIỆU TỪ CỬA SỔ HEATMAP ---
    def handle_sensor_data_captured(self, captured_matrix):
        """Xử lý dữ liệu ma trận nhận được từ cửa sổ SerialHeatmapWindow."""
        if captured_matrix is not None and isinstance(captured_matrix, np.ndarray):
             # Kiểm tra lại kích thước (mặc dù cửa sổ kia đã đảm bảo 30x16)
             if captured_matrix.shape == (self.sensor_rows, self.sensor_cols):
                 self.current_data_matrix = captured_matrix
                 self.current_data_origin = 'sensor_capture'
                 self.current_data_is_compatible = False # Dữ liệu chụp 30x16 không tương thích AI/Lưu
                 self.display_heatmap() # Hiển thị heatmap 30x16 đã chụp
                 self.update_status(f"Đã nhận dữ liệu {self.sensor_rows}x{self.sensor_cols} từ cửa sổ cảm biến.")
                 self.ai_result_label.setText("Chỉ số Arch Index: Không áp dụng (dữ liệu 30x16)")
                 # Đảm bảo các nút AI/Lưu bị vô hiệu hóa
                 self.btn_calculate_ai.setEnabled(False)
                 self.btn_save_patient.setEnabled(False)
             else:
                 print(f"Warning: Received captured data with unexpected shape {captured_matrix.shape}")
                 self.update_status("Lỗi: Dữ liệu chụp từ cảm biến có kích thước không đúng.", is_error=True)
        else:
             print("Warning: Invalid data received from heatmap window signal.")
             self.update_status("Lỗi: Không nhận được dữ liệu hợp lệ từ cửa sổ cảm biến.", is_error=True)

        # Đóng tham chiếu cửa sổ heatmap sau khi nhận dữ liệu (nếu nó chưa tự đóng)
        # Cửa sổ kia đã tự đóng sau khi emit signal, nên dòng này có thể không cần
        # if self.heatmap_window and self.heatmap_window.isVisible():
        #      self.heatmap_window.close()
        self.heatmap_window = None # Xóa tham chiếu


    def display_heatmap(self):
        """Cập nhật heatmap trên cửa sổ chính."""
        if self.current_data_matrix is not None:
            rows, cols = self.current_data_matrix.shape
            heatmap_display_title = f"Heatmap Dữ liệu ({rows}x{cols})"
            if self.current_data_origin == 'csv' and self.current_data_is_compatible:
                plot_title = f"Dữ liệu CSV ({rows}x{cols}) - Sẵn sàng tính AI/Lưu"
            elif self.current_data_origin == 'sensor_capture':
                 plot_title = f"Dữ liệu Cảm biến Đã Chụp ({rows}x{cols}) - Chỉ hiển thị"
            else:
                 plot_title = f"Dữ liệu ({rows}x{cols})" # Trường hợp khác

            self.heatmap_title.setText(heatmap_display_title)

            self.ax.clear()
            im = self.ax.imshow(self.current_data_matrix, cmap='jet', interpolation='nearest', origin='lower')
            # Điều chỉnh vmin/vmax nếu cần dựa trên loại dữ liệu
            if self.current_data_origin == 'sensor_capture':
                 im.set_clim(0, 255) # Giả sử dữ liệu cảm biến là 0-255
            # self.figure.colorbar(im, ax=self.ax) # Có thể thêm lại colorbar nếu muốn
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.ax.set_title(plot_title)
            self.figure.tight_layout()
            self.canvas.draw()
        else:
             self.ax.clear()
             self.ax.set_xticks([])
             self.ax.set_yticks([])
             self.ax.set_title("Chưa có dữ liệu")
             self.heatmap_title.setText("Heatmap Dữ liệu:")
             self.canvas.draw()


    def calculate_and_display_arch_index(self):
        """Tính Arch Index (chỉ khi dữ liệu là 60x60 từ CSV)."""
        if not self.current_data_is_compatible or self.current_data_matrix is None or self.current_data_origin != 'csv':
            QMessageBox.warning(self, "Dữ Liệu Không Phù Hợp", "Chức năng này yêu cầu dữ liệu 60x60 được tải từ file CSV.")
            self.ai_result_label.setText("Chỉ số Arch Index: Yêu cầu dữ liệu 60x60 từ CSV")
            return

        # Phần còn lại giữ nguyên...
        try:
            # ... (logic tính toán AI như cũ) ...
            self.update_status("Đang xử lý và tính Arch Index (dữ liệu 60x60)...")
            QApplication.processEvents()

            if not archindex.check_data(self.current_data_matrix):
                 self.update_status("Lỗi dữ liệu không hợp lệ (NaN, Inf).", is_error=True)
                 self.ai_result_label.setText("Chỉ số Arch Index: Lỗi dữ liệu")
                 return
            processed_matrix = archindex.convert_values(self.current_data_matrix, input_max = 5.0)
            processed_matrix = archindex.Isolated_point_removal(processed_matrix)
            processed_matrix = archindex.toes_remove(processed_matrix, threshold=30)
            processed_matrix = archindex.toes_remain_removes(processed_matrix)
            AI= archindex.compute_arch_index(processed_matrix)

            if AI is not None:
                result_text = f"Chỉ số Arch Index chân trái: {AI["left"]["AI"]:.4f} ({AI["left"]["type"]})\n"
                result_text += f"Chỉ số Arch Index chân phải: {AI["right"]["AI"]:.4f} ({AI["right"]["type"]})"
                self.ai_result_label.setText(result_text)
                self.update_status("Tính Arch Index thành công.")
            else:
                 result_text = f"Chỉ số Arch Index: Không thể tính ({foot_type})"
                 self.ai_result_label.setText(result_text)
                 self.update_status(f"Không thể tính Arch Index: {foot_type}", is_error=True)

        except Exception as e:
            self.update_status(f"Lỗi trong quá trình tính Arch Index: {e}", is_error=True, duration=10000)
            self.ai_result_label.setText("Chỉ số Arch Index: Lỗi")
            QMessageBox.critical(self, "Lỗi Tính Toán", f"Đã xảy ra lỗi: {e}")


    def save_patient(self):
        """Lưu bệnh nhân (chỉ khi dữ liệu là 60x60 từ CSV)."""
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        # ... (lấy các thông tin khác) ...

        if not name or not phone:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng nhập Họ và tên và Số điện thoại.")
            return

        if not self.current_data_is_compatible or self.current_data_matrix is None or self.current_data_origin != 'csv':
            QMessageBox.warning(self, "Dữ Liệu Không Phù Hợp", "Chức năng Lưu Bệnh Nhân yêu cầu dữ liệu 60x60 được tải từ file CSV.")
            return

        # Phần còn lại giữ nguyên...
        patient_id = f"P{uuid.uuid4().hex[:10].upper()}"
        patient_data = {
            # ... (tạo patient_data như cũ) ...
            "resourceType": "Patient", "id": patient_id, "name": [{"use": "official", "text": name}], "phone": phone,
            **({"gender": self.gender_input.text().strip()} if self.gender_input.text().strip() else {}),
            **({"birthDate": self.birthdate_input.text().strip()} if self.birthdate_input.text().strip() else {}),
            **({"address": self.address_input.text().strip()} if self.address_input.text().strip() else {}),
        }

        try:
            # ... (lưu thông tin bệnh nhân như cũ) ...
             self.update_status(f"Đang lưu thông tin bệnh nhân ID: {patient_id}...")
             QApplication.processEvents()
             save_result = self.db_manager.save_patient(patient_data)
             if "thành công" not in save_result.lower():
                 self.update_status(f"Lỗi lưu thông tin: {save_result}", is_error=True, duration=10000)
                 QMessageBox.critical(self, "Lỗi Lưu Bệnh Nhân", save_result)
                 return
             else:
                 self.update_status(f"Lưu thông tin BN {patient_id} thành công. Đang lưu dữ liệu bàn chân (60x60)...")
                 QApplication.processEvents()
        except Exception as e:
            self.update_status(f"Lỗi nghiêm trọng khi gọi save_patient: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Database", f"Lỗi kết nối hoặc lưu database: {e}")
            return

        # Lưu dữ liệu CSV (60x60)
        self.temp_csv_path = None
        try:
            # ... (lưu file CSV tạm và gọi db_manager.save_patient_csv_data như cũ) ...
            temp_dir = "temp_sensor_data"
            os.makedirs(temp_dir, exist_ok=True)
            self.temp_csv_path = os.path.join(temp_dir, f"data_{patient_id}_60x60.csv")
            np.savetxt(self.temp_csv_path, self.current_data_matrix, delimiter=',')
            data_file_to_save = self.temp_csv_path
            print(f"Saved 60x60 data temporarily to: {self.temp_csv_path} for DB")

            data_save_result = self.db_manager.save_patient_csv_data(patient_id, data_file_to_save)

            if "thành công" in data_save_result.lower():
                self.update_status(f"Lưu bệnh nhân ({patient_id}) và dữ liệu 60x60 thành công!", duration=8000)
                QMessageBox.information(self, "Thành Công", f"Đã lưu thành công bệnh nhân:\nTên: {name}\nID: {patient_id}\nvà dữ liệu bàn chân 60x60 liên quan.")
                self.clear_all()
            else:
                self.update_status(f"Lỗi lưu dữ liệu CSV (60x60): {data_save_result}", is_error=True, duration=10000)
                QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Lưu thông tin bệnh nhân thành công, nhưng lưu dữ liệu CSV 60x60 thất bại:\n{data_save_result}")

            if self.temp_csv_path and os.path.exists(self.temp_csv_path):
                try:
                    os.remove(self.temp_csv_path)
                    print(f"Removed temporary file: {self.temp_csv_path}")
                    self.temp_csv_path = None
                except OSError as e:
                    print(f"Warning: Could not remove temporary file {self.temp_csv_path}: {e}")

        except Exception as e:
            self.update_status(f"Lỗi khi lưu dữ liệu CSV 60x60 vào DB: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Đã xảy ra lỗi khi chuẩn bị hoặc lưu dữ liệu CSV 60x60: {e}")


# --- END OF FILE gui/create.py ---