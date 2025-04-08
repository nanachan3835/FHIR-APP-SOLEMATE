import serial
import numpy as np
import matplotlib.pyplot as plt

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)

plt.ion()

while True:
    data = []
    for _ in range(60):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "-----" in line:
            break
        if line == "":
            continue

        values = list(map(int, line.split(",")))
        if len(values) == 60:
            data.append(values)

    if len(data) == 60:
        matrix = np.array(data)

        # Xử lý nhiễu
        #for i in range(matrix.shape[0]):
            #matrix[i][0] = 0
            #matrix[i][-1] = 0
            # for j in range(1, matrix.shape[1] - 2):
            #     if matrix[i][j-1] == 0 and matrix[i][j+1] == 0:
            #         matrix[i][j] = 0
        
        # Vẽ heatmap với màu mặc định là xanh nước biển cho giá trị thấp
        plt.imshow(matrix, cmap="jet", interpolation="gaussian", origin="lower", vmin=0)
        plt.colorbar()
        plt.title("FSR Heatmap (30x16)")
        plt.pause(0.1)
        plt.clf()
