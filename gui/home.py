# --- START OF FILE gui/home.py ---

import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
                             QStackedWidget, QSpacerItem, QSizePolicy, QFrame)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QSize

# Import các page khác (giữ nguyên)
try:
    # ... (các import khác giữ nguyên) ...
    from database.manager_mongodb_2 import MongoDBManager # Đảm bảo import này có
except ImportError as e:
    print(f"Import Error in home.py: {e}. Make sure paths are correct.")
    sys.exit(1)


class HomePage(QWidget):
    def __init__(self, stacked_widget: QStackedWidget, db_manager: MongoDBManager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.db_manager = db_manager

        # --- BỎ Đặt ID Object Name ở đây (không cần thiết nếu không style trực tiếp) ---
        # self.setObjectName("HomePage")

        # --- Áp dụng StyleSheet CHỈ cho các thành phần bên trong HomePage ---
        # BỎ phần #HomePage { background-color: ... }
        self.setStyleSheet("""
            QLabel#TitleLabel { /* Style cho tiêu đề */
                font-size: 22px;
                font-weight: bold;
                color: white; /* Chữ trắng */
                margin-bottom: 10px;
            }
            QLabel#DescLabel { /* Style cho mô tả */
                font-size: 14px;
                color: #dddddd; /* Chữ xám nhạt */
                margin-bottom: 25px;
            }
            QPushButton#NormalButton { /* Style cho nút thường */
                font-size: 14pt;
                font-weight: bold;
                color: black; /* Chữ đen */
                background-color: white; /* Nền trắng */
                border: none;
                padding: 12px 20px;
                min-height: 50px;
                border-radius: 25px; /* Bo tròn nhiều hơn */
                margin-left: 50px; /* Căn lề nút */
                margin-right: 50px;
            }
            QPushButton#NormalButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton#NormalButton:pressed {
                background-color: #e0e0e0;
            }
            QPushButton#ExitButton { /* Style cho nút thoát */
                font-size: 14pt;
                font-weight: bold;
                color: white; /* Chữ trắng */
                background-color: #dc3545; /* Nền đỏ */
                border: none;
                padding: 12px 20px;
                min-height: 50px;
                border-radius: 25px; /* Bo tròn nhiều hơn */
                margin-left: 50px; /* Căn lề nút */
                margin-right: 50px;
            }
            QPushButton#ExitButton:hover {
                background-color: #c82333;
            }
            QPushButton#ExitButton:pressed {
                background-color: #a0202b;
            }
        """)

        # --- Layout chính ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(15)

        # --- Thêm Logo/Icon ---
        # ... (Phần logo giữ nguyên như trước) ...
        self.logo_label = QLabel()
        icon_path = "assets/SoleMate_icon.png" # Đảm bảo đường dẫn đúng

        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaledToWidth(350, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            print(f"Warning: Icon file not found at {icon_path}")
            self.logo_label.setText("SoleMate Logo (Not Found)")
            self.logo_label.setStyleSheet("color: white;") # Chữ trắng nếu không có icon

        self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)


        # --- Thêm khoảng trống lớn hơn ---
        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Tiêu đề và Mô tả ---
        self.label = QLabel("Chào mừng đến với SoleMate")
        self.label.setObjectName("TitleLabel")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.label_desc = QLabel("Chọn chức năng:")
        self.label_desc.setObjectName("DescLabel")
        self.label_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_desc)

        # --- Tạo các nút và đặt ID ---
        self.btn_create = QPushButton("Tạo hồ sơ mới")
        self.btn_create.setObjectName("NormalButton")

        self.btn_load = QPushButton("Load / Tìm kiếm")
        self.btn_load.setObjectName("NormalButton")

        self.btn_exit = QPushButton("Thoát")
        self.btn_exit.setObjectName("ExitButton")

        # --- Thêm nút vào layout ---
        layout.addWidget(self.btn_create)
        layout.addWidget(self.btn_load)
        layout.addStretch()
        layout.addWidget(self.btn_exit)

        # --- Connect Signals ---
        self.btn_create.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_load.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.btn_exit.clicked.connect(QApplication.instance().quit)

        self.setLayout(layout)

# --- END OF FILE gui/home.py ---