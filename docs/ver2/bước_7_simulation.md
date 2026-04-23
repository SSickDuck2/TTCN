# Máy Mô phỏng Thế giới Game (Bước 7)

`SimulationEngine` (`services/simulation_engine.py`) mang linh hồn cho thị trường. Thay vì các CLB xung quanh đều là "Dead Entity", công cụ này giúp các CLB không do người chơi điều khiển tự quản lý ngân sách và đội hình.

## 1. Cơ chế Scout & Auto Buy (Chủ động Mua)
Được móc trực tiếp vào The Global Scheduler (Chạy nền mỗi 5s/lần) trong Event-loop của `api.py`. Logic `_auto_scan_market` thiết kế như sau:
- Mỗi chu kỳ 5 giây, các CLB được gán đặc quyền mô phỏng có 10% cơ hội ném tiền vào thị trường.
- **Parametrized Strategy**: Không phải CLB nào cũng mua giống nhau. Hệ thống sẽ quét qua bảng `SimulationConfig`. Nếu CLB bị gán `YOUTH_DEV`, thay vì mua cầu thủ nổi tiếng, bot sẽ chỉ target các mục tiêu `age <= 23`. Nếu là `VETERAN_PREF`, bot tìm cầu thủ `age >= 29`.
- Sau khi chọn được Goal, Bot tự động bắn một lệnh Inquiry cho CLB chủ quản của cầu thủ để kick-start Đàm Phán ở **Bước 6**.

## 2. Chủ thể Đàm phán thông minh
Kế thừa toàn bộ giao diện Negotiation của Bước 6, khi có User hoặc Bot khác vào đàm phán mua/bán, Bot sẽ phân tích giá bằng phương thức `_auto_negotiate`:

- Nếu Bot đứng vai trò Bán và nhận được lời `Inquiry`: Hàm check biến số `willingness_to_sell` (Từ 0 -> 1.0). Càng cao tỉ lệ Bot Agree Negotiation càng cao. Nếu nó Okie, máy sẽ Hét 1 cái giá cao gấp rưỡi (150%) so với `market_value_fair` tính ở Bước 4.
- Nếu ở vai trò Người đáp trả (`NEGOTIATING`): Thuật toán đong đếm chênh lệch giá, nếu đối phương nhượng bộ chạm ngưỡng xấp xỉ `+/- 10%`, Bot tự động submit Agree để đẩy thành trạng thái `ACCEPTED`. Máy có tính kiềm chế ngân quỹ khi luôn kiểm tra số dư Budget trước khi đặt cọc để tránh bị phạt FFP thay vì vung tiền vớ vẩn.
