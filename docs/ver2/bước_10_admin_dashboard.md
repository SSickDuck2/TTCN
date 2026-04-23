# Bước 10: Admin, vận hành và kiểm soát dữ liệu

Tài liệu này mô tả chi tiết chức năng và cách vận hành các công cụ kiểm soát dữ liệu tại giao diện Admin (`/trade/admin`). Các chức năng này phục vụ mục đích kiểm thử (Testing), thuyết trình (Demo) và điều hành mô phỏng (Simulation).

## 1. Mục đích và Phạm vi
Admin Dashboard cung cấp giao diện trực quan cho người phát triển/trình bày dự án để can thiệp vào các kịch bản của trò chơi mà không cần phải chờ đợi logic thời gian thực hoặc phải tương tác trực tiếp với Database.

## 2. Các nhóm tính năng chính

### 2.1. Sức khỏe Hệ thống (System Health)
- Hiển thị số lượng Câu lạc bộ đang hoạt động trong Database.
- Đếm tổng số Hợp đồng cầu thủ.
- Cảnh báo "CLB Nợ ngân sách": Tự động phát hiện nếu có Câu lạc bộ nào bị âm tiền (`budget_remaining < 0`) do các sai lệch trong đàm phán hay trả lương.

### 2.2. Điều khiển Hệ thống & Thời gian (Time Control)
Module cốt lõi của tính năng Quản trị. Giúp thay đổi dòng thời gian:
- **Ép Trạng thái**: Cho phép admin chọn thủ công 4 trạng thái của game:
  - `TRANSFER_OPEN`: Mở cửa thị trường (cho phép Đấu giá, Đàm phán).
  - `TRANSFER_CLOSED`: Đóng cửa thị trường (khóa toàn bộ giao dịch mua bán).
  - `SEASON_UPDATE`: Đang cập nhật chỉ số cuối mùa.
  - `OFF_SEASON`: Giải lao nghỉ hè, chuẩn bị cho kỳ chuyển nhượng mới.
- **Tua nhanh thời gian**: Cho phép đẩy `current_date` của hệ thống nhảy vọt N ngày về tương lai (tối đa 365 ngày mỗi lần nhấn). Tính năng này dùng để kiểm tra việc "Hết hạn" (Expires) của Đàm phán và Đấu giá.

### 2.3. Trí tuệ Nhân tạo & Mô phỏng (AI Simulation)
- Nút **Trigger Simulation Now**: Thay vì chờ chu kỳ ngẫu nhiên của Server (10% cơ hội mỗi tick), nút này ép toàn bộ AI (các CLB ảo) thực hiện đánh giá ngân sách, tìm kiếm mục tiêu và tự động gửi lời "Hỏi mua (Inquiry)" hoặc "Đưa ra giá Counter" ngay lập tức. Tính năng này vô cùng quan trọng khi demo cho giáo viên thấy AI hoạt động như thế nào.

### 2.4. Khôi phục Dữ liệu Demo (Danger Zone)
Công cụ "vũ khí tối thượng" trước mỗi buổi báo cáo/thuyết trình:
- Đặt lại Thời gian (`current_date`) về **01/06/2024**.
- Chuyển hệ thống về trạng thái `TRANSFER_OPEN`.
- Xóa sạch mọi phiên Đàm phán (`Negotiations`) đang tồn tại.
- Xóa sạch mọi phiên Đấu giá (`MarketListings` và `Bids`).
- Phục hồi lại dòng tiền (`budget_remaining`) của toàn bộ các Câu lạc bộ về mốc **100 Triệu Euro**.

## 3. API Tham chiếu
Các tính năng UI gọi xuống các API sau của Backend:
- `GET /api/admin/system/health`
- `POST /api/admin/time/set-state`
- `POST /api/admin/time/advance`
- `POST /api/admin/simulation/trigger`
- `POST /api/admin/data/reset`
