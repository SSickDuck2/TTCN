# Time Engine & Transfer Window (Bước 3)

Tài liệu mô tả chi tiết logic hệ thống Quản lý Thời Gian Mô Phỏng (`TimeEngine`) được triển khai trong phiên bản V2.

## 1. Cơ chế State Machine
Hệ thống sử dụng mẫu thiết kế dạng Class Singleton có tên `TimeEngine` (nằm tại `backend/services/time_engine.py`) để đồng bộ hóa thời gian toàn trình.
State của hệ thống sẽ dựa trên Enum `SystemStateEnum`:
- **`TRANSFER_OPEN`**: Thị trường mở cửa (Mùa hè, Mùa đông).
- **`TRANSFER_CLOSED`**: Thị trường đóng cửa (Lúc diễn ra giải đấu thường ngày).
- **Trạng thái `NEGOTIATION`** (cục bộ): Khai thác từ việc Query trong bảng bảng `negotiations`.

## 2. Logic Trôi Thời Gian (Timeskip)
Hệ thống kết nối trực tiếp với Global `APScheduler` (chạy mỗi `1 giây` một lần).
Ở mỗi giây tick (thời gian thực tế của máy chủ), `TimeEngine` cộng dồn một giá trị `delta` ảo cho `current_date` dựa vào tình trạng hiện tại:

- **Có Đàm Phán đang mở (`NEGOTIATION`)**: `1 giây` = `1/300 ngày` (Tương đương tốc độ *5 phút thực = 1 ngày ảo*). Tốc độ chậm nhất để user hoặc máy có thời gian trao lặp và kéo thanh slide đàm phán mà không bị nhảy lố vài tuần.
- **Thị trường đón cửa (`TRANSFER_CLOSED`)**: `1 giây` = `1/5 ngày` (Tốc độ *5 giây thực = 1 ngày ảo*). Tốc độ nhảy cóc qua ngày thi đấu.
- **Thị trường mở cửa, không bận đàm phán (`TRANSFER_OPEN`)**: `1 giây` = `1/20 ngày` (Tốc độ *20 giây thực = 1 ngày ảo*). Tốc độ chuẩn cho trải nghiệm người dùng lướt săn tìm cầu thủ và đấu giá.

## 3. Chuyển trạng thái động (Auto-Transitions)
Sau khi ngày ảo (`cached_date`) bị nhảy, hệ thống gọi hàm `check_transitions()`:
1. Nếu tháng hiện tại là `Tháng 6, 7, 8` hoặc `Tháng 1`: Hệ thống tự động thiết lập trạng thái thành `TRANSFER_OPEN` để cho mọi người tham gia TTCN.
2. Nếu bước sang các tháng khác, trạng thái tự chuyển thành `TRANSFER_CLOSED`. Khi tháng 9 tới và vừa đóng cửa sổ chuyển nhượng thì hàm `trigger_season_update()` sẽ được gọi để tính/cộng stats của mùa giải trước (bước đệm cho Phrase Season Stats sau này).
3. Do thiết kế `TimeEngine` cache trạng thái trên RAM (`self.cached_state`), các request API sẽ không bị spam query tới Database để check trạng thái liên tục.

## 4. Bảo vệ Middleware Transfer Window
Đã cập nhật file `market_router.py`:
- Tính năng xem chợ, lọc thông tin, lấy Club `GET /api/market/players`, `GET /api/market/auctions` hoạt động bình thường kể cả khi đã đóng cửa (Cho phép scout lúc đóng chợ).
- Tính năng bắt đầu giao dịch, như Đấu giá (`POST /bid`), Đàm phán hay Kích hoạt phá vỡ hợp đồng sẽ bị Middleware khóa cứng nếu gọi khi `check_transfer_window_open() == False` trả về HTTP Status `403 Forbidden`.
