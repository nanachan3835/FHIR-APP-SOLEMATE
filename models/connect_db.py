from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class MongoDBConnection:
    def __init__(self, host="localhost", port=27017, database_name="fhir_db"):
        self.host = host
        self.port = port
        self.database_name = database_name
        self.client = None
        self.db = None

    def connect(self):
        """Kết nối đến MongoDB."""
        try:
            self.client = MongoClient(self.host, self.port)
            self.db = self.client[self.database_name]
            print(f"Đã kết nối đến MongoDB tại {self.host}:{self.port}, Database: {self.database_name}")
        except ConnectionFailure as e:
            print(f"Lỗi kết nối MongoDB: {e}")
            self.client = None

    def check_connection(self):
        """Kiểm tra kết nối đến MongoDB."""
        if self.client is None:
            print("Chưa kết nối đến MongoDB.")
            return False
        try:
            self.client.admin.command('ping')
            print("Kết nối MongoDB hoạt động bình thường.")
            return True
        except ConnectionFailure:
            print("Mất kết nối đến MongoDB.")
            return False

    def close_connection(self):
        """Đóng kết nối MongoDB."""
        if self.client:
            self.client.close()
            print("Đã đóng kết nối MongoDB.")

if __name__ == "__main__":
    mongo_conn = MongoDBConnection()
    mongo_conn.connect()
    mongo_conn.check_connection()
    mongo_conn.close_connection()