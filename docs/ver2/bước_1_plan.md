# Bước 1: Chốt phạm vi và mô hình dữ liệu (V2)

Dưới đây là phần chốt logic cho hệ thống dựa trên sự thống nhất giữa hai bên.

## 1. Các trạng thái thời gian và Thời gian trôi (Timeskip)
Hệ thống sẽ chạy một `TimeEngine` với các quy tắc tiến triển thời gian thực tế:

* **`TRANSFER_OPEN`**: Thị trường mở cửa.
    * **Kỳ chuyển nhượng Mùa hè (1/6 - 31/8)**: Diễn ra lúc giải đấu đã kết thúc (`OFF_SEASON` của các giải đấu). Các CLB tập trung hoàn toàn vào mua bán, chuẩn bị lực lượng.
    * **Kỳ chuyển nhượng Mùa đông (Tháng 1)**: Diễn ra song song với lúc giải đấu vẫn đá, giúp CLB bổ sung thêm cầu thủ chấn thương/xuống phong độ.
    * *Tốc độ thời gian*: **20 giây = 1 ngày**. Cho phép mọi hành động `Hỏi mua trực tiếp`, `Đấu giá`, `Đàm phán giá`, `Phá hợp đồng`.
* **`TRANSFER_CLOSED`**: Thị trường đóng cửa (trong thời gian mùa giải diễn ra, ngoại trừ tháng 1). 
    * *Tốc độ thời gian*: **5 giây = 1 ngày** (Vì chủ yếu đá giải, chạy nhanh qua ngày). Chỉ cho phép `Khảo sát (scout)`, `Xem thông tin`, `Gửi tín hiệu quan tâm` (Inquiry). Không cho phép chốt hợp đồng.
* **`NEGOTIATION`** (Trạng thái cục bộ khi đàm phán):
    * Khi một/hai CLB đồng ý đàm phán, hai bên sẽ bước vào Phase đàm phán. 
    * *Tốc độ thời gian cục bộ*: **5 phút = 1 ngày** cho 2 bên tham gia. Đàm phán thường kết thúc nhanh trong 2-3 ngày.
    * *Luật kết thúc*: Khi đàm phán hoàn tất (chốt deal/hủy), ngày hôm đó đối với 2 CLB có thể trực tiếp kết thúc sớm để trở lại nhịp bình thường.
* **`SEASON_UPDATE`**: Trạng thái lock cục bộ để chạy background job cộng dồn dữ liệu thi đấu định kỳ.

## 2. Bảng dữ liệu hợp đồng cầu thủ (Contract Schema Suggestions)
Dữ liệu hợp đồng sẽ lưu bảng riêng. Bảng `contracts`:
* `id` (PK)
* `player_id` (FK)
* `club_id` (FK)
* `start_date` (DateTime)
* `end_date` (DateTime) 
* `remaining_years` (Integer) - Tính toán từ `end_date`.
* `base_salary` (Decimal) - Lương cơ bản.
* `release_clause` (Decimal) - Phí phá vỡ hợp đồng.
* `performance_bonus` (Decimal) - Thưởng thành tích.
* `loyalty_bonus` (Decimal) - Thưởng trung thành.
* `early_termination_fee` (Decimal) - Phí đền bù nếu CLB hủy hợp đồng.
* `status` (Enum: `ACTIVE`, `TERMINATED`, `TRANSFERRED`)

## 3. Phân quyền dữ liệu công khai / riêng tư (Visibility)
* **Công khai (Public)** - *View của tất cả các CLB:* 
  * Tên cầu thủ, CLB hiện tại.
  * Tình trạng (Sẵn sàng bán, Không bán).
  * `remaining_years` (Thời hạn còn lại).
  * Lương ước tính (Hiển thị dạng range, VD: `100k - 150k`).
  * `market_value` (Giá trị thị trường).
* **Riêng tư (Private) / Có điều kiện**: 
  * Con số chính xác của `base_salary`, `performance_bonus`, `loyalty_bonus` và `early_termination_fee` chỉ có CLB chủ quản xem được.
  * **`release_clause`**: Mặc định ẨN với đội đối thủ. Tuy nhiên, khi một CLB tham gia hoặc gửi lời đề nghị đàm phán chính thức, điều khoản này sẽ được **CÔNG KHAI** (hiển thị) trong tiến trình đàm phán.

## 4. Cách định giá cầu thủ (Player Valuation Formula)
`Market Value = Base Ability Value x Contract Factor x Form Factor`

* **Contract Factor**: Cầu thủ còn hợp đồng dài (>3 năm) -> Giá giữ nguyên hoặc nhân hệ số cao. Cầu thủ sắp hết hạn (< 1 năm) -> Giá rớt mạnh (hệ số ~ 0.6 - 0.7).
* **Form Factor (Phong độ)**: Update liên tục ở đợt `SEASON_UPDATE` phụ thuộc vào bàn thắng, kiến tạo, số phút thi đấu.

## 5. Quy tắc mua bán & Transfer Window Lock
Quản lý bằng Middleware ở Backend. Giao dịch mua/bán bắt buộc phải diễn ra khi `TimeEngine` ở trạng thái `TRANSFER_OPEN`. Nếu cố tình Request khi đã đóng cửa, Server chặn và trả lỗi `403 Forbidden`.
