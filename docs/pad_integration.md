# Tài Liệu Tích Hợp Mô Hình Passive PAD (Silent-Face-Anti-Spoofing ONNX)

Tài liệu này giải thích lý do lựa chọn sử dụng mô hình MiniFASNet đã được huấn luyện sẵn (Pretrained Model) từ dự án **Silent-Face-Anti-Spoofing** của Minivision thay vì tự thiết kế và huấn luyện mô hình từ đầu.

---

## 1. Lý Do Lựa Chọn Pretrained Model thay vì Tự Huấn Luyện (Training from Scratch)

Việc phát triển một mô hình phát hiện giả mạo khuôn mặt (Presentation Attack Detection - PAD) đòi hỏi nhiều nguồn lực và kỹ thuật chuyên sâu. Dưới đây là các lý do thực tiễn và kỹ thuật giải thích việc tích hợp mô hình pretrained MiniFASNet ONNX là phương án tối ưu cho dự án `Face_attendance`:

### A. Yêu Cầu Cực Kỳ Cao Về Tập Dữ Liệu Huấn Luyện
- **Sự đa dạng của cuộc tấn công**: Một mô hình PAD hiệu quả cần nhận biết nhiều phương thức giả mạo (print attack trên giấy thường/giấy ảnh bóng, replay attack trên nhiều loại màn hình LCD/OLED, cutout attack khoét mắt). Việc tự thu thập hàng chục nghìn mẫu giả mạo này với chất lượng đồng đều là vô cùng khó khăn.
- **Sự khác biệt về phần cứng & môi trường**: Mô hình cần hoạt động ổn định dưới nhiều điều kiện ánh sáng (trong nhà, ngoài trời, ngược sáng) và các loại camera/cảm biến khác nhau. Các tập dữ liệu công khai lớn (như CASIA-SURF, OULU-NPU) chứa hàng triệu khung hình được ghi lại bằng các thiết bị chuyên dụng mà một dự án điểm danh thông thường khó tự trang bị đầy đủ.

### B. Overfitting Khi Tự Huấn Luyện Trên Tập Dữ Liệu Nhỏ
- Nếu tự thu thập dữ liệu quy mô nhỏ (vài trăm hoặc vài nghìn mẫu), mô hình học sâu sẽ rất dễ bị **overfitting** (quá khớp). Khi đó, mô hình sẽ hoạt động tốt trong phòng Lab thử nghiệm nhưng sẽ thất bại hoàn toàn (False Accept/False Reject cực cao) khi triển khai thực tế trên các camera và điều kiện môi trường khác.

### C. Kiến Trúc Mô Hình Đã Được Tối Ưu Hóa (MiniFASNet)
- Mô hình **MiniFASNet** (với các biến thể như MiniFASNetV1, MiniFASNetV1SE, MiniFASNetV2) sử dụng kiến trúc mạng gọn nhẹ (lightweight) được tối ưu hóa đặc biệt cho thiết bị di động và các hệ thống nhúng/edge devices.
- Mô hình đã tích hợp các cơ chế nâng cao như **Squeeze-and-Excitation (SE) blocks** để tập trung vào các kênh đặc trưng quan trọng nhất.
- Việc tự thiết kế một kiến trúc mạng tương đương và tìm kiếm siêu tham số (hyperparameter tuning) sẽ tiêu tốn hàng tuần hoặc hàng tháng nghiên cứu.

### D. Tối Ưu Hóa Tốc Độ Thực Thi Với ONNX
- Mô hình pretrained của Silent-Face-Anti-Spoofing dễ dàng được chuyển đổi sang định dạng **ONNX** và tối ưu hóa bằng **onnxruntime**.
- Điều này cho phép thực thi suy luận thời gian thực trực tiếp trên CPU (CPU Execution Provider) với độ trễ cực thấp (khoảng 30–80ms mỗi face crop), hoàn toàn tương thích với luồng xử lý multi-threading của OpenCV webcam runner trong dự án mà không cần trang bị GPU đắt tiền.

---

## 2. Giải Pháp Tích Hợp Chi Tiết Trong Dự Án

Thay vì tập trung vào huấn luyện, chúng tôi dành tài nguyên để thiết kế một hệ thống tích hợp vững chắc giúp bù đắp các hạn chế của mô hình đơn lẻ:

1. **Fast Voting (Lọc Trung Vị - Median score)**: 
   Sử dụng median filter trên cửa sổ 3–5 frame gần nhất của từng tracker để loại bỏ hoàn toàn các khung hình nhiễu nhất thời, giúp tăng độ ổn định của hệ thống lên rất nhiều.
2. **Chính Sách Đưa Ra Quyết Định (Decision Policy)**:
   - Nhận diện rõ ràng 3 trạng thái liveness: `LIVE` (Chấp nhận điểm danh), `SPOOF` (Từ chối ngay lập tức), và `UNCERTAIN` (Cần xác thực thêm).
   - Chỉ kích hoạt các thử thách chủ động (blink/head pose challenge) khi rơi vào trạng thái `UNCERTAIN` để tối ưu hóa trải nghiệm người dùng, giúp người dùng bình thường đi qua nhanh chóng mà không cần thực hiện tương tác phức tạp.
3. **Database Auditing & Ghi Nhận Event đầy đủ**:
   Ghi lại chi tiết từng điểm số `live_score`, `print_score`, `replay_score`, `spoof_score` cùng cờ `attendance_logged` để phục vụ công tác hậu kiểm và tinh chỉnh threshold trong tương lai.
