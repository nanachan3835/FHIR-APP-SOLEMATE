# --- START OF FILE gui/serial_heatmap.py ---

import sys
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import serial.tools.list_ports
import time

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                             QLabel, QMessageBox, QApplication)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt

# --- Constants ---
EXPECTED_ROWS = 30
EXPECTED_COLS = 30
DEFAULT_BAUDRATE = 115200

class SerialHeatmapWindow(QWidget):
    data_captured = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Live Sensor Heatmap ({EXPECTED_ROWS}x{EXPECTED_COLS})")
        self.setGeometry(150, 150, 700, 650)

        self.serial_connection = None
        self.animation = None
        self.latest_matrix = np.zeros((EXPECTED_ROWS, EXPECTED_COLS), dtype=int)
        self.reading_frame = False
        self.data_buffer = []
        self.is_running = False
        # === THÊM: Biến lưu giá trị max của frame trước ===
        self.last_frame_max = 1 # Khởi tạo là 1 để tránh lỗi chia cho 0 hoặc range màu quá hẹp ban đầu

        main_layout = QVBoxLayout(self)

        # -- Serial control section --
        control_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh Ports")
        self.connect_button = QPushButton("Connect & Start")
        control_layout.addWidget(QLabel("Select Serial Port:"))
        control_layout.addWidget(self.port_combo)
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.connect_button)
        main_layout.addLayout(control_layout)

        # -- Matplotlib Heatmap section --
        self.figure = Figure(figsize=(6, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        # Khởi tạo heatmap, đặt vmin=0, vmax ban đầu là giá trị nhỏ > 0
        self.heatmap_im = self.ax.imshow(self.latest_matrix, cmap='jet', interpolation='gaussian', origin='lower', vmin=0, vmax=self.last_frame_max)
        # Lưu tham chiếu đến colorbar để cập nhật sau
        self.cbar = self.figure.colorbar(self.heatmap_im, ax=self.ax)
        self.ax.set_title(f"Waiting for connection... ({EXPECTED_ROWS}x{EXPECTED_COLS})")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.figure.tight_layout()
        main_layout.addWidget(self.canvas)

        # -- Action buttons section --
        action_layout = QHBoxLayout()
        self.capture_button = QPushButton("Capture Current Heatmap")
        self.close_button = QPushButton("Close Window")
        action_layout.addWidget(self.capture_button)
        action_layout.addWidget(self.close_button)
        main_layout.addLayout(action_layout)

        # --- Connect Signals ---
        self.refresh_button.clicked.connect(self.populate_serial_ports)
        self.connect_button.clicked.connect(self.toggle_connection)
        self.capture_button.clicked.connect(self.capture_data)
        self.close_button.clicked.connect(self.close)

        # --- Initial setup ---
        self.capture_button.setEnabled(False)
        self.populate_serial_ports()

    # ... (populate_serial_ports, toggle_connection, start_animation, stop_animation giữ nguyên) ...
    def populate_serial_ports(self):
        """Fetches available serial ports and updates the ComboBox."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.port_combo.addItem("No ports found")
            self.port_combo.setEnabled(False)
            self.connect_button.setEnabled(False)
        else:
            for port in sorted(ports):
                self.port_combo.addItem(f"{port.device} - {port.description if port.description != 'n/a' else 'Unknown Device'}")
            self.port_combo.setEnabled(True)
            self.connect_button.setEnabled(True)
            if self.port_combo.count() > 0:
                self.port_combo.setCurrentIndex(0)

    def toggle_connection(self):
        """Connects/Disconnects from the selected serial port and starts/stops the animation."""
        if self.serial_connection is None:
            selected_text = self.port_combo.currentText()
            if "No ports found" in selected_text or not selected_text:
                QMessageBox.warning(self, "Connection Error", "No serial port selected or available.")
                return
            port_name = selected_text.split(" - ")[0]
            try:
                self.serial_connection = serial.Serial(port_name, DEFAULT_BAUDRATE, timeout=0.1)
                print(f"Successfully connected to {port_name} at {DEFAULT_BAUDRATE} baud.")
                self.connect_button.setText("Disconnect & Stop")
                self.port_combo.setEnabled(False)
                self.refresh_button.setEnabled(False)
                self.capture_button.setEnabled(True)
                self.start_animation()
            except serial.SerialException as e:
                QMessageBox.critical(self, "Serial Connection Error", f"Failed to open port {port_name}:\n{e}")
                self.serial_connection = None
        else:
            self.stop_animation()
            try:
                self.serial_connection.close()
                print(f"Closed serial port {self.serial_connection.port}")
            except Exception as e:
                print(f"Error closing serial port: {e}")
            finally:
                 self.serial_connection = None
                 self.connect_button.setText("Connect & Start")
                 self.port_combo.setEnabled(True)
                 self.refresh_button.setEnabled(True)
                 self.capture_button.setEnabled(False)
                 self.ax.set_title(f"Disconnected ({EXPECTED_ROWS}x{EXPECTED_COLS})")
                 self.canvas.draw_idle()

    def start_animation(self):
        """Starts the Matplotlib animation to update the heatmap."""
        if self.serial_connection and not self.is_running:
            self.is_running = True
            self.reading_frame = False
            self.data_buffer = []
            self.serial_connection.reset_input_buffer()
            print("Waiting for frame marker '-----'...")
            self.animation = FuncAnimation(self.figure, self.update_heatmap,
                                           interval=50, # Thay đổi khoảng thời gian nếu cần
                                           blit=False,
                                           cache_frame_data=False)
            self.canvas.draw_idle()
            print("Animation started.")

    def stop_animation(self):
        """Stops the Matplotlib animation."""
        if self.animation is not None:
            self.animation.event_source.stop()
            self.animation = None
            self.is_running = False
            print("Animation stopped.")


    def update_heatmap(self, frame):
        """Reads serial data, processes it, updates plot with dynamic vmax."""
        if self.serial_connection is None or not self.serial_connection.is_open or not self.is_running:
            return

        lines_processed_this_call = 0
        max_lines_per_call = 70 # Giới hạn số dòng đọc trong mỗi lần gọi để tránh treo GUI
        frame_completed = False # Cờ kiểm tra xem có frame nào hoàn thành trong lần gọi này không

        while lines_processed_this_call < max_lines_per_call:
            try:
                if self.serial_connection.in_waiting > 0:
                    line_bytes = self.serial_connection.readline()
                    if not line_bytes: break
                else: break

                lines_processed_this_call += 1

                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except Exception as decode_err:
                    print(f"Decode error: {decode_err}")
                    continue

                if "-----" in line:
                    if self.reading_frame:
                        if self.data_buffer:
                            print(f"Warning: Separator found mid-frame ({len(self.data_buffer)}/{EXPECTED_ROWS} rows). Discarding.")
                        self.reading_frame = False
                        self.data_buffer = []
                    else:
                        self.reading_frame = True
                        self.data_buffer = []
                    continue

                if not self.reading_frame or not line:
                    continue

                # --- Process Data Row (Target: 60 columns, replace errors/missing with 0) ---
                row_values = []
                parts = line.split(',')
                for i in range(EXPECTED_COLS):
                    value = 0
                    if i < len(parts):
                        p_stripped = parts[i].strip()
                        if p_stripped:
                            try: value = int(p_stripped)
                            except ValueError: pass # Lỗi thì value vẫn là 0
                    row_values.append(value)

                self.data_buffer.append(row_values)

                # --- Check if frame is complete ---
                if len(self.data_buffer) == EXPECTED_ROWS:
                    # print(f"Complete frame received ({EXPECTED_ROWS} rows). Processing...")
                    self.latest_matrix = np.array(self.data_buffer, dtype=int)
                    frame_completed = True # Đánh dấu frame hoàn thành

                    # === TÍNH TOÁN VÀ CẬP NHẬT VMAX ===
                    current_max = np.max(self.latest_matrix)
                    # Chỉ cập nhật vmax nếu max mới > 0 (tránh trường hợp toàn 0)
                    # và khác biệt đáng kể so với max cũ (tránh cập nhật liên tục nếu nhiễu nhỏ)
                    # hoặc nếu last_frame_max vẫn là giá trị khởi tạo
                    if current_max > 0 :
                         # Có thể thêm điều kiện lọc nhiễu ở đây nếu muốn
                         # Ví dụ: chỉ cập nhật nếu current_max > self.last_frame_max * 0.1
                         self.last_frame_max = current_max
                    elif np.sum(self.latest_matrix) == 0:
                         # Nếu cả frame toàn 0, đặt vmax=1 để tránh lỗi range màu
                         self.last_frame_max = 1

                    # Đảm bảo vmax luôn lớn hơn vmin (là 0)
                    vmax_to_set = max(1, self.last_frame_max)

                    self.heatmap_im.set_data(self.latest_matrix)
                    self.heatmap_im.set_clim(vmin=0, vmax=vmax_to_set) # Cập nhật giới hạn màu
                    # ====================================

                    self.ax.set_title(f"Live Heatmap ({EXPECTED_ROWS}x{EXPECTED_COLS}) - Max: {vmax_to_set}") # Hiển thị max hiện tại

                    # Reset cho frame tiếp theo
                    self.reading_frame = False
                    self.data_buffer = []
                    # Không break ở đây, tiếp tục đọc nếu còn data trong buffer

                elif len(self.data_buffer) > EXPECTED_ROWS:
                    print(f"Warning: Buffer overflow ({len(self.data_buffer)} rows). Resetting.")
                    self.reading_frame = False
                    self.data_buffer = []

            except serial.SerialException as se:
                print(f"Serial error during read: {se}")
                QMessageBox.critical(self, "Serial Error", f"Communication error:\n{se}")
                self.stop_animation()
                self.toggle_connection()
                break
            except Exception as e:
                 print(f"Unexpected error in update loop: {e}")
                 import traceback
                 traceback.print_exc()
                 self.stop_animation()
                 break

        # Chỉ yêu cầu vẽ lại canvas nếu có frame hoàn thành trong lần gọi này
        if frame_completed:
             # === CẬP NHẬT COLORBAR ===
             # Cập nhật giới hạn của colorbar để khớp với heatmap
             self.cbar.mappable.set_clim(vmin=0, vmax=max(1, self.last_frame_max))
             self.cbar._draw_all() # Vẽ lại colorbar
             # =========================
             self.figure.canvas.draw_idle()


    def capture_data(self):
        """Captures the current 60x60 heatmap data and emits the signal."""
        # Nên cho phép chụp ngay cả khi animation không chạy, miễn là có dữ liệu hợp lệ
        if self.latest_matrix is not None:
             if self.latest_matrix.shape == (EXPECTED_ROWS, EXPECTED_COLS):
                 print(f"Capturing heatmap data (Max value: {self.last_frame_max})...")
                 captured_matrix = self.latest_matrix.copy()
                 self.data_captured.emit(captured_matrix)
                 QMessageBox.information(self, "Capture Successful", f"Data ({EXPECTED_ROWS}x{EXPECTED_COLS}) captured.")
                 self.close()
             else:
                  QMessageBox.warning(self, "Capture Error", f"Internal error: Matrix shape is not {EXPECTED_ROWS}x{EXPECTED_COLS}.")
        else:
             QMessageBox.warning(self, "Capture Error", "No valid heatmap data available to capture.")


    def closeEvent(self, event):
        """Ensures resources are released when the window is closed."""
        print("Closing heatmap window...")
        self.stop_animation()
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                print(f"Serial port {self.serial_connection.port} closed on exit.")
            except Exception as e:
                print(f"Error closing serial port on exit: {e}")
        super().closeEvent(event)

# Optional: Main block for testing this window independently
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SerialHeatmapWindow()
    window.show()
    sys.exit(app.exec_())

# --- END OF FILE gui/serial_heatmap.py ---