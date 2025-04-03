# --- START OF FILE gui/home.py ---

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from PyQt5.QtCore import Qt
# Import the potentially modified/new page classes
# Adjust paths if needed
try:
    from gui.create import CreatePatientPage
    from gui.load import LoadPatientPage
    from database.manager_mongodb_2 import MongoDBManager # Needed for passing to pages
except ImportError as e:
    print(f"Import Error in home.py: {e}. Make sure paths are correct.")
    sys.exit(1)


class HomePage(QWidget):
    # Pass db_manager to potentially use on home page later, although not used now
    def __init__(self, stacked_widget: QStackedWidget, db_manager: MongoDBManager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.db_manager = db_manager # Store if needed later
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50) # Add some margins
        layout.setSpacing(20) # Add spacing between widgets

        self.label = QLabel("👣Ứng dụng Phân Tích Dấu Chân👣")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.label)

        self.label_desc = QLabel("Chọn chức năng:")
        self.label_desc.setAlignment(Qt.AlignCenter)
        self.label_desc.setStyleSheet("font-size: 14px; margin-bottom: 30px;")
        layout.addWidget(self.label_desc)

        # Buttons with better styling potentially
        self.btn_create = QPushButton("📄 Tạo hồ sơ bệnh nhân mới")
        self.btn_load = QPushButton("📂 Load / Tìm kiếm hồ sơ")
        self.btn_exit = QPushButton("❌ Thoát ứng dụng")

        button_style = """
            QPushButton {
                font-size: 14px;
                padding: 15px;
                min-height: 50px;
                border-radius: 5px;
                background-color: #4CAF50; /* Green */
                color: white;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """
        exit_button_style = button_style.replace("#4CAF50", "#f44336").replace("#45a049", "#e53935").replace("#3e8e41", "#d32f2f") # Red for exit

        self.btn_create.setStyleSheet(button_style)
        self.btn_load.setStyleSheet(button_style)
        self.btn_exit.setStyleSheet(exit_button_style)

        layout.addWidget(self.btn_create)
        layout.addWidget(self.btn_load)
        layout.addStretch() # Push exit button towards bottom
        layout.addWidget(self.btn_exit)

        # --- Connect Signals ---
        # Ensure the indices match how you add widgets in main.py/MainApp
        self.btn_create.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Go to Create Page (index 1)
        self.btn_load.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))   # Go to Load Page (index 2)
        self.btn_exit.clicked.connect(QApplication.instance().quit) # Proper way to quit

        # No direct go_to methods needed if lambdas are used directly

# Note: The simple CreatePatientPage and LoadPatientPage classes previously defined
# in home.py are now replaced by the more detailed implementations in
# gui/create.py and gui/load.py respectively.
# MainApp in main.py will instantiate those directly.