# --- START OF FILE gui/load.py ---

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QApplication)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Assuming database and components are accessible
try:
    from database.manager_mongodb_2 import MongoDBManager
    from models.patient import Patient # Import the Patient model
    from components import archindex # Import archindex functions
except ImportError as e:
     print(f"Import Error in load.py: {e}. Make sure paths are correct.")
     sys.exit(1)


# --- Update Patient Dialog ---
class UpdatePatientDialog(QDialog):
    def __init__(self, patient_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cập Nhật Thông Tin Bệnh Nhân")
        self.setMinimumWidth(400)

        self.patient_data = patient_data # Store original data

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit(patient_data.get("name", [{}])[0].get("text", ""))
        self.birthdate_input = QLineEdit(patient_data.get("birthDate", ""))
        self.gender_input = QLineEdit(patient_data.get("gender", ""))
        self.phone_input = QLineEdit(patient_data.get("phone", ""))
        self.address_input = QLineEdit(patient_data.get("address", ""))

        form_layout.addRow("Họ và tên (*):", self.name_input)
        form_layout.addRow("Ngày sinh:", self.birthdate_input)
        form_layout.addRow("Giới tính:", self.gender_input)
        form_layout.addRow("Số điện thoại (*):", self.phone_input)
        form_layout.addRow("Địa chỉ:", self.address_input)

        layout.addLayout(form_layout)

        # Dialog Buttons (OK/Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept) # Connect accept signal
        button_box.rejected.connect(self.reject) # Connect reject signal
        layout.addWidget(button_box)

    def get_updated_data(self) -> dict:
        """Returns a dictionary containing only the fields that have potentially changed."""
        updated_data = {}
        # Compare and add if changed (or always add if simpler)
        new_name = self.name_input.text().strip()
        if new_name != self.patient_data.get("name", [{}])[0].get("text", ""):
             # Update the name structure correctly
            updated_data["name"] = [{"use": "official", "text": new_name}]

        new_phone = self.phone_input.text().strip()
        if new_phone != self.patient_data.get("phone", ""):
            updated_data["phone"] = new_phone

        new_birthdate = self.birthdate_input.text().strip()
        if new_birthdate != self.patient_data.get("birthDate", ""):
             updated_data["birthDate"] = new_birthdate

        new_gender = self.gender_input.text().strip()
        if new_gender != self.patient_data.get("gender", ""):
            updated_data["gender"] = new_gender

        new_address = self.address_input.text().strip()
        if new_address != self.patient_data.get("address", ""):
             updated_data["address"] = new_address

        # Basic validation
        if not new_name:
             QMessageBox.warning(self, "Thiếu thông tin", "Họ và tên không được để trống.")
             return None # Indicate validation failure
        if not new_phone:
             QMessageBox.warning(self, "Thiếu thông tin", "Số điện thoại không được để trống.")
             return None

        return updated_data


# --- Load Patient Page ---
class LoadPatientPage(QWidget):
    def __init__(self, stacked_widget, db_manager: MongoDBManager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.db_manager = db_manager
        self.setWindowTitle("Load Hồ Sơ Bệnh Nhân")
        self.setGeometry(100, 100, 1000, 700) # Adjusted size

        self.selected_patient_id = None
        self.current_patient_data = None # Store full data dict of selected patient
        self.current_foot_data = None # Store numpy array of selected patient's foot data

        main_layout = QHBoxLayout(self)

        # --- Left Panel: Search and List ---
        list_widget_container = QWidget()
        list_layout = QVBoxLayout(list_widget_container)
        list_widget_container.setMaximumWidth(400) # Constrain width

        # Search Area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm theo Tên, SĐT...")
        self.search_button = QPushButton("Tìm")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        list_layout.addLayout(search_layout)

        # Patient List (Using QTableWidget for more columns)
        self.patient_table = QTableWidget()
        self.patient_table.setColumnCount(3) # ID, Name, Phone
        self.patient_table.setHorizontalHeaderLabels(["ID Bệnh Nhân", "Họ Tên", "Số Điện Thoại"])
        self.patient_table.setSelectionBehavior(QAbstractItemView.SelectRows) # Select whole row
        self.patient_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Read-only
        self.patient_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Stretch Name column
        self.patient_table.verticalHeader().setVisible(False) # Hide row numbers
        list_layout.addWidget(self.patient_table)

        # Action Buttons for selected patient
        action_layout = QHBoxLayout()
        self.btn_update = QPushButton("Cập Nhật Thông Tin")
        self.btn_delete = QPushButton("Xóa Bệnh Nhân")
        self.btn_back = QPushButton("⬅ Quay lại Home")
        action_layout.addWidget(self.btn_update)
        action_layout.addWidget(self.btn_delete)
        list_layout.addLayout(action_layout)
        list_layout.addWidget(self.btn_back)


        main_layout.addWidget(list_widget_container)

        # --- Right Panel: Details and Heatmap ---
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        # Patient Details Display
        self.details_label = QLabel("Chi Tiết Bệnh Nhân (Chọn từ danh sách)")
        self.details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(self.details_label)

        self.info_display = QLabel("...") # Will hold formatted patient info
        self.info_display.setWordWrap(True)
        self.info_display.setAlignment(Qt.AlignTop)
        details_layout.addWidget(self.info_display)

        self.ai_result_label = QLabel("Chỉ số Arch Index: Chưa tải dữ liệu")
        self.ai_result_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(self.ai_result_label)

        # Heatmap Display
        details_layout.addWidget(QLabel("Heatmap Bàn Chân:"))
        self.figure, self.ax = plt.subplots(figsize=(5, 5))
        self.canvas = FigureCanvas(self.figure)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.figure.tight_layout()
        self.canvas.draw()
        details_layout.addWidget(self.canvas)
        details_layout.addStretch()

        main_layout.addWidget(details_widget)

        # --- Connect Signals ---
        self.search_button.clicked.connect(self.search_patients)
        self.search_input.returnPressed.connect(self.search_patients) # Search on Enter
        self.patient_table.itemSelectionChanged.connect(self.patient_selected)
        self.btn_update.clicked.connect(self.update_patient)
        self.btn_delete.clicked.connect(self.delete_patient)
        self.btn_back.clicked.connect(self.go_home)

        # Initial Load
        self.search_patients() # Load all patients initially
        self.clear_details() # Ensure details are cleared initially

    def go_home(self):
        self.stacked_widget.setCurrentIndex(0) # Assuming Home is index 0

    def clear_details(self):
        """Clears the patient details, heatmap, and disables action buttons."""
        self.selected_patient_id = None
        self.current_patient_data = None
        self.current_foot_data = None
        self.details_label.setText("Chi Tiết Bệnh Nhân (Chọn từ danh sách)")
        self.info_display.setText("...")
        self.ai_result_label.setText("Chỉ số Arch Index: Chưa tải dữ liệu")

        self.ax.clear()
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("Chưa có dữ liệu")
        self.canvas.draw()

        self.btn_update.setEnabled(False)
        self.btn_delete.setEnabled(False)


    def search_patients(self):
        """Searches patients based on the input field and populates the table."""
        search_term = self.search_input.text().strip()
        self.clear_details() # Clear details before new search
        self.patient_table.setRowCount(0) # Clear table

        try:
            if not search_term:
                # Load all patients if search term is empty
                query = {}
                patients = self.db_manager.find_patients(query)
            else:
                # Simple search: Check name or phone containing the term (case-insensitive)
                # More complex searches might require different query structures
                query = {
                    "$or": [
                        {"name.text": {"$regex": search_term, "$options": "i"}},
                        {"phone": {"$regex": search_term, "$options": "i"}}
                        # Add more fields to search here if needed (e.g., ID, gender)
                        # {"id": {"$regex": search_term, "$options": "i"}},
                        # {"gender": {"$regex": search_term, "$options": "i"}},
                    ]
                }
                patients = self.db_manager.find_patients(query)

            self.populate_patient_table(patients)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Database", f"Không thể tìm kiếm bệnh nhân: {e}")
            print(f"Database search error: {e}")


    def populate_patient_table(self, patients: list[Patient]):
        """Fills the QTableWidget with patient data."""
        self.patient_table.setRowCount(len(patients))
        for row, patient in enumerate(patients):
             # Ensure patient has the expected structure (especially name list)
            patient_id = patient.id
            name = patient.name[0].text if patient.name else "N/A"
            phone = patient.phone if patient.phone else "N/A"

            # Create table items
            id_item = QTableWidgetItem(patient_id)
            id_item.setData(Qt.UserRole, patient_id) # Store ID for later retrieval
            name_item = QTableWidgetItem(name)
            phone_item = QTableWidgetItem(phone)

            # Add items to table
            self.patient_table.setItem(row, 0, id_item)
            self.patient_table.setItem(row, 1, name_item)
            self.patient_table.setItem(row, 2, phone_item)

        # self.patient_table.resizeColumnsToContents() # Adjust columns based on content


    def patient_selected(self):
        """Handles the selection of a patient in the table."""
        selected_items = self.patient_table.selectedItems()
        if not selected_items:
            self.clear_details()
            return

        # Get the patient ID from the first column's UserRole data
        selected_row = self.patient_table.currentRow()
        id_item = self.patient_table.item(selected_row, 0)
        if not id_item:
            self.clear_details()
            return

        self.selected_patient_id = id_item.data(Qt.UserRole)
        print(f"Selected Patient ID: {self.selected_patient_id}")

        # Fetch full patient details
        try:
             # Use get_patient_by_id which returns the Pydantic model
             patient_model = self.db_manager.get_patient_by_id(self.selected_patient_id)
             if patient_model:
                 # Convert model to dict for easier handling and dialog passing
                 self.current_patient_data = patient_model.model_dump(mode='json') # Use model_dump for Pydantic v2+
                 self.display_patient_details()
                 self.load_and_display_foot_data() # Load associated foot data
                 self.btn_update.setEnabled(True)
                 self.btn_delete.setEnabled(True)
             else:
                  QMessageBox.warning(self, "Không Tìm Thấy", f"Không tìm thấy chi tiết cho bệnh nhân ID: {self.selected_patient_id}")
                  self.clear_details()
        except Exception as e:
             QMessageBox.critical(self, "Lỗi Database", f"Lỗi khi lấy chi tiết bệnh nhân: {e}")
             print(f"Error fetching patient details: {e}")
             self.clear_details()


    def display_patient_details(self):
        """Updates the info display labels with the selected patient's data."""
        if not self.current_patient_data:
            self.info_display.setText("...")
            self.details_label.setText("Chi Tiết Bệnh Nhân")
            return

        p = self.current_patient_data
        name = p.get("name", [{}])[0].get("text", "N/A")
        self.details_label.setText(f"Chi Tiết Bệnh Nhân: {name} ({p.get('id', 'N/A')})")

        info_text = f"""
        <b>ID:</b> {p.get('id', 'N/A')}
        <br><b>Họ Tên:</b> {name}
        <br><b>SĐT:</b> {p.get('phone', 'N/A')}
        <br><b>Ngày Sinh:</b> {p.get('birthDate', 'N/A')}
        <br><b>Giới Tính:</b> {p.get('gender', 'N/A')}
        <br><b>Địa Chỉ:</b> {p.get('address', 'N/A')}
        """
        self.info_display.setText(info_text)

    def load_and_display_foot_data(self):
        """Loads foot data for the selected patient, displays heatmap, and calculates Arch Index."""
        if not self.selected_patient_id:
            return

        self.current_foot_data = None # Reset before loading
        self.ai_result_label.setText("Chỉ số Arch Index: Đang tải...")
        self.ax.clear()
        self.ax.set_title("Đang tải dữ liệu...")
        self.canvas.draw()
        QApplication.processEvents() # Update UI

        try:
             data_dict = self.db_manager.get_patient_csv_data(self.selected_patient_id)
             if data_dict:
                 # Convert the dictionary format back to numpy array
                 # Assumes format is {"0": [r0v0, r0v1,...], "1": [r1v0, r1v1,...]}
                 try:
                     # Use pandas to easily convert dict of lists (indexed by string numbers)
                     df = pd.DataFrame.from_dict(data_dict, orient='index')
                     # Ensure numeric type and correct sorting if keys were "0", "1", ...
                     df.index = df.index.astype(int)
                     df = df.sort_index()
                     self.current_foot_data = df.values.astype(float)
                     print(f"Successfully converted loaded data dict to numpy array, shape: {self.current_foot_data.shape}")

                     if self.current_foot_data.shape == (60, 60):
                        self.display_heatmap()
                        self.calculate_and_display_arch_index() # Calculate AI after loading
                     else:
                         raise ValueError(f"Dữ liệu tải về có kích thước không đúng: {self.current_foot_data.shape}")

                 except Exception as convert_e:
                     print(f"Error converting stored data dict to numpy array: {convert_e}")
                     QMessageBox.critical(self, "Lỗi Dữ Liệu", f"Không thể chuyển đổi dữ liệu bàn chân đã lưu: {convert_e}")
                     self.ai_result_label.setText("Chỉ số Arch Index: Lỗi dữ liệu")
                     self.ax.clear()
                     self.ax.set_title("Lỗi định dạng dữ liệu")
                     self.canvas.draw()

             else:
                 print(f"Không tìm thấy dữ liệu bàn chân cho bệnh nhân ID: {self.selected_patient_id}")
                 self.ai_result_label.setText("Chỉ số Arch Index: Không có dữ liệu")
                 self.ax.clear()
                 self.ax.set_title("Không có dữ liệu bàn chân")
                 self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Database", f"Lỗi khi lấy dữ liệu bàn chân: {e}")
            print(f"Error fetching foot data: {e}")
            self.ai_result_label.setText("Chỉ số Arch Index: Lỗi tải dữ liệu")
            self.ax.clear()
            self.ax.set_title("Lỗi tải dữ liệu")
            self.canvas.draw()

    def display_heatmap(self):
        """Updates the matplotlib canvas with the current foot data."""
        if self.current_foot_data is not None:
            self.ax.clear()
            im = self.ax.imshow(self.current_foot_data, cmap='jet', interpolation='nearest')
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.ax.set_title("Dữ liệu Bàn Chân")
            self.figure.tight_layout()
            self.canvas.draw()
        # No else needed, handled by caller

    def calculate_and_display_arch_index(self):
        """Calculates Arch Index from self.current_foot_data."""
        if self.current_foot_data is None:
            # This case should be handled by the caller, but double-check
            self.ai_result_label.setText("Chỉ số Arch Index: Không có dữ liệu để tính")
            return

        try:
            # --- Reuse calculation logic from CreatePatientPage ---
            if not archindex.check_data(self.current_foot_data):
                 self.ai_result_label.setText("Chỉ số Arch Index: Lỗi dữ liệu (NaN/Inf)")
                 return

            processed_matrix = archindex.convert_values(self.current_foot_data, gia_tri=5) # CHECK gia_tri=5
            processed_matrix = archindex.Isolated_point_removal(processed_matrix)
            processed_matrix = archindex.toes_remove(processed_matrix, threshold=30) # Check threshold
            processed_matrix = archindex.toes_remain_removes(processed_matrix)
            AI, foot_type = archindex.compute_arch_index(processed_matrix)

            if AI is not None:
                result_text = f"Chỉ số Arch Index: {AI:.4f} ({foot_type})"
                self.ai_result_label.setText(result_text)
            else:
                 result_text = f"Chỉ số Arch Index: Không thể tính ({foot_type})"
                 self.ai_result_label.setText(result_text)

        except Exception as e:
            self.ai_result_label.setText("Chỉ số Arch Index: Lỗi tính toán")
            print(f"Error during Arch Index calculation on load page: {e}")
            # QMessageBox.warning(self, "Lỗi Tính Toán AI", f"Lỗi khi tính Arch Index: {e}") # Avoid excessive popups


    def update_patient(self):
        """Opens the update dialog and processes the result."""
        if not self.selected_patient_id or not self.current_patient_data:
            QMessageBox.warning(self, "Chưa Chọn Bệnh Nhân", "Vui lòng chọn một bệnh nhân từ danh sách để cập nhật.")
            return

        dialog = UpdatePatientDialog(self.current_patient_data, self)
        if dialog.exec_() == QDialog.Accepted: # Check if user clicked Save
            updated_data = dialog.get_updated_data()

            if updated_data is None: # Validation failed in dialog
                return

            if not updated_data:
                QMessageBox.information(self, "Không Thay Đổi", "Không có thông tin nào được thay đổi.")
                return

            try:
                print(f"Attempting to update patient {self.selected_patient_id} with data: {updated_data}")
                result = self.db_manager.update_patient(self.selected_patient_id, updated_data)
                QMessageBox.information(self, "Kết Quả Cập Nhật", result)

                # Refresh the list and details
                self.search_patients() # Refresh the entire list/search results
                # Re-select the same patient if they still exist after update/refresh
                self.find_and_select_patient(self.selected_patient_id)

            except Exception as e:
                QMessageBox.critical(self, "Lỗi Cập Nhật", f"Đã xảy ra lỗi khi cập nhật bệnh nhân: {e}")
                print(f"Error updating patient in DB: {e}")


    def find_and_select_patient(self, patient_id_to_select):
        """Tries to find and select a patient row by ID after a refresh."""
        for row in range(self.patient_table.rowCount()):
            item = self.patient_table.item(row, 0) # ID is in column 0
            if item and item.data(Qt.UserRole) == patient_id_to_select:
                self.patient_table.selectRow(row)
                # self.patient_selected() # Selection change signal should handle the rest
                return
        # If not found (maybe deleted or ID changed - though ID shouldn't change)
        self.clear_details()


    def delete_patient(self):
        """Deletes the selected patient after confirmation."""
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Chưa Chọn Bệnh Nhân", "Vui lòng chọn một bệnh nhân từ danh sách để xóa.")
            return

        p_name = self.current_patient_data.get("name", [{}])[0].get("text", self.selected_patient_id)
        reply = QMessageBox.question(self, "Xác Nhận Xóa",
                                     f"Bạn có chắc chắn muốn xóa bệnh nhân:\nID: {self.selected_patient_id}\nTên: {p_name}\n\nHành động này sẽ xóa cả thông tin và dữ liệu bàn chân liên quan và không thể hoàn tác.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                print(f"Attempting to delete patient {self.selected_patient_id}")
                result = self.db_manager.delete_patient(self.selected_patient_id)
                QMessageBox.information(self, "Kết Quả Xóa", result)

                # Refresh the list after deletion
                self.search_patients() # This also calls clear_details

            except Exception as e:
                QMessageBox.critical(self, "Lỗi Xóa", f"Đã xảy ra lỗi khi xóa bệnh nhân: {e}")
                print(f"Error deleting patient from DB: {e}")