# --- START OF FILE main.py ---

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt

# --- Import Core Components ---
try:
    # ... (các import khác giữ nguyên) ...
    from gui.home import HomePage # Đảm bảo import này đúng
    from gui.create import CreatePatientPage
    from gui.load import LoadPatientPage
    from database.manager_mongodb_2 import MongoDBManager
except ImportError as e:
    # ... (xử lý lỗi import giữ nguyên) ...
    sys.exit(1)
except Exception as ge:
    print(f"Fatal General Error in main.py: {ge}")
    sys.exit(1)


# --- Main Application Window ---
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoleMate - Quản Lý & Phân Tích Dấu Chân") # Đổi tiêu đề nếu muốn
        self.setGeometry(50, 50, 700, 800) # Có thể chỉnh lại kích thước cửa sổ

        # --- Database Connection ---
        self.db_manager = self.setup_database()
        if not self.db_manager:
            sys.exit(1)

        # --- Central Widget and Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # === THAY ĐỔI CHÍNH: Đặt màu nền cho central_widget ===
        self.central_widget.setObjectName("MainBackground") # Đặt tên để CSS hoạt động
        self.central_widget.setStyleSheet("""
            #MainBackground {
                background-color: #003366; /* Màu xanh nước biển đậm */
            }
        """)
        # ====================================================

        # Layout cho central_widget sẽ chứa QStackedWidget
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0) # Không cần margin ở layout này

        # --- Stacked Widget for Pages ---
        self.stacked_widget = QStackedWidget()
        # Stacked widget không cần màu nền riêng vì central_widget đã có
        # self.stacked_widget.setStyleSheet("background-color: transparent;") # Hoặc đặt transparent
        self.main_layout.addWidget(self.stacked_widget)

        # --- Instantiate Pages ---
        self.home_page = HomePage(self.stacked_widget, self.db_manager)
        self.create_page = CreatePatientPage(self.stacked_widget, self.db_manager)
        self.load_page = LoadPatientPage(self.stacked_widget, self.db_manager)

        # --- Add Pages to Stack ---
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.create_page)
        self.stacked_widget.addWidget(self.load_page)

        self.stacked_widget.setCurrentIndex(0)

    def setup_database(self) -> MongoDBManager | None:
        # ... (hàm setup_database giữ nguyên) ...
        print("Initializing Database Connection...")
        try:
            manager = MongoDBManager()
            if manager.db_connection.db is not None:
                print("Database connection successful.")
                return manager
            else:
                 error_message = "Lỗi Kết Nối Database:\n\nKhông thể kết nối tới MongoDB.\nHãy đảm bảo MongoDB đang chạy trên localhost:27017."
                 QMessageBox.critical(None, "Lỗi Database", error_message)
                 print(error_message)
                 return None
        except Exception as e:
            error_message = f"Lỗi Khởi Tạo Database:\n\n{e}\n\nKiểm tra cài đặt và dịch vụ MongoDB."
            QMessageBox.critical(None, "Lỗi Database", error_message)
            print(error_message)
            return None


    def closeEvent(self, event):
        # ... (hàm closeEvent giữ nguyên) ...
        print("Closing application...")
        if self.db_manager:
            self.db_manager.close_connection()
        temp_dir = "temp_sensor_data"
        # ... (xóa temp_dir giữ nguyên) ...
        event.accept()


# --- Application Entry Point ---
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    window = MainApp()
    if window.db_manager:
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(1)

# --- END OF FILE main.py ---