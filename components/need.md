tôi cần bạn sửa lại đoan code python trong file create.py với yêu cầu như sau.
khi tôi bấm vào nút load cảm biến, tôi sẽ được đưa đến 1 cửa sổ khác được vẽ bằng matplotlib, khi đó sẽ có 1 box lựa chọn để tôi có thể lựa chọn được cổng serial trên máy tính của tôi, sau khi đã chọn được cổng serial thì sẽ hiển thị heatmap từ cảm biến bằng đoạn code sau:

import serial
import numpy as np
import matplotlib.pyplot as plt

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)

plt.ion()

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
và sẽ có 1 nút bấm chụp heatmap, khi tôi bấm vào nút chụp heatmap thì sẽ lưu lại phần dữ liệu đang hiển thị trên heatmap và đưa về cửa sổ create.py ban đầu, heatmap sẽ được hiển thị giống như là khi bấm nút chọn hiển thị file csv thành heatmap vậy.