# Contract Engine & Valuation System (Bước 4)

Việc quản lý Hợp đồng và Định giá cầu thủ là một nội dung cốt lõi trong version 2. Module `ContractEngine` (`backend/services/contract_engine.py`) chịu trách nhiệm trung chuyển dữ liệu tùy theo quyền truy cập và tính toán giá trị thị trường liên tục.

## 1. Cơ chế Tạo/Cập nhật Hợp đồng
Mỗi khi có một thương vụ chốt deal hoàn tất, hệ thống gọi hàm `create_contract()`:
1. Đặt thuộc tính `status = TRANSFERRED` cho tất cả các bản hợp đồng đang Active của cầu thủ hiện tại (Nhằm lưu lại Historical logs).
2. Thiết lập object bản hợp đồng mới với ngày kết thúc (tính theo năm), thiết lập `base_salary`, và `release_clause` cùng các phụ phí tùy chọn. Trạng thái của file mới này là `ACTIVE`.

## 2. Công thức Định giá Thị trường (Market Valuation Formula)
Giá trị của một cầu thủ không cố định mà được nội suy từ chỉ số gốc trong DB (`market_value_in_eur` của Transfermarkt) nhân với 3 biến số: `Fair Value = Base * Age * Contract * Form`
- **Age Factor**: Phản ánh giá trị tiềm năng. Tuổi trẻ (≤23) được cộng thêm giá trị x1.2. Tuổi lão tướng (≥32) bị giảm giá trị x0.8.
- **Contract Factor**: Phản ánh rủi ro mất trắng. Nếu hợp đồng còn xông xênh ≥ 3 năm, cầu thủ rất có giá (x1.2). Nếu hợp đồng sắp hết (≤ 1 năm), CLB thường phải bán tháo (x0.7).
- **Form Factor**: Mô phỏng phong độ linh hoạt tùy theo Vị trí (Position) dựa vào Data có sẵn:
  - **Tiền đạo (FW)**: Đánh giá bằng tổng Bàn thắng/Kiến tạo hoặc xG/xA. Nếu > 15 thì tăng 1.15. Nếu < 3 nhưng đá nhiều thì rớt giá 0.9.
  - **Tiền vệ (MD)**: Gắn với khả năng phát động (xGChain, xGBuildup) và số đường chuyền quyết định (Key Passes) để tăng hoặc giảm.
  - **Hậu vệ (DF)**: Chủ yếu chấm điểm dựa trên độ ổn định (số phút thi đấu), kỷ luật (bị rớt giá mạnh nếu dính nhiều thẻ vàng/đỏ) và kỹ năng phát động từ sân nhà (xGBuildup).
  - **Thủ môn (GK)**: Đánh giá độ uy tín bằng số phút thi đấu thực tế trên sân. Càng cày ải nhiều thì Form Factor càng cao.

*Công thức này sẽ được gọi ngầm khi User lướt trang Market để có một con giá chuẩn trước khi Bid.*

## 3. Phân cấp dữ liệu Công Khai và Riêng Tư (Public/Private Visibility)

### Dữ liệu Công Khai (`get_public_info`)
Tất cả các CLB chỉ xem được:
- Lương dạng khoảng ước tính (VD: Không hiển thị `50,000$` mà sẽ hiện chuỗi `40,000 - 60,000`).
- Giá trị định giá mới nhất (`market_value` tính nhờ công thức bên trên).
- `release_clause` và `loyalty_bonus` bị che kín hoàn toàn.

### Dữ liệu Riêng Tư (`get_private_info`)
Chỉ hiển thị con số chính xác (`exact_base_salary`, `release_clause`, v.v..) khi thoả mãn một trong 2 điều kiện:
1. ID của CLB Call API khớp với `club_id` đang đứng tên trên Hợp Đồng.
2. (Rule Mở Nút Đàm Phán): Truy vấn vào bảng `Negotiations`, nếu thương thảo đạt trạng thái `is_public_release_clause = True`, hệ thống cấp quyền xem con số phí phá hợp đồng cho bên Mua đang đàm phán trực tiếp để họ cân nhắc trả giá hợp lý.
