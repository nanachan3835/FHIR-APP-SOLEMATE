# --- START OF FILE gui/serial_heatmap.py ---

import sys
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import serial.tools.list_ports
import time

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                             QLabel, QMessageBox, QApplication)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt # Thêm Qt

# --- Constants ---
EXPECTED_ROWS = 60
EXPECTED_COLS = 60
DEFAULT_BAUDRATE = 115200

class SerialHeatmapWindow(QWidget):
    # Signal để gửi dữ liệu ma trận đã chụp về cửa sổ chính
    # Sử dụng 'object' để có thể truyền numpy array
    data_captured = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Sensor Heatmap (30x16)")
        self.setGeometry(150, 150, 700, 650) # Kích thước cửa sổ

        # --- Biến trạng thái ---
        self.serial_connection = None
        self.animation = None
        self.latest_matrix = np.zeros((EXPECTED_ROWS, EXPECTED_COLS)) # Khởi tạo ma trận rỗng
        self.reading_frame = False
        self.data_buffer = []
        self.is_running = False # Cờ kiểm tra animation đang chạy hay không

        # --- UI Elements ---
        main_layout = QVBoxLayout(self)

        # -- Phần điều khiển Serial --
        control_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Làm mới Ports")
        self.connect_button = QPushButton("Kết nối & Bắt đầu")
        control_layout.addWidget(QLabel("Chọn Cổng Serial:"))
        control_layout.addWidget(self.port_combo)
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.connect_button)
        main_layout.addLayout(control_layout)

        # -- Phần Heatmap Matplotlib --
        # Tạo Figure và FigureCanvas
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111) # Add axes to the figure
        self.heatmap_im = self.ax.imshow(self.latest_matrix, cmap='jet', interpolation='nearest', origin='lower', vmin=0, vmax=255)
        self.figure.colorbar(self.heatmap_im, ax=self.ax)
        self.ax.set_title(f"Chờ kết nối... ({EXPECTED_ROWS}x{EXPECTED_COLS})")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.figure.tight_layout()
        main_layout.addWidget(self.canvas)

        # -- Toolbar Matplotlib (Tùy chọn) --
        # self.toolbar = NavigationToolbar(self.canvas, self)
        # main_layout.addWidget(self.toolbar)

        # -- Nút Chụp và Đóng --
        action_layout = QHBoxLayout()
        self.capture_button = QPushButton("Chụp Heatmap Hiện Tại")
        self.close_button = QPushButton("Đóng Cửa Sổ")
        action_layout.addWidget(self.capture_button)
        action_layout.addWidget(self.close_button)
        main_layout.addLayout(action_layout)

        # --- Kết nối Signals ---
        self.refresh_button.clicked.connect(self.populate_serial_ports)
        self.connect_button.clicked.connect(self.toggle_connection)
        self.capture_button.clicked.connect(self.capture_data)
        self.close_button.clicked.connect(self.close)

        # --- Khởi tạo ---
        self.capture_button.setEnabled(False) # Vô hiệu hóa nút chụp ban đầu
        self.populate_serial_ports()          # Tải danh sách cổng serial khi mở

    def populate_serial_ports(self):
        """Lấy danh sách cổng serial và cập nhật ComboBox."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.port_combo.addItem("Không tìm thấy cổng nào")
            self.port_combo.setEnabled(False)
            self.connect_button.setEnabled(False)
        else:
            for port in sorted(ports):
                self.port_combo.addItem(f"{port.device} - {port.description}")
            self.port_combo.setEnabled(True)
            self.connect_button.setEnabled(True)
            # Tự động chọn cổng đầu tiên nếu có
            self.port_combo.setCurrentIndex(0)

    def toggle_connection(self):
        """Kết nối/Ngắt kết nối tới cổng serial và bắt đầu/dừng animation."""
        if self.serial_connection is None:
            # --- Kết nối ---
            selected_text = self.port_combo.currentText()
            if "Không tìm thấy" in selected_text:
                QMessageBox.warning(self, "Lỗi", "Không có cổng Serial nào được chọn.")
                return

            # Trích xuất tên cổng từ text trong combobox
            port_name = selected_text.split(" - ")[0]

            try:
                self.serial_connection = serial.Serial(port_name, DEFAULT_BAUDRATE, timeout=0.1) # Timeout ngắn để không block animation quá lâu
                print(f"Đã kết nối tới {port_name} at {DEFAULT_BAUDRATE}")
                self.connect_button.setText("Ngắt kết nối & Dừng")
                self.port_combo.setEnabled(False)
                self.refresh_button.setEnabled(False)
                self.capture_button.setEnabled(True)
                self.start_animation()
            except serial.SerialException as e:
                QMessageBox.critical(self, "Lỗi Kết Nối Serial", f"Không thể mở cổng {port_name}:\n{e}")
                self.serial_connection = None # Đảm bảo reset nếu lỗi
        else:
            # --- Ngắt kết nối ---
            self.stop_animation()
            try:
                self.serial_connection.close()
                print(f"Đã đóng cổng {self.serial_connection.port}")
            except Exception as e:
                print(f"Lỗi khi đóng cổng serial: {e}") # Vẫn tiếp tục ngay cả khi có lỗi đóng
            finally:
                 self.serial_connection = None
                 self.connect_button.setText("Kết nối & Bắt đầu")
                 self.port_combo.setEnabled(True)
                 self.refresh_button.setEnabled(True)
                 self.capture_button.setEnabled(False)
                 self.ax.set_title(f"Đã ngắt kết nối ({EXPECTED_ROWS}x{EXPECTED_COLS})")
                 self.canvas.draw_idle() # Cập nhật tiêu đề trên plot

    def start_animation(self):
        """Bắt đầu Matplotlib animation để cập nhật heatmap."""
        if self.serial_connection and not self.is_running:
            self.is_running = True
            # Reset trạng thái đọc frame
            self.reading_frame = False
            self.data_buffer = []
            print("Bắt đầu chờ dấu '-----'...")
            # Interval thấp để cập nhật nhanh, nhưng không nên quá thấp để tránh quá tải CPU
            self.animation = FuncAnimation(self.figure, self.update_heatmap,
                                           interval=50, # Cập nhật mỗi 50ms
                                           blit=False, # Blit=True có thể nhanh hơn nhưng phức tạp hơn về return value
                                           cache_frame_data=False) # Quan trọng để tránh memory leak
            self.canvas.draw_idle() # Vẽ lần đầu
            print("Animation started.")

    def stop_animation(self):
        """Dừng Matplotlib animation."""
        if self.animation is not None:
            # Ngừng animation một cách an toàn
            self.animation.event_source.stop()
            self.animation = None # Xóa tham chiếu
            self.is_running = False
            print("Animation stopped.")

    def update_heatmap(self, frame):
        """Hàm được gọi bởi FuncAnimation để đọc serial và cập nhật plot."""
        if self.serial_connection is None or not self.serial_connection.is_open or not self.is_running:
            return # Không làm gì nếu không kết nối hoặc không đang chạy

        # Đọc nhiều dòng trong một lần gọi để cố gắng bắt kịp dữ liệu
        lines_processed_this_call = 0
        max_lines_per_call = 50 # Giới hạn số dòng đọc mỗi lần để không block quá lâu

        while lines_processed_this_call < max_lines_per_call:
            try:
                # Đọc non-blocking hoặc với timeout ngắn
                if self.serial_connection.in_waiting > 0:
                    line_bytes = self.serial_connection.readline()
                    if not line_bytes:
                        break # Không còn gì để đọc ngay lập tức
                else:
                    break # Không có dữ liệu đang chờ

                lines_processed_this_call += 1

                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except Exception as decode_err:
                    print(f"Decode error: {decode_err}")
                    continue

                # print(f"Line: {line}") # Debug

                if "-----" in line:
                    if self.reading_frame:
                        print(f"Warning: Separator mid-frame ({len(self.data_buffer)} rows). Resetting.")
                        self.reading_frame = False
                        self.data_buffer = []
                    else:
                        self.reading_frame = True
                        self.data_buffer = []
                        # print("Separator found. Reading frame...")
                    continue # Xử lý xong separator, đọc dòng tiếp

                if not self.reading_frame or not line:
                    continue # Bỏ qua nếu không đọc frame hoặc dòng trống

                # --- Xử lý dòng dữ liệu ---
                try:
                    parts = line.split(',')
                    valid_parts = [p for p in parts if p.strip()]
                    values = [int(p) for p in valid_parts]

                    if len(values) == EXPECTED_COLS:
                        self.data_buffer.append(values)

                        # Kiểm tra đủ hàng
                        if len(self.data_buffer) == EXPECTED_ROWS:
                            # print("Complete frame received. Updating heatmap.")
                            self.latest_matrix = np.array(self.data_buffer) # Cập nhật ma trận mới nhất
                            self.heatmap_im.set_data(self.latest_matrix) # Cập nhật dữ liệu plot
                            self.ax.set_title(f"Live Heatmap ({EXPECTED_ROWS}x{EXPECTED_COLS})")
                            self.figure.canvas.draw_idle() # Yêu cầu vẽ lại

                            # Reset cho frame tiếp theo
                            self.reading_frame = False
                            self.data_buffer = []
                            # Không 'break' ở đây, tiếp tục đọc nếu còn dữ liệu trong buffer serial
                    elif len(self.data_buffer) > EXPECTED_ROWS:
                         print(f"Warning: Buffer overflow ({len(self.data_buffer)} rows). Resetting.")
                         self.reading_frame = False
                         self.data_buffer = []

                except ValueError as ve:
                    print(f"Data parse error: '{line}'. {ve}. Skipping.")
                except Exception as e:
                    print(f"Unexpected processing error: {e}")
                    self.reading_frame = False # Reset nếu có lỗi lạ
                    self.data_buffer = []


            except serial.SerialException as se:
                print(f"Serial error during read: {se}")
                self.stop_animation() # Dừng animation nếu lỗi serial
                self.toggle_connection() # Cố gắng ngắt kết nối sạch sẽ
                break # Thoát vòng lặp đọc
            except Exception as e:
                 print(f"Unexpected error in update loop: {e}")
                 self.stop_animation()
                 break

        # Hàm update của FuncAnimation nên trả về một iterable các artists đã thay đổi
        # nhưng với blit=False, việc này không bắt buộc.
        # return [self.heatmap_im] # Bỏ comment nếu dùng blit=True

    def capture_data(self):
        """Chụp ma trận heatmap hiện tại và gửi tín hiệu đi."""
        if self.latest_matrix is not None and self.is_running:
             print("Capturing current heatmap data...")
             # Tạo bản sao để tránh thay đổi ngoài ý muốn
             captured_matrix = self.latest_matrix.copy()
             # Gửi tín hiệu chứa dữ liệu đã chụp
             self.data_captured.emit(captured_matrix)
             QMessageBox.information(self, "Đã Chụp", "Dữ liệu heatmap đã được chụp và gửi về cửa sổ chính.")
             # Tự động đóng cửa sổ sau khi chụp
             self.close()
        else:
             QMessageBox.warning(self, "Chưa Sẵn Sàng", "Chưa có dữ liệu heatmap hợp lệ hoặc quá trình đọc chưa bắt đầu.")

    def closeEvent(self, event):
        """Đảm bảo dừng animation và đóng cổng serial khi đóng cửa sổ."""
        print("Closing heatmap window...")
        self.stop_animation()
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                print(f"Serial port {self.serial_connection.port} closed on exit.")
            except Exception as e:
                print(f"Error closing serial port on exit: {e}")
        super().closeEvent(event) # Chấp nhận sự kiện đóng

# --- Main để test cửa sổ độc lập (Tùy chọn) ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SerialHeatmapWindow()
    window.show()
    sys.exit(app.exec_())

# --- END OF FILE gui/serial_heatmap.py ---