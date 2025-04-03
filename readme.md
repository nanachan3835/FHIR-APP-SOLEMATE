# FHIR - Ứng Dụng Quản Lý Bệnh Nhân & Phân Tích Dấu Chân 🎉

Ứng dụng desktop được xây dựng bằng Python và PyQt5 để quản lý thông tin bệnh nhân, thu thập dữ liệu từ cảm biến áp lực bàn chân (ma trận 60x60), lưu trữ vào MongoDB, và tính toán chỉ số Arch Index.

## Mục lục🔥 🔥 🔥 

-   [Yêu cầu hệ thống (Prerequisites)](#yêu-cầu-hệ-thống-prerequisites)
-   [Cài đặt](#cài-đặt)
    -   [Bước 1: Lấy mã nguồn](#bước-1-lấy-mã-nguồn)
    -   [Bước 2: Thiết lập môi trường ảo](#bước-2-thiết-lập-môi-trường-ảo)
    -   [Bước 3: Cài đặt thư viện Python](#bước-3-cài-đặt-thư-viện-python)
-   [Chạy ứng dụng (Trực tiếp)](#chạy-ứng-dụng-trực-tiếp)
-   [Chạy ứng dụng (Sử dụng Docker)](#chạy-ứng-dụng-sử-dụng-docker)
-   [Cấu hình](#cấu-hình)
    -   [Cổng Serial](#cổng-serial)
    -   [Kết nối MongoDB](#kết-nối-mongodb)
    -   [Tham số Arch Index](#tham-số-arch-index)
-   [Xử lý sự cố (Troubleshooting)](#xử-lý-sự-cố-troubleshooting)

## Yêu cầu hệ thống (Prerequisites)🌟

Trước khi bắt đầu, hãy đảm bảo bạn đã cài đặt các phần mềm sau trên hệ thống của mình:

1.  **Python:** Phiên bản 3.9 trở lên được khuyến nghị.
    *   **Ubuntu:** Thường đã cài sẵn. Kiểm tra với `python3 --version`. Nếu chưa có, cài đặt bằng `sudo apt update && sudo apt install python3`.
    *   **Windows:** Tải về từ [python.org](https://www.python.org/downloads/). **Quan trọng:** Trong quá trình cài đặt, hãy nhớ **chọn ô "Add Python X.X to PATH"**.
2.  **Pip:** Trình quản lý gói Python (thường đi kèm với Python).
    *   **Ubuntu:** Nếu thiếu, cài đặt bằng `sudo apt install python3-pip`.
    *   **Windows:** Đi kèm với trình cài đặt Python.
3.  **Git:** Hệ thống quản lý phiên bản mã nguồn.
    *   **Ubuntu:** `sudo apt install git`.
    *   **Windows:** Tải về từ [git-scm.com](https://git-scm.com/download/win).
4.  **MongoDB:** Cơ sở dữ liệu NoSQL. Ứng dụng mặc định kết nối tới `mongodb://localhost:27017`.
    *   **Ubuntu/Windows:** Tải về và cài đặt từ [mongodb.com](https://www.mongodb.com/try/download/community). Đảm bảo dịch vụ MongoDB đang chạy trước khi khởi động ứng dụng.
5.  **(Ubuntu) `python3-venv`:** Cần thiết để tạo môi trường ảo. Cài đặt bằng `sudo apt install python3-venv`.
6.  **(Tùy chọn - Nếu dùng Docker) Docker Engine & Docker Desktop:**
    *   **Ubuntu:** Làm theo hướng dẫn cài đặt Docker Engine tại [docs.docker.com](https://docs.docker.com/engine/install/ubuntu/).
    *   **Windows:** Tải về Docker Desktop từ [docker.com](https://www.docker.com/products/docker-desktop/).

## Cài đặt🌟

Thực hiện các bước sau để cài đặt ứng dụng trên máy của bạn.

### Bước 1: Lấy mã nguồn 💡

Mở Terminal (Ubuntu) hoặc Command Prompt/PowerShell (Windows) và clone repository:

```bash
git clone <URL_CỦA_REPOSITORY_CỦA_BẠN>
cd <TÊN_THƯ_MỤC_REPOSITORY>
#Thay thế <URL_CỦA_REPOSITORY_CỦA_BẠN> và <TÊN_THƯ_MỤC_REPOSITORY> bằng thông tin thực tế.
```
### Bước 2: Thiết lập môi trường ảo 💡
Sử dụng môi trường ảo là cách tốt nhất để quản lý các thư viện Python cho từng dự án riêng biệt.
+ Trên Ubuntu:
```
python3 -m venv venv
source venv/bin/activate
#Bash
```
+ - Bạn sẽ thấy (venv) xuất hiện ở đầu dòng lệnh, cho biết môi trường ảo đã được kích hoạt.

+ Trên Windows (Command Prompt):
```
python -m venv venv
.\venv\Scripts\activate
```
+ Trên Windows (PowerShell):
```
python -m venv venv
.\venv\Scripts\Activate.ps1
```
+ - (Nếu gặp lỗi về Execution Policy trong PowerShell, bạn có thể cần chạy Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser và xác nhận, sau đó thử lại lệnh activate).

+ - Bạn sẽ thấy (venv) xuất hiện ở đầu dòng lệnh.

+ Lưu ý: Mỗi khi bạn mở một cửa sổ terminal/cmd mới để làm việc với dự án, bạn cần kích hoạt lại môi trường ảo bằng lệnh 
```source venv/bin/activate (Ubuntu) ``` hoặc ```.\venv\Scripts\activate (Windows).```


### Bước 3: Cài đặt thư viện Python 💡
+ Khi môi trường ảo đã được kích hoạt (có (venv) ở đầu dòng lệnh), cài đặt các thư viện cần thiết từ file requirements.txt:
```
pip install -r requirements.txt
```
Quá trình này có thể mất vài phút tùy thuộc vào tốc độ mạng của bạn.

Sau khi hoàn tất cài đặt:
+ - Đảm bảo MongoDB đang chạy trên localhost:27017.
+ - Kích hoạt môi trường ảo (nếu chưa làm):

Ubuntu: ```source venv/bin/activate```

Windows: ```.\venv\Scripts\activate```
### Chạy ứng dụng (Trực tiếp) 💡
Chạy file main.py:

Ubuntu: ```python3 main.py```

Windows: ```python main.py```

Ứng dụng sẽ khởi động.

### Chạy ứng dụng (Sử dụng Docker) 💡

Đây là phương pháp thay thế, đóng gói ứng dụng và các phụ thuộc vào một container.
Yêu cầu: Đã cài đặt Docker, MongoDB đang chạy và có thể truy cập từ host (localhost:27017).

+ Build Docker Image: 

Mở terminal trong thư mục gốc của dự án và chạy:
```
docker build -t fhir-qt-app .
```
+ Run Docker Container:
Trên Ubuntu (Linux):
Cho phép container kết nối tới X server của host (chạy trên terminal của host):
```
xhost +local:docker
```
+ -(Để thu hồi quyền sau khi dùng xong: xhost -local:docker)
+ Chạy container:
```
docker run -it --rm \
    --network host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --device=/dev/ttyACM0:/dev/ttyACM0 `# THAY ĐỔI CỔNG SERIAL Ở ĐÂY NẾU CẦN` \
    --name my-fhir-app \
    fhir-qt-app
```
+ Quan trọng: 

+ - Thay đổi --device=/dev/ttyACM0:/dev/ttyACM0 thành cổng serial thực tế của bạn (ví dụ: /dev/ttyUSB0, /dev/ttyS0). 

+ - Bạn có thể cần thêm user vào group dialout (sudo usermod -aG dialout $USER và đăng xuất/đăng nhập lại) hoặc thêm --group-add dialout vào lệnh docker run nếu gặp lỗi quyền truy cập serial.

Trên Windows (với Docker Desktop):

Thử lệnh sau:
```
docker run -it --rm \
    --network host \
    -e DISPLAY=host.docker.internal:0 \
    --device=COM3:COM3  `# THAY ĐỔI CỔNG SERIAL CỦA BẠN VÀ CÚ PHÁP CÓ THỂ KHÁC` \
    --name my-fhir-app \
    fhir-qt-app
```
+ - Lưu ý: Việc map cổng serial (--device) trên Windows vào Docker có thể phức tạp hơn và phụ thuộc vào cấu hình Docker Desktop/WSL2. Bạn có thể cần tìm hiểu thêm tài liệu của Docker Desktop. --network host có thể không hoạt động như mong đợi trên Windows; bạn có thể cần chỉ định địa chỉ IP của host thay vì localhost trong mã nguồn nếu MongoDB chạy trên host. ( lên trang chủ của docker nhé 😊 : https://www.docker.com/ )


## Cấu hình:🌟

Một số cài đặt có thể cần được điều chỉnh:📝

### Cổng Serial 🎯

Ứng dụng cần biết cổng serial nào được kết nối với cảm biến.

Khi chạy trực tiếp: Chỉnh sửa giá trị mặc định (COM3) trong file gui/create.py ở dòng self.serial_port_input = QLineEdit("COM3") hoặc nhập trực tiếp vào ô "Cổng Serial" trên giao diện. 

File components/serial.py cũng có thể chứa cổng mặc định trong phần if __name__ == '__main__':.


+ Khi chạy bằng Docker: 

Phải chỉnh sửa tham số --device trong lệnh docker run (xem phần Chạy bằng Docker).

### Kết nối MongoDB:🎯

Mặc định, ứng dụng kết nối tới mongodb://localhost:27017, database fhir_db.
Nếu MongoDB của bạn chạy ở địa chỉ/cổng khác, hãy chỉnh sửa file database/connect.py.

### Tham số Arch Index🎯
Các giá trị như gia_tri (dùng để chuyển đổi giá trị cảm biến) và threshold (ngưỡng loại bỏ ngón chân) trong file components/archindex.py có thể cần được tinh chỉnh dựa trên đặc tính của cảm biến bạn đang sử dụng.

## Xử lý sự cố (Troubleshooting)🌟
### qt.qpa.plugin: Could not find the Qt platform plugin "wayland" in "" (Chỉ trên Linux): ☑️

Đây thường là cảnh báo và ứng dụng vẫn chạy được bằng X11 (XCB).

+ Để khắc phục (tùy chọn): ```sudo apt install qtwayland5.```
### Lỗi quyền truy cập cổng Serial (Permission Denied - Chỉ trên Linux): ☑️
Đảm bảo user của bạn thuộc group dialout: ```sudo usermod -aG dialout $USER```. Cần đăng xuất và đăng nhập lại hoặc chạy lệnh newgrp dialout trong terminal hiện tại để áp dụng thay đổi group.

Khi dùng Docker, đảm bảo cờ ```--device``` đúng và cân nhắc thêm ```--group-add dialout``` vào lệnh ```docker run```
### Lỗi kết nối Database:☑️
+ Kiểm tra xem dịch vụ MongoDB đã được khởi động và đang chạy chưa.
+ Đảm bảo không có tường lửa nào chặn kết nối tới cổng 27017.
+ Kiểm tra lại cấu hình kết nối trong database/connect.py nếu MongoDB không chạy ở địa chỉ mặc định.
### Lỗi ModuleNotFoundError:☑️
+ Đảm bảo bạn đã kích hoạt môi trường ảo (source venv/bin/activate hoặc .\venv\Scripts\activate).
+ Chạy lại ```pip install -r requirements.txt``` để chắc chắn tất cả thư viện đã được cài đặt trong môi trường ảo đó.

