# --- START OF FILE gui/create.py ---

import sys
import os
import uuid
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
                             QLineEdit, QFileDialog, QTextEdit, QHBoxLayout, QMessageBox, QGridLayout,
                             QFormLayout, QDialog, QDialogButtonBox, QSizePolicy) # <<< THÊM QSizePolicy
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.colorbar import Colorbar # Thường không cần import trực tiếp

# --- THÊM IMPORT CỬA SỔ HEATMAP MỚI ---
from gui.serial_heatmap import SerialHeatmapWindow # Đảm bảo đường dẫn đúng

try:
    # <<< KIỂM TRA LẠI TÊN FILE MANAGER CỦA BẠN >>>
    # Nếu bạn dùng file gốc là manager_mongodb.py thì đổi lại ở đây
    from database.manager_mongodb_2 import MongoDBManager
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
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
        # Tăng kích thước cửa sổ mặc định để có chỗ cho heatmap cao hơn
        self.setGeometry(100, 100, 1050, 800)


        self.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 10pt; /* Đặt kích thước font cơ bản cho label */
            }
            /* Style cho các ô nhập liệu */
            QLineEdit {
                color: black; /* Chữ nhập màu đen */
                background-color: white; /* Nền trắng */
                border: 1px solid #ccc;
                border-radius: 8px; /* Bo tròn nhẹ */
                padding: 20px 24px; /* Tăng padding bên trong (Top/Bottom, Left/Right) */
                font-size: 15pt; /* Tăng kích thước chữ nhập */
                min-height: 40px; /* Đảm bảo chiều cao tối thiểu */
            }
            QLineEdit::placeholder {
                 color: #a0a0a0; /* Giữ màu placeholder */
            }

            /* Style cho các nút bấm */
            QPushButton {
                /* Kế thừa màu nền/chữ từ theme hoặc đặt ở đây */
                /* Ví dụ dùng màu giống nút Home nhưng chữ đen */
                /* background-color: white; */
                /* color: black; */
                font-size: 10pt; /* Tăng nhẹ font chữ nút */
                font-weight: bold;
                padding: 30px 40px; /* Tăng padding bên trong nút */
                min-height: 65px;  /* Làm nút cao hơn */
                border-radius: 15px; /* Bo tròn viền */
                margin: 5px; /* Thêm khoảng cách nhỏ giữa các nút trong grid */
            }
            /* Có thể thêm :hover, :pressed nếu muốn */
            QPushButton:hover {
                 /* background-color: #f0f0f0; */ /* Ví dụ */
            }
             QPushButton:pressed {
                 /* background-color: #e0e0e0; */ /* Ví dụ */
            }
            /* Nút Back có thể style riêng nếu muốn */
             QPushButton#BackButton { /* Ví dụ đặt ID nếu cần */
                /* font-weight: normal; */
             }

        """)

        # --- Giữ lại style chữ trắng cho QLabel ---
        self.setStyleSheet("QLabel { color: white; }")

        # --- Khai báo biến ---
        self.expected_rows = 60 # Số hàng mong đợi
        self.expected_cols = 60# Số cột mong đợi
        self.sensor_rows = 60   # Giả định cửa sổ heatmap trả về 60x60
        self.sensor_cols = 60

        self.current_data_matrix = None
        self.current_data_is_compatible = False
        self.current_data_origin = None
        self.temp_csv_path = None
        self.heatmap_window = None
        self.cbar = None # <<< THÊM: Biến lưu trữ colorbar

        # --- Layout chính ---
        main_layout = QHBoxLayout(self)

        # --- Left Panel: Form Inputs ---
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_widget.setMaximumWidth(380) # Đặt chiều rộng tối đa cho form

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

        self.form_group.addRow("Họ và tên (*):", self.name_input)
        self.form_group.addRow("Ngày sinh:", self.birthdate_input)
        self.form_group.addRow("Giới tính:", self.gender_input)
        self.form_group.addRow("Số điện thoại (*):", self.phone_input)
        self.form_group.addRow("Địa chỉ:", self.address_input)

        form_layout.addLayout(self.form_group)
        form_layout.addSpacing(20)
        # === THÊM HÌNH ẢNH VÀO ĐÂY ===
        form_layout.addSpacing(15) # Thêm khoảng trống phía trên ảnh

        self.regions_image_label = QLabel()
        regions_image_path = "assets/ngon.png"

        if os.path.exists(regions_image_path):
            pixmap = QPixmap(regions_image_path)
            # Chỉnh kích thước ảnh cho phù hợp với chiều rộng của panel (ví dụ 350px)
            scaled_pixmap = pixmap.scaledToWidth(500, Qt.SmoothTransformation)
            self.regions_image_label.setPixmap(scaled_pixmap)
            self.regions_image_label.setAlignment(Qt.AlignCenter) # Căn giữa ảnh
        else:
            print(f"Warning: Foot regions image not found at {regions_image_path}")
            self.regions_image_label.setText("Foot Regions Image (Not Found)")
            self.regions_image_label.setStyleSheet("color: yellow;") # Cho dễ thấy nếu lỗi
            self.regions_image_label.setAlignment(Qt.AlignCenter)

        form_layout.addWidget(self.regions_image_label) # Thêm label ảnh vào layout
        form_layout.addSpacing(15) # Thêm khoảng trống phía dưới ảnh
        # === KẾT THÚC THÊM HÌNH ẢNH ===
        # --- Action Buttons ---
        btn_layout = QGridLayout()
        self.btn_load_csv = QPushButton("1. Load CSV (60x60)")
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

        main_layout.addWidget(form_widget) # Thêm form panel

        # --- Right Panel: Heatmap ---
        heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_widget)
        heatmap_layout.setContentsMargins(10, 10, 10, 10)

        self.heatmap_title = QLabel("Heatmap Dữ liệu:")
        self.heatmap_title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        heatmap_layout.addWidget(self.heatmap_title)

        # --- Cấu hình Matplotlib Figure và Canvas ---
        self.figure, self.ax = plt.subplots(figsize=(5.5, 5.5)) # Kích thước ban đầu
        self.canvas = FigureCanvas(self.figure)

        # <<< THIẾT LẬP SIZE POLICY ĐỂ CANVAS TỰ CO DÃN >>>
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        # --- Thiết lập màu nền và màu chữ Matplotlib ---
        self.figure.patch.set_facecolor('#003366')
        self.ax.set_facecolor('#EAEAF2') # Màu nền vùng vẽ
        self.ax.title.set_color('white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        # self.ax.spines['bottom'].set_color('white') # Có thể ẩn spines nếu muốn gọn hơn
        # self.ax.spines['top'].set_color('white')
        # self.ax.spines['left'].set_color('white')
        # self.ax.spines['right'].set_color('white')

        self.ax.set_title("Chưa có dữ liệu", color='white')

        # <<< KHỞI TẠO HEATMAP VÀ COLORBAR >>>
        # Dùng dữ liệu NaN để không vẽ gì ban đầu
        initial_data = np.full((self.expected_rows, self.expected_cols), np.nan)
        self.heatmap_im = self.ax.imshow(initial_data, cmap='jet', interpolation='gaussian', origin='lower', vmin=0, vmax=1) # vmax=1 ban đầu
        self.cbar = self.figure.colorbar(self.heatmap_im, ax=self.ax)
        self.cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(self.cbar.ax.axes, 'yticklabels'), color='white')
        # <<< KẾT THÚC KHỞI TẠO HEATMAP VÀ COLORBAR >>>

        # <<< HIỂN THỊ TRỤC BAN ĐẦU (nhưng sẽ không có số liệu) >>>
        self.ax.xaxis.set_visible(True)
        self.ax.yaxis.set_visible(True)
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # self.figure.tight_layout() # Tạm thời bỏ comment, gọi trong display_heatmap
        heatmap_layout.addWidget(self.canvas)

        # <<< ĐẶT STRETCH FACTOR CHO LAYOUT CHÍNH >>>
        main_layout.setStretchFactor(form_widget, 1)
        main_layout.addWidget(heatmap_widget)
        main_layout.setStretchFactor(heatmap_widget, 3) # Ưu tiên không gian cho heatmap
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # --- Connect Signals ---
        # ... (Giữ nguyên) ...
        self.btn_load_csv.clicked.connect(self.load_csv_data)
        self.btn_load_sensor.clicked.connect(self.open_sensor_window)
        self.btn_calculate_ai.clicked.connect(self.calculate_and_display_arch_index)
        self.btn_save_patient.clicked.connect(self.save_patient)
        self.btn_clear_form.clicked.connect(self.clear_all)
        self.btn_back.clicked.connect(self.go_home)


        # --- Timer và setEnabled ban đầu ---
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        # Sửa lại lambda để reset màu chữ status về trắng
        self.status_timer.timeout.connect(lambda: self.status_label.setStyleSheet("color: white;"))
        self.status_timer.timeout.connect(lambda: self.status_label.setText("Trạng thái: Sẵn sàng"))
        self.btn_calculate_ai.setEnabled(False)
        self.btn_save_patient.setEnabled(False)
        # Gọi display_heatmap một lần để đảm bảo trạng thái ban đầu đúng
        self.display_heatmap()


    def go_home(self):
        if self.heatmap_window and self.heatmap_window.isVisible():
            self.heatmap_window.close()
        self.clear_all()
        self.stacked_widget.setCurrentIndex(0)

    # Sửa update_status để reset về màu trắng
    def update_status(self, message, is_error=False, duration=5000):
        print(f"Status Update: {message}")
        if is_error:
            self.status_label.setStyleSheet("color: red;")
        else:
            # Thành công hoặc thông báo thông thường -> màu trắng
            self.status_label.setStyleSheet("color: white;")
        self.status_label.setText(f"Trạng thái: {message}")
        if duration > 0:
            self.status_timer.start(duration)
        else:
            self.status_timer.stop()

    # Sửa clear_all để gọi display_heatmap
    def clear_all(self):
        self.name_input.clear()
        self.birthdate_input.clear()
        self.gender_input.clear()
        self.phone_input.clear()
        self.address_input.clear()

        self.current_data_matrix = None # <<< Đặt lại data = None
        self.current_data_origin = None
        self.current_data_is_compatible = False
        # <<< Gọi display_heatmap để reset plot >>>
        self.display_heatmap()
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        if self.temp_csv_path and os.path.exists(self.temp_csv_path):
             try: os.remove(self.temp_csv_path)
             except OSError as e: print(f"Could not remove temp file {self.temp_csv_path}: {e}")
        self.temp_csv_path = None

        self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính")
        # Sửa status label ở đây thay vì trong timer timeout
        self.status_label.setStyleSheet("color: white;")
        self.status_label.setText("Trạng thái: Form đã xóa.")


        self.btn_calculate_ai.setEnabled(False)
        self.btn_save_patient.setEnabled(False)

    def load_csv_data(self):
        """Loads data from CSV (60x60)."""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV 60x60", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            try:
                # Đọc dữ liệu (có thể dùng pandas hoặc numpy)
                # Giả sử đọc thành công vào df
                df = pd.read_csv(file_name, header=None) # Hoặc np.loadtxt
                if df.shape <=(self.expected_rows, self.expected_cols):
                    self.current_data_matrix = df.values.astype(float)
                    self.current_data_origin = 'csv'
                    self.current_data_is_compatible = True
                    self.display_heatmap() # <<< Gọi display_heatmap để cập nhật plot
                    self.update_status(f"Tải thành công file CSV ({self.expected_rows}x{self.expected_cols}): {os.path.basename(file_name)}")
                    self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính (Nhấn nút 2)")
                    self.btn_calculate_ai.setEnabled(True)
                    self.btn_save_patient.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Lỗi Kích Thước", f"File CSV phải có kích thước {self.expected_rows}x{self.expected_cols}. File đã chọn có kích thước {df.shape}.")
                    self.current_data_matrix = None # Đặt lại data nếu lỗi
                    self.current_data_origin = None
                    self.current_data_is_compatible = False
                    self.display_heatmap() # <<< Cập nhật plot về trạng thái rỗng
                    self.btn_calculate_ai.setEnabled(False)
                    self.btn_save_patient.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Đọc File", f"Không thể đọc file CSV: {e}")
                self.current_data_matrix = None # Đặt lại data nếu lỗi
                self.current_data_origin = None
                self.current_data_is_compatible = False
                self.display_heatmap() # <<< Cập nhật plot về trạng thái rỗng
                self.btn_calculate_ai.setEnabled(False)
                self.btn_save_patient.setEnabled(False)

    def open_sensor_window(self):
        """Mở cửa sổ hiển thị heatmap trực tiếp từ cảm biến."""
        if self.heatmap_window is None or not self.heatmap_window.isVisible():
            self.heatmap_window = SerialHeatmapWindow()
            self.heatmap_window.data_captured.connect(self.handle_sensor_data_captured)
            self.heatmap_window.show()
            self.update_status("Đã mở cửa sổ cảm biến. Vui lòng chọn cổng và kết nối.", duration=0)
        else:
            self.heatmap_window.raise_()
            self.heatmap_window.activateWindow()

    # Sửa lại handle_sensor_data_captured
    def handle_sensor_data_captured(self, captured_matrix):
        """Xử lý dữ liệu ma trận 60x60 nhận được từ cửa sổ SerialHeatmapWindow."""
        if captured_matrix is not None and isinstance(captured_matrix, np.ndarray):
             if captured_matrix.shape == (self.sensor_rows, self.sensor_cols):
                 self.current_data_matrix = captured_matrix
                 self.current_data_origin = 'sensor_capture'
                 self.current_data_is_compatible = True # Dữ liệu 60x60 từ sensor giờ tương thích
                 self.display_heatmap() # <<< Gọi display_heatmap để cập nhật plot
                 self.update_status(f"Đã nhận dữ liệu {self.sensor_rows}x{self.sensor_cols} từ cảm biến.")
                 self.ai_result_label.setText("Chỉ số Arch Index: Chưa tính (Nhấn nút 2)")
                 self.btn_calculate_ai.setEnabled(True)
                 self.btn_save_patient.setEnabled(True)
             else:
                 # ... (xử lý lỗi kích thước như cũ) ...
                 print(f"Warning: Received captured data with unexpected shape {captured_matrix.shape}. Expected {(self.sensor_rows, self.sensor_cols)}")
                 self.update_status("Lỗi: Dữ liệu chụp từ cảm biến có kích thước không đúng.", is_error=True)
                 self.current_data_matrix = None # Reset data
                 self.display_heatmap() # Reset plot
                 self.btn_calculate_ai.setEnabled(False)
                 self.btn_save_patient.setEnabled(False)
        else:
             # ... (xử lý lỗi data không hợp lệ như cũ) ...
             print("Warning: Invalid data received from heatmap window signal.")
             self.update_status("Lỗi: Không nhận được dữ liệu hợp lệ từ cửa sổ cảm biến.", is_error=True)
             self.current_data_matrix = None # Reset data
             self.display_heatmap() # Reset plot
             self.btn_calculate_ai.setEnabled(False)
             self.btn_save_patient.setEnabled(False)
        self.heatmap_window = None


    # <<< HÀM display_heatmap ĐÃ SỬA ĐỔI HOÀN CHỈNH >>>
        # <<< HÀM display_heatmap ĐÃ SỬA LỖI >>>
    def display_heatmap(self):
        """Cập nhật heatmap trên cửa sổ chính, bao gồm colorbar và trục."""
        try: # Thêm try-except bao quát để bắt lỗi vẽ tiềm ẩn
            if self.current_data_matrix is not None and self.current_data_matrix.size > 0:
                rows, cols = self.current_data_matrix.shape
                # --- Xác định tiêu đề plot ---
                heatmap_display_title = f"Heatmap Dữ liệu ({rows}x{cols})"
                plot_title = f"Dữ liệu ({rows}x{cols})"
                if self.current_data_is_compatible:
                    if self.current_data_origin == 'csv':
                        plot_title = f"Dữ liệu CSV ({rows}x{cols}) - Sẵn sàng tính AI/Lưu"
                    elif self.current_data_origin == 'sensor_capture':
                        plot_title = f"Dữ liệu Cảm biến ({rows}x{cols}) - Sẵn sàng tính AI/Lưu"
                self.heatmap_title.setText(heatmap_display_title)

                # --- Cập nhật dữ liệu và màu sắc ---
                self.heatmap_im.set_data(np.flip(self.current_data_matrix,axis = 0 ))
                # Tính min/max, xử lý NaN nếu có
                min_val = np.nanmin(self.current_data_matrix) if np.any(np.isnan(self.current_data_matrix)) else np.min(self.current_data_matrix)
                max_val = np.nanmax(self.current_data_matrix) if np.any(np.isnan(self.current_data_matrix)) else np.max(self.current_data_matrix)
                min_val = 0 if np.isnan(min_val) else min_val # Mặc định min là 0 nếu toàn NaN
                max_val = 1 if np.isnan(max_val) else max_val # Mặc định max là 1 nếu toàn NaN

                # Đảm bảo max > min để tránh lỗi colorbar
                if max_val <= min_val:
                    max_val = min_val + 1 # Hoặc một giá trị phù hợp khác

                # === CHỈ CẦN SET CLIM CHO HEATMAP IMAGE ===
                self.heatmap_im.set_clim(vmin=min_val, vmax=max_val)
                # ==========================================

                # --- Hiển thị trục và đặt tiêu đề ---
                self.ax.xaxis.set_visible(True)
                self.ax.yaxis.set_visible(True)
                self.ax.set_title(plot_title, color='white')

                # === KIỂM TRA VÀ TẠO COLORBAR NẾU CHƯA CÓ ===
                # Điều này thường chỉ cần thiết nếu ax bị clear hoàn toàn trước đó,
                # nhưng để chắc chắn, ta kiểm tra self.cbar
                if self.cbar is None:
                    print("Recreating colorbar...") # Debug
                    self.cbar = self.figure.colorbar(self.heatmap_im, ax=self.ax)
                    self.cbar.ax.yaxis.set_tick_params(color='white')
                    plt.setp(plt.getp(self.cbar.ax.axes, 'yticklabels'), color='white')
                # ============================================

            else: # Trường hợp không có dữ liệu (None hoặc rỗng)
                 # --- Reset Heatmap về trạng thái rỗng ---
                 nan_data = np.full((self.expected_rows, self.expected_cols), np.nan)
                 self.heatmap_im.set_data(nan_data)
                 # Reset clim về mặc định nhỏ

                 self.heatmap_im.set_clim(vmin=0, vmax=1)
                 # --- Ẩn trục ---
                 self.ax.xaxis.set_visible(False)
                 self.ax.yaxis.set_visible(False)
                 # --- Đặt lại tiêu đề ---
                 self.ax.set_title("Chưa có dữ liệu", color='white')
                 self.heatmap_title.setText("Heatmap Dữ liệu:")

            # --- Vẽ lại canvas và điều chỉnh layout ---
            try:
                # Gọi tight_layout trước khi vẽ có thể tốt hơn
                self.figure.tight_layout()
            except ValueError as e:
                print(f"Warning: tight_layout failed: {e}")
            self.canvas.draw() # Yêu cầu canvas vẽ lại tất cả

        except Exception as e:
             print(f"Error during display_heatmap: {e}")
             import traceback
             traceback.print_exc()
    # --- Hàm calculate_and_display_arch_index giữ nguyên logic tính toán ---
    # Chỉ cần đảm bảo nó kiểm tra self.current_data_is_compatible
    def calculate_and_display_arch_index(self):
        if not self.current_data_is_compatible or self.current_data_matrix is None:
            QMessageBox.warning(self, "Dữ Liệu Không Phù Hợp", "Chức năng này yêu cầu dữ liệu 60x60 hợp lệ.")
            # Đặt lại label AI về trạng thái chưa tính
            self.ai_result_label.setText("Chỉ số Arch Index: Yêu cầu dữ liệu 60x60")
            return
        try:
            self.update_status("Đang xử lý và tính Arch Index...", duration=0) # Hiển thị trạng thái
            QApplication.processEvents() # Cho phép UI cập nhật

            # --- Các bước xử lý dữ liệu Arch Index ---
            if not archindex.check_data(self.current_data_matrix):
                 self.update_status("Lỗi dữ liệu không hợp lệ (NaN, Inf).", is_error=True)
                 self.ai_result_label.setText("Chỉ số Arch Index: Lỗi dữ liệu")
                 return
            # Chuyển đổi giá trị (giả sử đầu vào 0-5V?) -> Chỉnh input_max nếu cần
            #processed_matrix = archindex.spin_matrix(self.current_data_matrix)
            processed_matrix = archindex.convert_values(self.current_data_matrix, input_max=5.0)
            processed_matrix = archindex.Isolated_point_removal(processed_matrix)
            processed_matrix = archindex.toes_remove(processed_matrix, threshold=15)
            processed_matrix = archindex.toes_remain_removes(processed_matrix)

            # --- Tính AI cho cả hai chân ---
            ai_results = archindex.compute_arch_index(processed_matrix)

            # --- Hiển thị kết quả ---
            if ai_results and ai_results['left']['AI'] is not None and ai_results['right']['AI'] is not None:
                # Format kết quả cho cả hai chân
                result_text = (f"Trái: AI={ai_results['left']['AI']:.3f} ({ai_results['left']['type']}) | "
                               f"Phải: AI={ai_results['right']['AI']:.3f} ({ai_results['right']['type']})")
                self.ai_result_label.setText(result_text)
                self.update_status("Tính Arch Index thành công.")
            elif ai_results: # Trường hợp tính được 1 chân hoặc có lỗi cụ thể
                 left_msg = f"Trái: {ai_results['left']['type']}" if ai_results['left']['AI'] is None else f"Trái: AI={ai_results['left']['AI']:.3f} ({ai_results['left']['type']})"
                 right_msg = f"Phải: {ai_results['right']['type']}" if ai_results['right']['AI'] is None else f"Phải: AI={ai_results['right']['AI']:.3f} ({ai_results['right']['type']})"
                 self.ai_result_label.setText(f"{left_msg} | {right_msg}")
                 self.update_status(f"Không thể tính đầy đủ Arch Index.", is_error=True)
            else: # Trường hợp lỗi chung từ compute_arch_index
                 self.ai_result_label.setText("Chỉ số Arch Index: Lỗi tính toán")
                 self.update_status(f"Lỗi khi gọi compute_arch_index.", is_error=True)

        except Exception as e:
            self.update_status(f"Lỗi trong quá trình tính Arch Index: {e}", is_error=True, duration=10000)
            self.ai_result_label.setText("Chỉ số Arch Index: Lỗi")
            QMessageBox.critical(self, "Lỗi Tính Toán", f"Đã xảy ra lỗi: {e}")


    # --- Hàm save_patient giữ nguyên logic ---
    # Chỉ cần đảm bảo nó kiểm tra self.current_data_is_compatible
    def save_patient(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng nhập Họ và tên và Số điện thoại.")
            return

        # Kiểm tra dữ liệu tương thích
        if not self.current_data_is_compatible or self.current_data_matrix is None:
            QMessageBox.warning(self, "Dữ Liệu Không Phù Hợp", "Chức năng Lưu Bệnh Nhân yêu cầu dữ liệu 60x60 hợp lệ.")
            return

        # ... (Phần còn lại của save_patient giữ nguyên) ...
        patient_id = f"P{uuid.uuid4().hex[:10].upper()}"
        patient_data = { # Tạo dict dữ liệu bệnh nhân }
            "resourceType": "Patient", "id": patient_id, "name": [{"use": "official", "text": name}], "phone": phone,
            **({"gender": self.gender_input.text().strip()} if self.gender_input.text().strip() else {}),
            **({"birthDate": self.birthdate_input.text().strip()} if self.birthdate_input.text().strip() else {}),
            **({"address": self.address_input.text().strip()} if self.address_input.text().strip() else {}),
        }
        try: # Lưu thông tin bệnh nhân
            self.update_status(f"Đang lưu thông tin bệnh nhân ID: {patient_id}...")
            QApplication.processEvents()
            save_result = self.db_manager.save_patient(patient_data)
            # ... (Xử lý kết quả save_result) ...
            if "thành công" not in save_result.lower():
                 self.update_status(f"Lỗi lưu thông tin: {save_result}", is_error=True, duration=10000)
                 QMessageBox.critical(self, "Lỗi Lưu Bệnh Nhân", save_result)
                 return
            else:
                 self.update_status(f"Lưu thông tin BN {patient_id} thành công. Đang lưu dữ liệu bàn chân (60x60)...")
                 QApplication.processEvents()

        except Exception as e: # Xử lý lỗi lưu bệnh nhân
            self.update_status(f"Lỗi nghiêm trọng khi gọi save_patient: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Database", f"Lỗi kết nối hoặc lưu database: {e}")
            return

        # Lưu dữ liệu CSV (60x60)
        self.temp_csv_path = None
        try: # Lưu file CSV tạm và gọi manager
            temp_dir = "temp_sensor_data"
            os.makedirs(temp_dir, exist_ok=True)
            self.temp_csv_path = os.path.join(temp_dir, f"data_{patient_id}_60x60.csv")
            np.savetxt(self.temp_csv_path, self.current_data_matrix, delimiter=',')
            data_file_to_save = self.temp_csv_path
            print(f"Saved 60x60 data temporarily to: {self.temp_csv_path} for DB")

            data_save_result = self.db_manager.save_patient_csv_data(patient_id, data_file_to_save)
            # ... (Xử lý kết quả data_save_result) ...
            if "thành công" in data_save_result.lower():
                self.update_status(f"Lưu bệnh nhân ({patient_id}) và dữ liệu 60x60 thành công!", duration=8000)
                QMessageBox.information(self, "Thành Công", f"Đã lưu thành công bệnh nhân:\nTên: {name}\nID: {patient_id}\nvà dữ liệu bàn chân 60x60 liên quan.")
                self.clear_all() # Xóa form sau khi lưu thành công
            else:
                self.update_status(f"Lỗi lưu dữ liệu CSV (60x60): {data_save_result}", is_error=True, duration=10000)
                QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Lưu thông tin bệnh nhân thành công, nhưng lưu dữ liệu CSV 60x60 thất bại:\n{data_save_result}")

            # ... (Xóa file tạm) ...
            if self.temp_csv_path and os.path.exists(self.temp_csv_path):
                try:
                    os.remove(self.temp_csv_path)
                    print(f"Removed temporary file: {self.temp_csv_path}")
                    self.temp_csv_path = None
                except OSError as e:
                    print(f"Warning: Could not remove temporary file {self.temp_csv_path}: {e}")

        except Exception as e: # Xử lý lỗi lưu CSV
            self.update_status(f"Lỗi khi lưu dữ liệu CSV 60x60 vào DB: {e}", is_error=True, duration=10000)
            QMessageBox.critical(self, "Lỗi Lưu Dữ Liệu", f"Đã xảy ra lỗi khi chuẩn bị hoặc lưu dữ liệu CSV 60x60: {e}")


# --- END OF FILE gui/create.py ---