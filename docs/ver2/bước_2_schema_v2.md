# Schema & Cấu trúc Mô-đun (Bước 2)

Tài liệu này tổng hợp lại các thành phần cốt lõi của Backend đã được thiết kế và bổ sung để hỗ trợ các chức năng Chuyển nhượng (Version 2).

## 1. Database Schema
Các bảng cơ sở dữ liệu mới đã được thêm vào `backend/database/models.py` với cấu trúc như sau:

### `SystemState` (Bảng trạng thái Thời gian)
Kiểm soát dòng thời gian chung của hệ thống.
* `current_state`: `TRANSFER_OPEN`, `TRANSFER_CLOSED`, `OFF_SEASON`, `SEASON_UPDATE`.
* `current_date`: Ngày giờ hiển thị mô phỏng (trong game).
* `season_year`: Năm của mùa bóng hiện tại.

### `Contract` (Bảng Hợp đồng)
Quản lý thỏa thuận giữa cầu thủ và CLB.
* `start_date`, `end_date`: Mốc thời gian của hợp đồng.
* `remaining_years`: Số năm hoàn thành (giúp dễ truy xuất tính phí).
* `base_salary`: Lương cơ bản.
* `release_clause`: Phí phá vỡ hợp đồng.
* Các khoản thưởng (`performance_bonus`, `loyalty_bonus`) và mức phí đền bù (`early_termination_fee`).
* `status`: Trạng thái (`ACTIVE`, `TERMINATED`, `TRANSFERRED`).

### `Negotiation` (Bảng Đàm phán)
Ghi chép tiến trình đàm phán mua cầu thủ giữa các CLB (Phase đàm phán kéo thanh giá).
* `buying_club_id`, `selling_club_id`, `player_id`.
* `current_offer`: Mức giá bên mua nộp vào hệ thống.
* `selling_club_demand`: Mức giá bên bán mong muốn.
* `round_number`: Số vòng trao đổi (1, 2, 3 vòng).
* `status`: `INQUIRY` -> `NEGOTIATING` -> `ACCEPTED` / `REJECTED` / `CANCELLED`.
* `is_public_release_clause`: Cờ đánh dấu lúc đàm phán thì khoản tiền release block có bị rò rỉ ra public không.

### `SimulationConfig` (Bảng Cấu hình CLB mô phỏng)
Thêm "bộ não" cho các CLB do máy tính điều khiển.
* `is_simulated`: `True`/`False`.
* `strategy`: Tư duy mua bán (VD: `BALANCED`, `AGGRESSIVE`, `SELLING_CLUB`).
* `willingness_to_sell`: Sẵn sàng nhả người (0 đến 1).
* `negotiation_flexibility`: Độ mềm mỏng khi nhượng bộ kéo giá.

---

## 2. Các Module Service Chức năng

Đã khởi tạo các file `Router` / `Service` ở cấp độ thư mục `backend/services/` với thiết kế rỗng (*skeleton functions*). Khi vào vòng code sâu, ta sẽ điền logic tại các file này:

1. **`time_engine.py`**: Xử lý logic làm trôi thời gian nhanh/chậm tùy thuộc vào state (*Timeskip engine*).
2. **`contract_engine.py`**: Tính toán `Market Value` (theo 3 loại Factor), che giấu thông tin private, trả về thông tin public. Sinh hợp đồng khi mua bán hoàn tất.
3. **`negotiation_engine.py`**: Nhận yêu cầu "hỏi mua", cập nhật mức giá hai bên báo giá cho nhau. Xử lý logic lúc người mua và bán "giao giá" và bấm chốt `ACCEPTED`.
4. **`simulation_engine.py`**: Chạy dưới dạng cron-job/background worker, quét ngẫu nhiên các CLB mô phỏng để tự động gửi thông điệp yêu cầu hỏi mua giúp *Chợ* trở nên sống động.
