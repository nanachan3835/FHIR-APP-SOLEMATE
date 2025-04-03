# Phương pháp đo chỉ số vòm bàn chân tự động mới dựa trên cảm biến áp suất màng mềm

## 1. Giới thiệu
Bài báo đề xuất một phương pháp tự động để đo chỉ số vòm bàn chân nhằm khắc phục những hạn chế của phương pháp đo thủ công.

Phương pháp này sử dụng một cảm biến áp suất màng mềm để thu thập dữ liệu áp suất gan bàn chân. Cảm biến có kích thước 36.5 cm (dài) × 30.5 cm (rộng) và 2288 điểm cảm biến (44 hàng × 52 cột). Dải điện áp đầu ra của cảm biến là 0 V–3.2 V.

Dữ liệu áp suất được chuyển đổi thành hình ảnh kỹ thuật số để xử lý.

---

## 2. Các bước xử lý dữ liệu chính

### 2.1 Loại bỏ nhiễu (Isolated Point Removal)
Sử dụng phương pháp tương quan pixel 8 vùng lân cận. Một pixel được coi là nhiễu nếu tất cả 8 pixel lân cận của nó có giá trị xám là 0. Giá trị của pixel nhiễu sẽ được đặt thành 0. Phương pháp này hiệu quả hơn các bộ lọc truyền thống như bộ lọc trung vị, Gaussian và trung bình.

### 2.2 Loại bỏ dữ liệu ngón chân (Toe Data Removal)
Sử dụng thuật toán liên kết phần tử hàng. Thuật toán này dựa trên sự khác biệt về số lượng điểm ảnh liên tục có giá trị khác 0 giữa ngón chân (tối đa 6 điểm) và lòng bàn chân (thường khoảng 10 điểm) trong mỗi hàng từ hàng 0 đến 15.

### 2.3 Binar hóa dữ liệu hiệu quả của lòng bàn chân (Binarization)
Chuyển đổi hình ảnh thành nhị phân để thuận tiện cho việc tính toán diện tích. Các pixel có giá trị lớn hơn 0 được đặt thành 255, và các pixel có giá trị bằng 0 vẫn là 0, theo công thức:

$\
P(i, j) = \begin{cases}
255, & \text{nếu } P(i, j) > 0 \\
0, & \text{nếu } P(i, j) = 0
\end{cases}
$

Trong đó, \( P(i, j) \) là giá trị pixel tại hàng \( i \) và cột \( j \).

### 2.4 Tự động nhận diện và xác định vị trí các điểm cuối của bàn chân (Endpoint Extraction)
Xác định tọa độ của điểm đầu và điểm cuối của mỗi bàn chân (trái và phải) bằng cách duyệt qua các pixel trong hình ảnh nhị phân.

### 2.5 Tính toán chiều dài bàn chân
- Chiều dài bàn chân trái:
  $
  \alpha_1 = i_B - i_A
  $
- Chiều dài bàn chân phải:
  $
  \alpha_2 = i_D - i_C
  $

---

## 3. Tính toán chỉ số vòm bàn chân (Foot Arch Index Calculation)
Chỉ số vòm bàn chân \( \beta \) được tính bằng tỷ lệ giữa diện tích áp suất của vòm bàn chân (một phần ba giữa của chiều dài bàn chân) và tổng diện tích áp suất của lòng bàn chân (không bao gồm ngón chân).

$
\beta = \frac{s_2}{s_1 + s_2 + s_3}
$

Trong đó:
- s1  là diện tích áp suất hiệu quả của một phần ba trước của bàn chân.
- s2 là diện tích áp suất hiệu quả của một phần ba giữa của bàn chân (vùng vòm).
- s3 là diện tích áp suất hiệu quả của một phần ba sau của bàn chân.

Chỉ số vòm bàn chân trái và phải:
$
\beta_{left} = \frac{s_2}{s_1 + s_2 + s_3}
$
 và 
$
\beta_{right} = \frac{s_5}{s_4 + s_5 + s_6}
$

Trong đó:
- s4,s5,s6 là diện tích áp suất hiệu quả của các phần tương ứng trên bàn chân phải.

---

## 4. Phân loại hình dạng vòm bàn chân
- **Bàn chân vòm cao (High arch foot):** Chỉ số vòm thường \( \leq 0.2 \). Lực dồn chủ yếu ở ngón chân và gót chân.
- **Bàn chân bình thường (Normal foot):** Chỉ số vòm thường từ \( 0.2 \) đến \( 0.26 \). Có tác dụng đệm và bảo vệ toàn bộ cơ thể.
- **Bàn chân bẹt (Flat foot):** Chỉ số vòm thường \( \geq 0.26 \). Toàn bộ lòng bàn chân chịu lực, giảm khả năng đệm.

---

## 5. Kết quả thử nghiệm và đánh giá
- Phương pháp tự động cho kết quả tương đồng với phương pháp thủ công trong việc phân loại các loại vòm bàn chân.
- Phương pháp tự động có độ lặp lại cao hơn so với phương pháp thủ công, thể hiện qua độ lệch chuẩn (STDEV) và hệ số biến thiên (CV) thấp hơn.
- Giá trị AVEDEV, STDEV và CV trung bình của phương pháp tự động lần lượt là **0.0069, 0.0090 và 0.0408**, so với **0.0071, 0.0093 và 0.0440** của phương pháp thủ công.

---

## 6. Lưu ý quan trọng trong quá trình đo
- Người thử nghiệm cần đứng tự nhiên và giữ yên, không nghiêng người sang trái hoặc phải để đảm bảo dữ liệu thu được chính xác và có giá trị tham khảo cho chẩn đoán y tế.

Phương pháp đo chỉ số vòm bàn chân tự động này có tiềm năng ứng dụng trong chẩn đoán y tế thực tế.

