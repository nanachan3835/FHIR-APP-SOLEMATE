# --- START OF FILE archindex.py ---

# khai báo thư viện
import serial
import csv
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

# load file csv
def load_csv_data(file_path: str) -> np.ndarray | None: # Thêm | None vào type hint
    """
    Load CSV data from the specified file path.
    """
    try:
        # Sử dụng pandas để đọc, linh hoạt hơn với header/index
        # Nếu file không có header, header=None
        # Nếu file có header, bỏ header=None hoặc header=0
        df = pd.read_csv(file_path, header=None, delimiter=',')
        # Kiểm tra nếu đọc được dataframe rỗng
        if df.empty:
             print(f"Warning: CSV file '{file_path}' is empty or could not be parsed correctly.")
             return None
        return df.values.astype(float) # Trả về numpy array
    except FileNotFoundError:
        print(f"Error: CSV file not found at {file_path}")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: CSV file '{file_path}' is empty.")
        return None
    except Exception as e:
        print(f"Error loading CSV data from {file_path}: {e}")
        return None

# kiem tra data
def check_data(data: np.ndarray | None) -> bool: # Cho phép input là None
    """
    Check if the data is valid (not None, not empty, no NaN, no Inf).
    """
    if data is None or data.size == 0: # Kiểm tra size thay vì len cho numpy array
        print("No data to process.")
        return False
    if np.isnan(data).any():
        print("Data contains NaN values.")
        # Optionally handle NaN: data = np.nan_to_num(data, nan=0.0)
        return False
    if np.isinf(data).any():
        print("Data contains infinite values.")
        # Optionally handle Inf: data = np.nan_to_num(data, posinf=HIGH_VALUE, neginf=LOW_VALUE)
        return False
    return True

# chuyển đổi giá trị tu 0-5 sang 0-255
def convert_values(matrix: np.ndarray, input_max: float = 5.0) -> np.ndarray: # Sửa tên gia_tri thành input_max
    """
    Convert values in the matrix from 0-input_max to 0-255.
    Handles potential division by zero if input_max is 0.
    """
    if input_max == 0:
        print("Warning: input_max is 0 in convert_values. Returning zeros.")
        return np.zeros_like(matrix, dtype=np.uint8)
    # Đảm bảo không vượt quá 255 và xử lý giá trị âm (nếu có)
    scaled_matrix = (matrix / input_max) * 255.0
    scaled_matrix = np.clip(scaled_matrix, 0, 255) # Giới hạn giá trị trong khoảng 0-255
    return scaled_matrix.astype(np.uint8)


# loai bo diem nhieu don le trong ma tran 60x60 su dung thuan toán 8-neighborhood
def Isolated_point_removal(gray_image: np.ndarray) -> np.ndarray:
    """Removes isolated noise points using 8-neighborhood algorithm."""
    filtered_image = gray_image.copy()
    rows, cols = gray_image.shape

    # Thêm kiểm tra kích thước để tránh lỗi index nếu ảnh quá nhỏ
    if rows < 3 or cols < 3:
        print("Warning: Image too small for isolated point removal.")
        return filtered_image

    # Duyệt qua từng điểm ảnh trừ viền ngoài
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            # Chỉ xét điểm ảnh có giá trị (không phải nền)
            if gray_image[i, j] > 0:
                # Lấy 8 điểm lân cận
                neighbors = gray_image[i-1:i+2, j-1:j+2].flatten()
                # Kiểm tra xem tất cả lân cận (trừ điểm trung tâm) có bằng 0 không
                # Tạo một mask để loại trừ điểm trung tâm khi kiểm tra
                center_index = 4 # Index của điểm [i,j] trong mảng 3x3 phẳng
                neighbor_sum_excluding_center = np.sum(neighbors) - gray_image[i,j]

                # Nếu tổng các lân cận (không tính điểm đang xét) là 0 -> điểm nhiễu
                if neighbor_sum_excluding_center == 0:
                    filtered_image[i, j] = 0 # Loại bỏ điểm nhiễu

    return filtered_image

def toes_remove(foot_matrix, threshold=0, rows_to_check=5):
    """
    Loại bỏ dữ liệu ngón chân trong ma trận cảm biến bằng thuật toán Row Element Association.
    Args:
        foot_matrix: Ma trận NumPy chứa ảnh xám (0-255).
        threshold: Ngưỡng số lượng điểm có giá trị > 0 để phân biệt ngón chân.
        rows_to_check: Số hàng từ trên xuống để kiểm tra ngón chân.
    Returns:
        Ma trận đã loại bỏ phần ngón chân.
    """
     # Tìm hàng đầu tiên và hàng cuối cùng có pixel bàn chân
    row_indices = np.where(foot_matrix > 0)[0]
    if len(row_indices) == 0:
        return None, "No foot detected in this half"

    top_row = row_indices.min()
    bottom_row = row_indices.max()
    #foot_length = bottom_row - top_row + 1

    foot_matrix_height = foot_matrix[top_row:bottom_row + 1, :] 
    filtered_matrix = foot_matrix.copy()
    rows, cols = foot_matrix_height.shape
    actual_rows_to_check = min(rows_to_check, rows) # Đảm bảo không vượt quá số hàng

    # Duyệt từng hàng từ trên xuống
    for row in range(actual_rows_to_check):
        nonzero_count = np.count_nonzero(filtered_matrix[row, :])
        if nonzero_count < threshold and nonzero_count > 0: # Thêm đk > 0 để tránh xóa hàng trống hoàn toàn
            filtered_matrix[row, :] = 0
        elif nonzero_count >= threshold:
             # Khi gặp hàng đầu tiên có đủ pixel (không phải ngón chân), dừng lại
             break

    return filtered_matrix

# loại bỏ phần còn lại của ngón chân khỏi cảm biến
def toes_remain_removes(foot_matrix, start_row=5, end_row=12, connectivity_threshold=20):
    """Loại bỏ các cụm pixel nhỏ còn sót lại ở vùng ngón chân."""
    filtered_matrix = foot_matrix.copy()
    rows, cols = foot_matrix.shape
    actual_start_row = min(start_row, rows)
    actual_end_row = min(end_row, rows)

    for row in range(actual_start_row, actual_end_row):
        in_cluster = False
        cluster_start_col = -1
        current_cluster_count = 0
        for col in range(cols):
            if filtered_matrix[row, col] > 0:
                if not in_cluster: # Bắt đầu một cụm mới
                    in_cluster = True
                    cluster_start_col = col
                    current_cluster_count = 1
                else: # Đang trong một cụm
                    current_cluster_count += 1
            else: # Gặp pixel 0
                if in_cluster: # Kết thúc một cụm
                    # Nếu cụm vừa kết thúc quá nhỏ, xóa nó
                    if current_cluster_count < connectivity_threshold:
                        filtered_matrix[row, cluster_start_col:col] = 0
                    # Reset lại trạng thái
                    in_cluster = False
                    cluster_start_col = -1
                    current_cluster_count = 0
        # Xử lý trường hợp cụm kéo dài đến hết hàng
        if in_cluster and current_cluster_count < connectivity_threshold:
             filtered_matrix[row, cluster_start_col:cols] = 0

    return filtered_matrix

# --- HÀM PHỤ TRỢ TÍNH AI CHO MỘT NỬA BÀN CHÂN ---
def _calculate_single_foot_ai(single_foot_matrix: np.ndarray):
    """
    Tính toán chỉ số Arch Index (AI) cho một ma trận bàn chân đơn lẻ (trái hoặc phải).
    Args:
        single_foot_matrix: Ma trận NumPy chứa ảnh xám (0-255) của một nửa bàn chân.
    Returns:
        tuple: (AI_value, foot_type) hoặc (None, error_message)
    """
    if not check_data(single_foot_matrix):
        return None, "Invalid data for single foot"
    
    single = single_foot_matrix[::-1, ::-1] # Đảo ngược thứ tự cột
    height, width = single_foot_matrix.shape

    # Tìm hàng đầu tiên và hàng cuối cùng có pixel bàn chân
    row_indices = np.where(single_foot_matrix > 0)[0]
    if len(row_indices) == 0:
        return None, "No foot detected in this half"

    top_row = row_indices.min()
    bottom_row = row_indices.max()
    foot_length = bottom_row - top_row + 1

    # Xử lý trường hợp foot_length quá nhỏ (ví dụ: < 3 hàng)
    if foot_length < 3:
        return None, "Detected foot area is too small"

    # Xác định khoảng cách chia 3 phần
    third = foot_length // 3
    # Đảm bảo các vùng không bị chồng chéo hoặc bỏ sót pixel do làm tròn
    row_div1 = top_row + third
    row_div2 = top_row + 2 * third

    # Xác định 3 vùng (đảm bảo index hợp lệ)
    heel_region = single_foot_matrix[top_row : row_div1, :]
    midfoot_region = single_foot_matrix[row_div1 : row_div2, :]
    forefoot_region = single_foot_matrix[row_div2 : bottom_row + 1, :]

    # Tính tổng số pixel có giá trị trong từng vùng
    S_heel = np.count_nonzero(heel_region)
    S_midfoot = np.count_nonzero(midfoot_region) - 60
    S_forefoot = np.count_nonzero(forefoot_region)

    # Tính AI
    total_area = S_heel + S_midfoot + S_forefoot
    if total_area == 0:
        # Trường hợp này không nên xảy ra nếu row_indices không rỗng, nhưng kiểm tra lại
        return None, "No valid pixels found after region splitting"

    AI = S_midfoot / total_area

    # Phân loại bàn chân
    if AI < 0.21:
        foot_type = "High Arch Foot"
    elif 0.21 <= AI <= 0.26:
        foot_type = "Normal Foot"
    else: # AI > 0.26
        foot_type = "Flat Foot"

    return AI, foot_type

# --- HÀM CHÍNH ĐÃ SỬA ĐỔI ---
def compute_arch_index(foot_matrix_processed: np.ndarray):
    """
    Tính toán chỉ số Arch Index (AI) riêng biệt cho chân trái và chân phải
    từ ma trận bàn chân 60x60 đã được xử lý.

    Args:
        foot_matrix_processed: Ma trận NumPy (60x60) đã qua các bước xử lý
                               (convert_values, noise removal, toes removal).
    Returns:
        dict: Dictionary chứa kết quả AI và loại bàn chân cho 'left' và 'right'.
              Ví dụ: {'left': {'AI': 0.25, 'type': 'Normal Foot'},
                      'right': {'AI': 0.28, 'type': 'Flat Foot'}}
              Hoặc giá trị AI/type có thể là None nếu không tính được.
    """
    if not check_data(foot_matrix_processed):
        return {"left": {"AI": None, "type": "Invalid input data"},
                "right": {"AI": None, "type": "Invalid input data"}}
    foot_matrix_processed = np.flip(foot_matrix_processed,axis = 0)
    foot_matrix_processed = foot_matrix_processed[::-1, ::-1] # Đảo ngược thứ tự cột
    rows, cols = foot_matrix_processed.shape

    # Chia đôi ma trận theo cột
    mid_col = cols // 2 # = 30
    left_foot_matrix = foot_matrix_processed[:, :mid_col] # Cột 0 đến 29
    right_foot_matrix = foot_matrix_processed[:, mid_col:] # Cột 30 đến 59

    # Tính toán AI cho từng nửa
    left_ai, left_type = _calculate_single_foot_ai(left_foot_matrix)
    right_ai, right_type = _calculate_single_foot_ai(right_foot_matrix)
    if left_ai == 0 or right_ai == 0:
        # foot_matrix_processed_spin=spin_matrix(foot_matrix_processed)
        # left_foot_matrix = foot_matrix_processed_spin[:, :mid_col] # Cột 0 đến 29
        # right_foot_matrix = foot_matrix_processed_spin[:, mid_col:]
        # left_ai, left_type = _calculate_single_foot_ai(left_foot_matrix)
        # right_ai, right_type = _calculate_single_foot_ai(right_foot_matrix) 
        return compute_arch_index(spin_matrix(foot_matrix_processed)) # Gọi lại hàm để tính toán lại
    # Trả về kết quả dưới dạng dictionary
   

    results = {
        "right": {"AI": left_ai, "type": left_type},
        "left": {"AI": right_ai, "type": right_type}
         }
        
    return results

# --- Các hàm tính chiều cao có thể cần điều chỉnh ---
# Bây giờ bạn có thể muốn tính chiều cao riêng cho mỗi chân nếu AI khác nhau

def compute_foot_height(archindex: float | None) -> float | None:
    """Tính chiều cao vòm dựa trên Arch Index."""
    if archindex is None or archindex <= 0: # Thêm kiểm tra archindex > 0
        return None
    # Công thức này có thể cần xem xét lại nguồn gốc và đơn vị
    return 0.67 / archindex

def compute_height_need(archindex: float | None) -> str:
    """Đề xuất chiều cao đế điều chỉnh."""
    foot_height = compute_foot_height(archindex)
    normal_foot_max_ai = 0.26 # AI tối đa cho bàn chân thường
    min_normal_height = compute_foot_height(normal_foot_max_ai)

    if foot_height is None or min_normal_height is None:
        return "Không thể tính toán chiều cao cần thiết."

    # Chiều cao cần bù = chiều cao tối thiểu của chân thường - chiều cao hiện tại
    height_diff = min_normal_height - foot_height

    if height_diff <= 0: # Chân thường hoặc vòm cao, không cần bù nhiều hoặc không cần
        return "Chiều cao vòm bình thường hoặc cao, không cần điều chỉnh nhiều."
        # Hoặc trả về khoảng nhỏ: return f"Chiều cao đế điều chỉnh khoảng 0 - {abs(height_diff):.2f} cm"
    else:
        # Chỉ đề xuất bù phần thiếu so với chân thường
        return f"Chiều cao đế điều chỉnh khoảng {height_diff:.2f} cm"
        # Hoặc giữ lại cách tính cũ nếu đó là yêu cầu:
        # return f"Chiều cao của đế điều chỉnh trong khoảng từ {height_diff:.2f} cm"
#spin csv
# === HÀM MỚI ĐỂ XOAY MA TRẬN ===
def spin_matrix(matrix: np.ndarray) -> np.ndarray:
    """
    Swaps rows and columns of the input matrix (transposes the matrix).

    Args:
        matrix: The input NumPy array (matrix).

    Returns:
        The transposed NumPy array (rows become columns and columns become rows).

    Raises:
        TypeError: If the input is not a NumPy array.
    """
    if not isinstance(matrix, np.ndarray):
        raise TypeError(f"Input must be a NumPy array, but got {type(matrix)}")

    # Sử dụng thuộc tính .T của NumPy array để chuyển vị
    transposed_matrix = matrix.T
    return transposed_matrix


def reverse_matrix(matrix: np.ndarray) -> np.ndarray:
    """
    Đảo ngược thứ tự của cả hàng và cột trong ma trận NumPy (xoay 180 độ).

    Args:
        matrix: Ma trận NumPy đầu vào.

    Returns:
        Ma trận NumPy mới với cả hàng và cột đã được đảo ngược.

    Raises:
        TypeError: Nếu đầu vào không phải là NumPy array.
    """
    if not isinstance(matrix, np.ndarray):
        raise TypeError(f"Input must be a NumPy array, but got {type(matrix)}")

    # np.flip() với tuple axis=(0, 1) sẽ đảo ngược cả trục 0 (hàng) và trục 1 (cột)
    reversed_matrix = np.flip(matrix)
    return reversed_matrix

# ===============================

if __name__ == '__main__':
    # Tạo dữ liệu giả 60x60
    # Dữ liệu này cần thực tế hơn để kiểm tra đúng
    dummy_data = np.zeros((60, 60))
    # Thêm một ít 'dấu chân' giả định
    dummy_data[15:55, 5:25] = np.random.rand(40, 20) * 3 # Chân trái giả
    dummy_data[15:55, 35:55] = np.random.rand(40, 20) * 4 # Chân phải giả (AI khác)
    dummy_data[5:15, 10:20] = np.random.rand(10,10) * 1 # Ít 'ngón chân' trái
    dummy_data[5:15, 40:50] = np.random.rand(10,10) * 1 # Ít 'ngón chân' phải

    print("Dữ liệu gốc (shape):", dummy_data.shape)

    # 1. Xử lý dữ liệu
    processed_data = convert_values(dummy_data, input_max=5.0)
    processed_data = Isolated_point_removal(processed_data)
    processed_data = toes_remove(processed_data, threshold=15) # Giảm ngưỡng cho data giả
    processed_data = toes_remain_removes(processed_data, connectivity_threshold=5) # Giảm ngưỡng

    print("Dữ liệu sau xử lý (shape):", processed_data.shape)

    # 2. Tính toán Arch Index cho cả hai chân
    ai_results = compute_arch_index(processed_data)

    print("\n--- Arch Index Results ---")
    print(f"Left Foot - AI: {ai_results['left']['AI']}, Type: {ai_results['left']['type']}")
    print(f"Right Foot - AI: {ai_results['right']['AI']}, Type: {ai_results['right']['type']}")

    # 3. Tính toán chiều cao (ví dụ cho chân trái)
    left_ai = ai_results['left']['AI']
    if left_ai is not None:
        height_left = compute_foot_height(left_ai)
        need_left = compute_height_need(left_ai)
        print(f"\n--- Left Foot Height Calculations ---")
        print(f"Estimated Height: {height_left}")
        print(f"Suggested Adjustment: {need_left}")
    else:
        print("\nCannot calculate height for left foot.")

    # (Tương tự cho chân phải nếu cần)
    right_ai = ai_results['right']['AI']
    # ... tính toán cho chân phải ...

