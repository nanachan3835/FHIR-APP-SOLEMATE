import serial
import numpy as np
import matplotlib.pyplot as plt

ser = serial.Serial("/dev/ttyACM0", 115200, timeout=1)

plt.ion()

while True:
    data = []
    for _ in range(30):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "-----" in line:
            break
        if line == "":
            continue

        parts = line.split(",")
        if len(parts) == 30 and all(part.strip().isdigit() for part in parts):
            values = list(map(int, parts))
            data.append(values)

    if len(data) == 30:
        matrix = np.array(data)

        # Xử lý nhiễu (nếu muốn bật lại)
        # for i in range(matrix.shape[0]):
        #     for j in range(1, matrix.shape[1] - 1):
        #         if matrix[i][j-1] == 0 and matrix[i][j+1] == 0:
        #             matrix[i][j] = 0

        # Vẽ heatmap
        plt.imshow(matrix, cmap="jet", interpolation="gaussian", origin="lower", vmin=0)
        plt.colorbar()
        plt.title("FSR Heatmap (16x16)")
        plt.pause(0.1)
        
        plt.clf()
