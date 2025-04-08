# --- START OF FILE main.py ---
import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt

# --- Import Core Components ---
try:

    from database.manager_mongodb_2 import MongoDBManager
    from gui.home import HomePage
    from gui.create import CreatePatientPage
    from gui.load import LoadPatientPage
except ImportError as e:
    print(f"Fatal Import Error in main.py: {e}")
    print("Please ensure the project structure is correct and all dependencies are installed.")
    # Show a simple message box if GUI is available
    try:
        app = QApplication([])
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Lỗi Khởi Tạo")
        msg_box.setText(f"Không thể tải các thành phần cần thiết: {e}\n\nVui lòng kiểm tra cài đặt và cấu trúc thư mục.")
        msg_box.exec_()
    except Exception:
        pass # Ignore if GUI can't even start
    sys.exit(1)
except Exception as ge: # Catch other potential startup errors
     print(f"Fatal General Error in main.py: {ge}")
     sys.exit(1)


# --- Main Application Window ---
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FHIR - Ứng Dụng Quản Lý Bệnh Nhân & Phân Tích Dấu Chân")
        self.setGeometry(50, 50, 1100, 750) # Adjust initial size

        # --- Database Connection ---
        # Encapsulate DB setup
        self.db_manager = self.setup_database()
        if not self.db_manager:
             # Error handled in setup_database, exit here
             sys.exit(1)

        # --- Central Widget and Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget) # Use QVBoxLayout for the main window
        self.main_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main layout

        # --- Stacked Widget for Pages ---
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget) # Add stack to the main layout

        # --- Instantiate Pages ---
        # Pass the db_manager instance to pages that need it
        self.home_page = HomePage(self.stacked_widget, self.db_manager)
        self.create_page = CreatePatientPage(self.stacked_widget, self.db_manager)
        self.load_page = LoadPatientPage(self.stacked_widget, self.db_manager)

        # --- Add Pages to Stack ---
        # Index 0: Home
        # Index 1: Create
        # Index 2: Load
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.create_page)
        self.stacked_widget.addWidget(self.load_page)

        # Start at the home page
        self.stacked_widget.setCurrentIndex(0)

    def setup_database(self) -> MongoDBManager | None:
        """Initializes MongoDB connection and returns the manager."""
        print("Initializing Database Connection...")
        #Use MongoDBManager which internally uses MongoDBConnection
        try:
            manager = MongoDBManager() # Assumes default connection params localhost:27017, db: fhir_db
        #     # The manager connects automatically in its __init__ via MongoDBConnection
        #     if manager.db_connection.db: # Check if connection was successful
        #         print("Database connection successful.")
        #         return manager
        #     else:
        #          # Connection failed within MongoDBConnection.connect()
        #          error_message = "Lỗi Kết Nối Database:\n\nKhông thể kết nối tới MongoDB.\nHãy đảm bảo MongoDB đang chạy trên localhost:27017."
        #          QMessageBox.critical(None, "Lỗi Database", error_message) # Use None parent as main window doesn't exist yet
        #          print(error_message)
        #          return None
                    # Check if connection was successful
            # Sửa lỗi: So sánh trực tiếp với None
            if manager.db_connection.db is not None: # <--- ĐÃ SỬA
                print("Database connection successful.")
                return manager
            else:
                 # Connection failed within MongoDBConnection.connect()
                 error_message = "Lỗi Kết Nối Database:\n\nKhông thể kết nối tới MongoDB.\nHãy đảm bảo MongoDB đang chạy trên localhost:27017."
                 QMessageBox.critical(None, "Lỗi Database", error_message) # Use None parent as main window doesn't exist yet
                 print(error_message)
                 return None
        
        except Exception as e:
            error_message = f"Lỗi Khởi Tạo Database:\n\n{e}\n\nKiểm tra cài đặt và dịch vụ MongoDB."
            QMessageBox.critical(None, "Lỗi Database", error_message)
            print(error_message)
            return None

    def closeEvent(self, event):
        """Ensure database connection is closed when the application exits."""
        print("Closing application...")
        if self.db_manager:
            self.db_manager.close_connection()
        # Clean up temporary sensor data directory if it exists
        temp_dir = "temp_sensor_data"
        if os.path.exists(temp_dir):
             try:
                 import shutil
                 shutil.rmtree(temp_dir)
                 print(f"Removed temporary directory: {temp_dir}")
             except Exception as e:
                 print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")

        event.accept() # Accept the close event


# --- Application Entry Point ---
if __name__ == "__main__":
    # Enable high DPI scaling for better visuals on some systems
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Apply a style sheet (optional)
    # app.setStyleSheet("""
    #     QWidget { font-size: 11pt; }
    #     QPushButton { padding: 8px; }
    #     QLineEdit { padding: 5px; }
    #     QTableWidget { gridline-color: #d0d0d0; }
    #     QHeaderView::section { background-color: #f0f0f0; padding: 4px; border: 1px solid #d0d0d0; }
    # """)

    window = MainApp()
    if window.db_manager: # Only show window if DB init was successful
        window.show()
        sys.exit(app.exec_())
    else:
        # If DB failed, setup_database already showed an error, just exit
        sys.exit(1)