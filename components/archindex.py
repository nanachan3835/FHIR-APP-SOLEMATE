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

#load file csv
def load_csv_data(file_path: str)-> np.ndarray:
    """
    Load CSV data from the specified file path.
    """
    try:
        data_matrix = np.loadtxt(file_path, delimiter=',')
        return data_matrix
    except Exception as e:
        print(f"Error loading CSV data: {e}")
        return None

#kiem tra data 
def check_data(data: np.ndarray) -> bool:
    """
    Check if the data is valid.
    """
    if data is None or len(data) == 0:
        print("No data to process.")
        return False
    if np.isnan(data).any():
        print("Data contains NaN values.")
        return False
    if np.isinf(data).any():
        print("Data contains infinite values.")
        return False
    return True

# chuyển đổi giá trị tu 0-5 sang 0-255
def convert_values(matrix: np.ndarray,gia_tri: int) -> np.ndarray:
    """
    Convert values in the matrix from 0-5 to 0-255.
    """
    matrix = (matrix / gia_tri) * 255
    return matrix.astype(np.uint8)


# loai bo diem nhieu don le trong ma tran 60x60 su dung thuan toán 8-neighborhood
def Isolated_point_removal(gray_image: np.ndarray) -> np.ndarray:
    filtered_image = gray_image.copy()
    rows, cols = gray_image.shape

    # Duyệt qua từng điểm ảnh trừ viền ngoài
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            if gray_image[i, j] > 0: 
                neighbors = [
                    gray_image[i-1, j-1], gray_image[i-1, j], gray_image[i-1, j+1],  # Hàng trên
                    gray_image[i, j-1],                     gray_image[i, j+1],    # Hàng giữa
                    gray_image[i+1, j-1], gray_image[i+1, j], gray_image[i+1, j+1]   # Hàng dưới
                ]
                if all(pixel == 0 for pixel in neighbors):
                    filtered_image[i, j] = 0
    
    return filtered_image

def toes_remove(foot_matrix, threshold=30):
    """
    Loại bỏ dữ liệu ngón chân trong ma trận cảm biến 60x60 bằng thuật toán Row Element Association.

    Tham số:
    - foot_matrix: Ma trận NumPy (60x60) chứa ảnh xám (giá trị 0-255).
    - threshold: Ngưỡng số lượng điểm có giá trị > 0 để phân biệt ngón chân (mặc định = 5).

    Trả về:
    - Ma trận đã loại bỏ phần ngón chân.
    """
    # Sao chép ma trận để tránh làm thay đổi dữ liệu gốc
    filtered_matrix = foot_matrix.copy()
    
    # Duyệt từng hàng từ trên xuống
    for row in range(0,10):
        # Đếm số lượng pixel có giá trị > 0 trong hàng
        nonzero_count = np.count_nonzero(filtered_matrix[row, :])
        # Nếu số lượng điểm có giá trị > 0 quá ít, coi như hàng này thuộc ngón chân và xóa nó
        if nonzero_count < threshold:
            filtered_matrix[row, :] = 0  # Đặt tất cả pixel trong hàng đó về 0
        else:
            break  # Khi gặp phần lòng bàn chân, dừng vòng lặp
    
    return filtered_matrix

# loại bỏ phần còn lại của ngón chân khỏi cảm biến
def toes_remain_removes(foot_matrix):
    filtered_matrix = foot_matrix.copy()
    for row in range(10,12):
        count = 0
        for i in range(0,60):
            if filtered_matrix[row][i] != 0:
                count += 1
            if filtered_matrix[row][i] == 0  and count < 7 and count > 0:
                filtered_matrix[row][:i] = 0
                filtered_matrix[row][i:] = 0

    
    return filtered_matrix

#tinh toan chi so arch index

def compute_arch_index(foot_matrix):
    """
    Tính toán chỉ số Arch Index (AI) từ ma trận bàn chân đã xử lý.

    Tham số:
    - foot_matrix: Ma trận NumPy (60x60) chứa ảnh xám (giá trị từ 0-255).

    Trả về:
    - AI (float): Giá trị Arch Index.
    - Foot Type (str): Kiểu bàn chân ('High Arch', 'Normal', 'Flat Foot').
    """
    height, width = foot_matrix.shape

    # Tìm hàng đầu tiên và hàng cuối cùng có pixel bàn chân
    row_indices = np.where(foot_matrix > 0)[0]  # Chỉ lấy hàng có giá trị > 0
    if len(row_indices) == 0:
        return None, "No foot detected"

    top_row = row_indices.min()
    bottom_row = row_indices.max()
    foot_length = bottom_row - top_row + 1  # Chiều dài bàn chân thực tế

    # Xác định khoảng cách chia 3 phần
    third = foot_length // 3

    # Xác định 3 vùng
    heel_region = foot_matrix[top_row : top_row + third, :]
    midfoot_region = foot_matrix[top_row + third : top_row + 2 * third, :]
    forefoot_region = foot_matrix[top_row + 2 * third : bottom_row + 1, :]

    # Tính tổng số pixel có giá trị trong từng vùng
    S_heel = np.count_nonzero(heel_region)
    S_midfoot = np.count_nonzero(midfoot_region)
    S_forefoot = np.count_nonzero(forefoot_region)

    # Tính AI
    total_area = S_heel + S_midfoot + S_forefoot
    if total_area == 0:
        return None, "No foot detected"

    AI = S_midfoot / total_area

    # Phân loại bàn chân
    if AI < 0.21:
        foot_type = "High Arch Foot"
    elif 0.21 <= AI <= 0.26:
        foot_type = "Normal Foot"
    else:
        foot_type = "Flat Foot"

    return AI, foot_type

# tính chiều cao bàn chân
def compute_foot_height(archindex:float )-> float:
    return 0.67/archindex

def compute_height_need(archindex:float)-> str:
    return f"Chiều cao của đế điều chỉnh trong khoảng từ {0.67/archindex - 0.67/0.26} cm"
