# --- START OF FILE components/serial.py ---

import serial
import time
import numpy as np
import io # Use io.TextIOWrapper for cleaner text reading

def read_sensor_data(port: str, baudrate: int = 115200, timeout: int = 5, expected_rows: int = 60, expected_cols: int = 60) -> (np.ndarray | None, str):
    """
    Đọc dữ liệu ma trận 60x60 từ cổng serial.

    Giả định:
    - Cảm biến gửi dữ liệu dưới dạng 60 dòng text.
    - Mỗi dòng chứa 60 giá trị số, phân tách bằng dấu phẩy (,).
    - Kết thúc mỗi chu kỳ gửi dữ liệu có thể có một dấu hiệu (hoặc dựa vào timeout).

    Args:
        port (str): Tên cổng serial (e.g., 'COM3' or '/dev/ttyACM0').
        baudrate (int): Tốc độ baud.
        timeout (int): Thời gian chờ tối đa (giây) cho mỗi lần đọc dòng.
        expected_rows (int): Số hàng mong đợi.
        expected_cols (int): Số cột mong đợi.

    Returns:
        tuple: (numpy.ndarray | None, str)
            - Ma trận numpy 60x60 nếu đọc thành công.
            - None nếu có lỗi.
            - Thông báo trạng thái (str).
    """
    matrix_data = []
    print(f"Attempting to connect to serial port {port} at {baudrate} baud...")

    try:
        # Use a context manager for the serial connection
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            # Wrap the binary serial stream in a text wrapper for easier line reading
            # Adjust encoding if your sensor uses something different
            sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser), encoding='ascii', errors='ignore', newline='\r\n')

            print(f"Connected to {port}. Waiting for data...")
            ser.reset_input_buffer() # Clear any old data

            start_time = time.time()
            rows_read = 0

            while rows_read < expected_rows and (time.time() - start_time) < (timeout * expected_rows + 5): # Generous overall timeout
                try:
                    line = sio.readline().strip() # Read one line
                    # print(f"Read line: {line}") # Debugging

                    if line:
                        # Split line by comma and convert to numbers (float or int)
                        row_values = [float(val) for val in line.split(',') if val] # Handle potential empty strings

                        if len(row_values) == expected_cols:
                            matrix_data.append(row_values)
                            rows_read += 1
                            print(f"Read row {rows_read}/{expected_rows}") # Progress
                        else:
                            print(f"Warning: Received row with {len(row_values)} columns, expected {expected_cols}. Skipping. Line: '{line}'")
                            # Optionally break or implement more robust sync logic here
                    else:
                        # Timeout occurred for this line read or empty line received
                        print("Warning: Empty line or read timeout for a single line.")
                        pass # Continue trying

                except serial.SerialTimeoutException:
                    print(f"Timeout waiting for line {rows_read + 1}. Read {rows_read} rows so far.")
                    break # Exit loop if timeout occurs
                except ValueError as ve:
                    print(f"Error converting value in line to number: {ve}. Line: '{line}'. Skipping row.")
                    continue # Skip this corrupted row
                except Exception as line_e:
                     print(f"Error reading/processing line {rows_read + 1}: {line_e}")
                     continue # Try next line

            # End of reading loop

            if rows_read == expected_rows:
                print("Successfully read all expected rows.")
                numpy_matrix = np.array(matrix_data)
                if numpy_matrix.shape == (expected_rows, expected_cols):
                     return numpy_matrix, f"Đọc thành công dữ liệu {expected_rows}x{expected_cols} từ {port}."
                else:
                     # This shouldn't happen if row check passed, but defensive check
                     return None, f"Lỗi: Dữ liệu đọc được có kích thước không đúng ({numpy_matrix.shape})."
            else:
                 return None, f"Lỗi: Chỉ đọc được {rows_read}/{expected_rows} hàng trước khi hết giờ hoặc gặp lỗi."

    except serial.SerialException as se:
        return None, f"Lỗi Serial: Không thể mở hoặc đọc từ cổng {port}. Chi tiết: {se}"
    except Exception as e:
        return None, f"Lỗi không xác định khi đọc serial: {e}"

# Example Usage (for testing)
if __name__ == '__main__':
    # Replace 'COM_PORT_HERE' with your actual serial port
    # You might need a simulator or a real device sending data in the expected format
    port_to_test = 'COM3' # <-- CHANGE THIS
    print(f"Testing serial read on {port_to_test}...")
    data, message = read_sensor_data(port_to_test, timeout=2) # Short timeout for testing

    print("\n--- Result ---")
    print(message)
    if data is not None:
        print(f"Received data shape: {data.shape}")
        print("First 5x5 elements:")
        print(data[:5, :5])
    else:
        print("No data received.")