import serial
import time
import numpy as np
import io # Us

def read_sensor_data(port: str, baudrate: int = 115200):
    ser = serial.Serial(port, baudrate, timeout=1)
    while True:
        data = []
        for _ in range(30):
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if "-----" in line:
                break
            if line == "":
                continue
            values = list(map(int, line.split(",")))
            if len(values) == 16:
                data.append(values)
        if len(data) == 30:
            matrix = np.array(data)
            return matrix

    return None, "Not enough data received."
#
if __name__ == '__main__':
    port_to_test = '/dev/ttyUSB0'  # <-- CHANGE THIS
    data = read_sensor_data(port_to_test)
    print(data)