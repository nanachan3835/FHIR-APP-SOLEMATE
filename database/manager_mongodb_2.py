# --- START OF FILE manager_mongodb.py ---

import pandas as pd
from pymongo.errors import DuplicateKeyError # Import necessary for handling potential duplicate key errors if needed, though current logic prevents it before insertion.
from bson import ObjectId # Useful if directly manipulating MongoDB's default _id

# Assuming connect.py defines MongoDBConnection correctly
import models 
from models.connect_db import MongoDBConnection 
# Assuming models define Patient and FHIRResource correctly
from models.patient import Patient
from models.fhir import FHIR as FHIRResource 

# This script quản lý kết nối và thao tác với MongoDB cho ứng dụng FHIR

class MongoDBManager:
    def __init__(self, patient_collection="patients", data_collection="patient_sensor_data"):
        """
        Initializes the MongoDBManager.
        Args:
            patient_collection (str): Name of the collection to store patient demographic data.
            data_collection (str): Name of the collection to store patient-associated data (like CSV).
        """
        self.db_connection = MongoDBConnection()
        self.db_connection.connect()
        self.db = self.db_connection.db
        self.patient_collection = self.db[patient_collection]
        self.data_collection = self.db[data_collection]
        # Ensure unique index on patient_id for faster lookups and data integrity
        # Optional: Add index on name/phone for faster duplicate checks if collection is large
        self.patient_collection.create_index([("name.text", 1), ("phone", 1)], unique=False) # Index for duplicate check/lookup
        self.patient_collection.create_index("id") # Ensure patient FHIR ID is unique
        self.data_collection.create_index("patient_id",unique=True) # Ensure one data entry per patient_id

    # --- Patient Management ---

    def save_patient(self, patient_data: dict) -> str:
        """
        Lưu hồ sơ bệnh nhân vào MongoDB nếu chưa tồn tại.
        Args:
            patient_data (dict): Dữ liệu bệnh nhân dưới dạng dictionary (tuân theo cấu trúc Patient model).
        Returns:
            str: Thông báo kết quả ("Lưu thành công", "Đã có data của bệnh nhân trong cơ sở dữ liệu", "Lỗi: ...").
        Raises:
            ValueError: Nếu patient_data không phải là dictionary hoặc thiếu các trường cần thiết.
        """
        if not isinstance(patient_data, dict):
            raise ValueError("Dữ liệu bệnh nhân phải là dictionary")
        if "name" not in patient_data or not patient_data["name"] or "text" not in patient_data["name"][0]:
             raise ValueError("Dữ liệu bệnh nhân thiếu trường 'name' hoặc 'name[0].text'.")
        if "phone" not in patient_data:
             raise ValueError("Dữ liệu bệnh nhân thiếu trường 'phone'.")
        if "id" not in patient_data:
             raise ValueError("Dữ liệu bệnh nhân thiếu trường 'id'.")

        patient_name = patient_data["name"][0]["text"]
        patient_phone = patient_data["phone"]
        patient_id = patient_data["id"]

        # --- Checked: check duplicate_patient ---
        # Use the harmonized check function
        if self.is_duplicate_patient(patient_name, patient_phone):
            # Check if the duplicate has the same ID. If so, maybe it's an update attempt?
            # For now, strictly prevent saving if name+phone exists.
            existing = self.patient_collection.find_one({"name.text": patient_name, "phone": patient_phone})
            return f"Đã có data của bệnh nhân '{patient_name}' với SĐT '{patient_phone}' trong cơ sở dữ liệu (ID: {existing.get('id', 'N/A')})."

        # Check if patient ID already exists (should be unique)
        if self.patient_collection.find_one({"id": patient_id}):
             return f"Đã tồn tại bệnh nhân khác với ID '{patient_id}'."

        try:
            # Validate data with Pydantic model before insertion (optional but recommended)
            # Patient(**patient_data) # This will raise ValidationError if data is invalid

            result = self.patient_collection.insert_one(patient_data)
            print(f"Đã lưu bệnh nhân '{patient_name}' với MongoDB _id: {result.inserted_id} và FHIR ID: {patient_id}")
            return "Lưu thành công"
        except DuplicateKeyError:
             # This might happen if the unique index on 'id' catches a duplicate race condition
             return f"Lỗi: Đã tồn tại bệnh nhân khác với ID '{patient_id}' (DuplicateKeyError)."
        except Exception as e:
            print(f"Lỗi khi lưu bệnh nhân: {e}")
            return f"Lỗi khi lưu bệnh nhân: {e}"

    def get_patient_by_id(self, patient_id: str):
        """Lấy hồ sơ bệnh nhân từ MongoDB theo ID FHIR."""
        patient_doc = self.patient_collection.find_one({"id": patient_id})
        if patient_doc:
            # Convert MongoDB doc (potentially with _id) to Patient object
            patient_doc.pop('_id', None) # Remove MongoDB _id before creating Patient model
            return Patient(**patient_doc)
        return None

    def get_patient_by_name(self, name: str):
        """Lấy hồ sơ bệnh nhân từ MongoDB theo tên (first match)."""
         # Uses the harmonized query style
        patient_doc = self.patient_collection.find_one({"name.text": name})
        if patient_doc:
            patient_doc.pop('_id', None)
            return Patient(**patient_doc)
        return None

    def get_patient_by_phone(self, phone: str):
        """Lấy hồ sơ bệnh nhân từ MongoDB theo số điện thoại."""
        patient_doc = self.patient_collection.find_one({"phone": phone})
        if patient_doc:
            patient_doc.pop('_id', None)
            return Patient(**patient_doc)
        return None

    def find_patients(self, query: dict):
        """
        Tìm kiếm bệnh nhân dựa trên một query dictionary tùy chỉnh.
        Args:
            query (dict): Bộ lọc MongoDB (ví dụ: {"gender": "female"}).
        Returns:
            List[Patient]: Danh sách các bệnh nhân khớp với query.
        """
        results = list(self.patient_collection.find(query))
        patients = []
        for doc in results:
            doc.pop('_id', None)
            try:
                patients.append(Patient(**doc))
            except Exception as e: # Handle potential data inconsistency
                 print(f"Warning: Could not parse patient document {doc.get('id', 'N/A')} into Patient model: {e}")
        return patients

    def load_data(self, query_type: str, query_value: str):
        """
        Truy vấn bệnh nhân theo ID, tên hoặc số điện thoại. (Simplified wrapper around find_patients)
        Args:
            query_type (str): Loại truy vấn ('id', 'name', 'phone').
            query_value (str): Giá trị cần tìm.
        Returns:
            List[Patient]: Danh sách bệnh nhân tìm được.
        Raises:
            ValueError: Nếu query_type không hợp lệ.
        """
        if query_type not in ["id", "name", "phone"]:
            raise ValueError("Loại truy vấn không hợp lệ. Chỉ hỗ trợ 'id', 'name', hoặc 'phone'")

        # Harmonized query construction
        if query_type == "id":
            query = {"id": query_value}
        elif query_type == "name":
            query = {"name.text": query_value}
        else: # phone
            query = {"phone": query_value}

        return self.find_patients(query)

    # --- Checked: check duplicate_patient ---
    def is_duplicate_patient(self, name: str, phone: str) -> bool:
        """Kiểm tra xem bệnh nhân đã tồn tại trong MongoDB chưa dựa trên tên và SĐT."""
        # Harmonized query
        existing_patient = self.patient_collection.find_one({"name.text": name, "phone": phone})
        return existing_patient is not None

    # --- Checked: thêm yếu tố xóa bệnh nhân ---
    def delete_patient(self, patient_id: str) -> str:
        """
        Xóa bệnh nhân dựa trên ID FHIR. Đồng thời xóa dữ liệu liên quan (CSV).
        Args:
            patient_id (str): ID FHIR của bệnh nhân cần xóa.
        Returns:
            str: Thông báo kết quả.
        """
        # First, delete associated data
        data_deletion_result = self.data_collection.delete_one({"patient_id": patient_id})
        if data_deletion_result.deleted_count > 0:
            print(f"Đã xóa dữ liệu liên quan của bệnh nhân ID: {patient_id}")
        else:
            print(f"Không tìm thấy dữ liệu liên quan để xóa cho bệnh nhân ID: {patient_id}")

        # Then, delete patient record
        result = self.patient_collection.delete_one({"id": patient_id})
        if result.deleted_count > 0:
            return f"Đã xóa bệnh nhân với ID FHIR '{patient_id}' và dữ liệu liên quan khỏi database."
        else:
            return f"Không tìm thấy bệnh nhân với ID FHIR '{patient_id}' để xóa."

    def remove_duplicate_patients(self):
        """
        Xóa các bệnh nhân trùng lặp dựa trên name.text và phone,
        chỉ giữ lại hồ sơ bệnh nhân được tạo gần nhất (theo MongoDB _id).
        """
        pipeline = [
            {"$sort": {"_id": -1}},  # Sắp xếp theo _id (mới nhất trước)
            {"$group": {
                "_id": {"name": "$name.text", "phone": "$phone"}, # Group by name and phone
                "latest_doc_id": {"$first": "$_id"},             # Get the _id of the newest document in the group
                "all_doc_ids": {"$push": "$_id"},                 # Get all _ids in the group
                "count": {"$sum": 1}                             # Count documents per group
            }},
            {"$match": {"count": {"$gt": 1}}} # Filter for groups with more than one document (duplicates)
        ]
        duplicate_groups = list(self.patient_collection.aggregate(pipeline))

        deleted_count_total = 0
        for group in duplicate_groups:
            ids_to_remove = group["all_doc_ids"]
            ids_to_remove.remove(group["latest_doc_id"])  # Keep the latest _id

            if ids_to_remove:
                # Find associated patient FHIR IDs for the documents to be removed
                # to also clean up related data
                docs_to_remove = self.patient_collection.find({"_id": {"$in": ids_to_remove}}, {"id": 1})
                patient_ids_to_remove_data = [doc.get('id') for doc in docs_to_remove if doc.get('id')]

                # Delete duplicate patient documents
                result = self.patient_collection.delete_many({"_id": {"$in": ids_to_remove}})
                deleted_count_total += result.deleted_count
                print(f"Đã xóa {result.deleted_count} hồ sơ trùng lặp của bệnh nhân {group['_id']['name']} / {group['_id']['phone']}")

                # Delete associated data for the removed duplicates
                if patient_ids_to_remove_data:
                    data_delete_result = self.data_collection.delete_many({"patient_id": {"$in": patient_ids_to_remove_data}})
                    if data_delete_result.deleted_count > 0:
                         print(f"  -> Đã xóa {data_delete_result.deleted_count} bản ghi dữ liệu liên quan.")

        if deleted_count_total == 0:
             print("Không tìm thấy hồ sơ bệnh nhân trùng lặp để xóa.")
        else:
             print(f"Tổng cộng đã xóa {deleted_count_total} hồ sơ bệnh nhân trùng lặp.")


    # --- NEW: Thêm yếu tố cập nhật thông tin patient ---
    def update_patient(self, patient_id: str, update_data: dict) -> str:
        """
        Cập nhật thông tin cho bệnh nhân dựa trên ID FHIR.
        Chỉ cập nhật các trường được cung cấp trong update_data.
        Lưu ý: Để cập nhật tên (name), hãy cung cấp toàn bộ danh sách tên mới.
              Không cập nhật trường 'id'.
        Args:
            patient_id (str): ID FHIR của bệnh nhân cần cập nhật.
            update_data (dict): Dictionary chứa các trường và giá trị mới.
                                Ví dụ: {"phone": "1122334455", "address": "Địa chỉ mới"}
                                Ví dụ cập nhật tên: {"name": [{"use": "official", "text": "Tên Mới"}]}
        Returns:
            str: Thông báo kết quả.
        """
        if "id" in update_data:
            return "Lỗi: Không thể cập nhật trường 'id' của bệnh nhân."
        if not update_data:
             return "Lỗi: Không có dữ liệu cập nhật được cung cấp."

        # Optional: Validate update_data structure if needed, especially for complex fields like 'name'

        result = self.patient_collection.update_one(
            {"id": patient_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return f"Không tìm thấy bệnh nhân với ID FHIR '{patient_id}' để cập nhật."
        elif result.modified_count == 0:
            return f"Thông tin bệnh nhân ID FHIR '{patient_id}' không thay đổi (dữ liệu mới giống dữ liệu cũ)."
        else:
            # If name or phone was updated, update the redundant copies in the data collection
            updated_fields = update_data.keys()
            if "name" in updated_fields or "phone" in updated_fields:
                # Fetch the updated patient to get current name/phone
                updated_patient_doc = self.patient_collection.find_one({"id": patient_id})
                if updated_patient_doc:
                    update_payload_data = {}
                    if "name" in updated_fields:
                         update_payload_data["patient_name"] = updated_patient_doc["name"][0]["text"]
                    if "phone" in updated_fields:
                         update_payload_data["patient_phone"] = updated_patient_doc["phone"]

                    if update_payload_data:
                        data_update_res = self.data_collection.update_one(
                            {"patient_id": patient_id},
                            {"$set": update_payload_data}
                        )
                        if data_update_res.modified_count > 0:
                            print(f"  -> Đã cập nhật thông tin tham chiếu (tên/SĐT) trong bản ghi dữ liệu liên quan.")

            return f"Đã cập nhật thành công thông tin cho bệnh nhân ID FHIR '{patient_id}'."

    # --- Patient Data (CSV) Management ---

    # --- NEW: Thêm truy vấn data của patient ---
    # Renamed save_csv_to_mongodb to be specific to patient data
    def save_patient_csv_data(self, patient_id: str, csv_file_path: str) -> str:
        """
        Lưu dữ liệu ma trận (ví dụ 60x60) từ file CSV vào MongoDB, liên kết với patient_id.
        Ghi đè nếu dữ liệu cho patient_id này đã tồn tại.
        Args:
            patient_id (str): ID FHIR của bệnh nhân liên quan.
            csv_file_path (str): Đường dẫn đến file CSV.
        Returns:
            str: Thông báo kết quả.
        """
        # First, check if the patient exists
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return f"Lỗi: Không tìm thấy bệnh nhân với ID FHIR '{patient_id}'. Không thể lưu dữ liệu CSV."

        try:
            df = pd.read_csv(csv_file_path, header=None)
            # Convert DataFrame to a dictionary format suitable for MongoDB
            # Example: { "0": [val, val, ...], "1": [val, val,...], ... }
            # Or store as list of lists: [[row1], [row2], ...]
            # Using dict of lists here as in the original example
            matrix_dict = {str(i): df.iloc[i].tolist() for i in range(df.shape[0])}

            data_document = {
                "patient_id": patient.id,
                "patient_name": patient.name[0].text, # Store for potential simpler lookups
                "patient_phone": patient.phone,     # Store for potential simpler lookups
                "data": matrix_dict,
                # Add timestamp? metadata?
                # "last_updated": datetime.utcnow()
            }

            # Use update_one with upsert=True to insert if not exist, or replace if exist
            result = self.data_collection.update_one(
                {"patient_id": patient.id}, # Filter by patient_id
                {"$set": data_document},     # Data to insert/update
                upsert=True                  # Create if doesn't exist
            )

            if result.upserted_id:
                print(f"Đã lưu dữ liệu CSV mới cho bệnh nhân ID {patient.id} vào collection '{self.data_collection.name}' với _id: {result.upserted_id}.")
                return "Lưu dữ liệu CSV thành công."
            elif result.modified_count > 0:
                 print(f"Đã cập nhật (ghi đè) dữ liệu CSV cho bệnh nhân ID {patient.id} trong collection '{self.data_collection.name}'.")
                 return "Cập nhật (ghi đè) dữ liệu CSV thành công."
            else:
                 # This case (matched but not modified) might happen if the exact same data is saved again
                 print(f"Dữ liệu CSV cho bệnh nhân ID {patient.id} không thay đổi.")
                 return "Dữ liệu CSV không thay đổi."

        except FileNotFoundError:
            print(f"Lỗi: Không tìm thấy file CSV tại đường dẫn: {csv_file_path}")
            return f"Lỗi: Không tìm thấy file CSV tại đường dẫn: {csv_file_path}"
        except pd.errors.EmptyDataError:
             print(f"Lỗi: File CSV '{csv_file_path}' rỗng.")
             return f"Lỗi: File CSV '{csv_file_path}' rỗng."
        except Exception as e:
            print(f"Lỗi khi đọc hoặc lưu CSV vào MongoDB: {e}")
            return f"Lỗi khi đọc hoặc lưu CSV vào MongoDB: {e}"

    def get_patient_csv_data(self, patient_id: str):
        """
        Lấy dữ liệu ma trận (đã lưu từ CSV) của bệnh nhân theo ID FHIR.
        Args:
            patient_id (str): ID FHIR của bệnh nhân.
        Returns:
            Optional[dict]: Dictionary chứa dữ liệu ma trận (ví dụ: {"0": [...], "1": [...]})
                           hoặc None nếu không tìm thấy.
        """
        data_doc = self.data_collection.find_one({"patient_id": patient_id})
        if data_doc and "data" in data_doc:
            return data_doc["data"]
        else:
            print(f"Không tìm thấy dữ liệu CSV cho bệnh nhân ID: {patient_id}")
            return None

    # --- NEW: Thêm yếu tố cập nhật dữ liệu csv của patient ---
    # This is effectively handled by save_patient_csv_data now, as it overwrites.
    # We can keep update_patient_csv_data as an alias for clarity if desired.
    def update_patient_csv_data(self, patient_id: str, new_csv_file_path: str) -> str:
        """
        Cập nhật (ghi đè) dữ liệu CSV cho bệnh nhân. Alias for save_patient_csv_data.
        Args:
            patient_id (str): ID FHIR của bệnh nhân.
            new_csv_file_path (str): Đường dẫn đến file CSV mới.
        Returns:
            str: Thông báo kết quả từ save_patient_csv_data.
        """
        print(f"Thực hiện cập nhật/ghi đè dữ liệu CSV cho bệnh nhân ID {patient_id} từ file {new_csv_file_path}...")
        return self.save_patient_csv_data(patient_id, new_csv_file_path)


    # --- Other Methods ---

    def save_fhir_resource(self, resource: FHIRResource):
        """Lưu tài nguyên FHIR chung (không phải Patient) vào MongoDB."""
        # This seems less used based on other functions, but keeping it.
        # Consider a separate collection or adding type discrimination if mixing resources.
        if not isinstance(resource, FHIRResource):
            raise ValueError("Dữ liệu phải là một FHIRResource")
        resource_dict = resource.dict()
        # Decide on a collection for generic resources, e.g., 'fhir_resources'
        fhir_collection = self.db.get_collection("fhir_resources") # Use get_collection
        result = fhir_collection.insert_one(resource_dict)
        print(f"Đã lưu tài nguyên FHIR loại '{resource.resourceType}' với ID: {result.inserted_id}")


    def close_connection(self):
        """Đóng kết nối MongoDB."""
        self.db_connection.close_connection()

#--- Example Usage (Illustrative) ---
if __name__ == "__main__":
    manager = MongoDBManager()

    # --- Test Patient Operations ---
    print("\n--- Testing Patient Operations ---")
    patient_info_1 = {
        "resourceType": "Patient",
        "id": "P001",
        "name": [{"use": "official", "text": "Trần Văn B"}],
        "gender": "male",
        "birthDate": "1985-10-15",
        "phone": "0912345678",
        "address": "Hồ Chí Minh, Việt Nam"
    }
    patient_info_2 = {
        "resourceType": "Patient",
        "id": "P002",
        "name": [{"use": "official", "text": "Lê Thị C"}],
        "gender": "female",
        "birthDate": "1992-03-22",
        "phone": "0988776655",
        "address": "Đà Nẵng, Việt Nam"
    }
    patient_info_duplicate = { # Same name/phone as P001 but different ID initially
        "resourceType": "Patient",
        "id": "P003_dup",
        "name": [{"use": "official", "text": "Trần Văn B"}],
        "gender": "male",
        "birthDate": "1985-10-15",
        "phone": "0912345678",
        "address": "Hồ Chí Minh, Việt Nam - Cập nhật" # Different address
    }

    print(manager.save_patient(patient_info_1))
    print(manager.save_patient(patient_info_2))
    print(manager.save_patient(patient_info_duplicate)) # Should report duplicate name/phone

    # Retrieve
    retrieved = manager.get_patient_by_id("P001")
    print(f"Retrieved P001 by ID: {retrieved.model_dump_json(indent=2) if retrieved else 'Not Found'}")
    retrieved_list = manager.load_data("name", "Lê Thị C")
    print(f"Found by Name 'Lê Thị C': {[p.id for p in retrieved_list] if retrieved_list else 'Not Found'}")

    # Update
    update_result = manager.update_patient("P002", {"address": "Đà Nẵng - Quận Hải Châu", "phone": "0988111222"})
    print(f"Update P002 result: {update_result}")
    retrieved_updated = manager.get_patient_by_id("P002")
    print(f"P002 after update: {retrieved_updated.model_dump_json(indent=2) if retrieved_updated else 'Not Found'}")


    # --- Test CSV Data Operations ---
    print("\n--- Testing CSV Data Operations ---")
    # Create dummy CSV files
    try:
        dummy_data_1 = [[i+j for j in range(60)] for i in range(60)]
        df1 = pd.DataFrame(dummy_data_1)
        df1.to_csv("dummy_p001_data.csv", index=False, header=False)

        dummy_data_2 = [[(i*j)%100 for j in range(60)] for i in range(60)]
        df2 = pd.DataFrame(dummy_data_2)
        df2.to_csv("dummy_p002_data.csv", index=False, header=False)

        dummy_data_2_updated = [[100 + (i*j)%100 for j in range(60)] for i in range(60)]
        df2_upd = pd.DataFrame(dummy_data_2_updated)
        df2_upd.to_csv("dummy_p002_data_updated.csv", index=False, header=False)

        # Save CSV data
        print(manager.save_patient_csv_data("P001", "dummy_p001_data.csv"))
        print(manager.save_patient_csv_data("P002", "dummy_p002_data.csv"))
        print(manager.save_patient_csv_data("P999", "dummy_p001_data.csv")) # Test non-existent patient

        # Retrieve CSV data
        csv_data = manager.get_patient_csv_data("P001")
        print(f"Retrieved CSV data for P001: {'Data received (keys: ' + ', '.join(csv_data.keys()) + '...)' if csv_data else 'Not Found'}")
        # print(csv_data['0'][:10]) # Print first 10 elements of the first row

        # Update CSV data
        print(manager.update_patient_csv_data("P002", "dummy_p002_data_updated.csv"))
        csv_data_updated = manager.get_patient_csv_data("P002")
        print(f"Retrieved updated CSV data for P002: {'Data received' if csv_data_updated else 'Not Found'}")
        # print(csv_data_updated['0'][:10]) # Check if data changed


    except Exception as e:
        print(f"Error during CSV file creation/testing: {e}")
    finally:
        # Clean up dummy files
        import os
        for fname in ["dummy_p001_data.csv", "dummy_p002_data.csv", "dummy_p002_data_updated.csv"]:
            if os.path.exists(fname):
                os.remove(fname)

     # --- Test Deletion and Duplicates ---
    print("\n--- Testing Deletion and Duplicates ---")
    # Save the duplicate again for removal test
    # We need a unique ID to save it first, even if name/phone are duplicates for the *logic*
    patient_info_duplicate_for_removal = {
        "resourceType": "Patient",
        "id": "P001_OlderDuplicate", # Different ID
        "name": [{"use": "official", "text": "Trần Văn B"}], # Same name/phone as P001
        "gender": "male",
        "birthDate": "1985-10-15",
        "phone": "0912345678",
        "address": "Hồ Chí Minh, Việt Nam - Old Record"
    }
    # Temporarily bypass duplicate check by inserting directly (for testing remove_duplicates)
    # In real usage, save_patient prevents this kind of duplicate based on name/phone
    try:
         manager.patient_collection.insert_one(patient_info_duplicate_for_removal)
         print("Manually inserted a duplicate record for testing remove_duplicate_patients.")
         # Optionally save some dummy data for this duplicate
         manager.save_patient_csv_data("P001_OlderDuplicate", "dummy_p001_data.csv")

    except Exception as e:
        print(f"Could not insert manual duplicate for testing: {e}")


    # Remove duplicates (should keep P001, remove P001_OlderDuplicate)
    manager.remove_duplicate_patients()
    print(f"Checking if P001 still exists: {manager.get_patient_by_id('P001') is not None}")
    print(f"Checking if P001_OlderDuplicate was removed: {manager.get_patient_by_id('P001_OlderDuplicate') is None}")
    print(f"Checking if P001_OlderDuplicate data was removed: {manager.get_patient_csv_data('P001_OlderDuplicate') is None}")


    # Delete a patient
    print(manager.delete_patient("P002"))
    print(f"Checking if P002 was deleted: {manager.get_patient_by_id('P002') is None}")
    print(f"Checking if P002's data was deleted: {manager.get_patient_csv_data('P002') is None}")


    # --- Close Connection ---
    manager.close_connection()