# Negotiation Engine (Bước 6)

Module Đàm Phán `services/negotiation_engine.py` là bộ máy xử lý logic trao đổi trực tiếp ("kéo thanh giá") 1-1 giữa CLB Mua và CLB Bán, giúp hệ thống không chỉ còn những màn Đấu Giá Công khai nữa.

## 1. Vòng Đời Đàm Phán (Negotiation Lifecycle)
Quá trình đàm phán đi qua 3 quy trình (States) chính:
- **`INQUIRY`**: Bên mua gửi lời hỏi thăm. Bên bán (hoặc máy) sẽ quyết định `Đồng Ý` (vào bàn đàm phán) hoặc `Từ Chối` (Hủy thương vụ ngay lập tức).
- **`NEGOTIATING`**: Điểm nổi bật nhất của tính năng. Khi đạt tới phase này, 2 bên bắt đầu chốt giá `current_offer` (giá ném ra) và `demand` (giá đòi hỏi). Ở state này, biến số `is_public_release_clause = True` được bật để Người Mua có thể nhìn thấy Mức phí phá vỡ hợp đồng của cầu thủ và đưa ra một lựa chọn Bid sát sườn.
  - **Cơ chế Q&A (Hỏi Đáp Tình Trạng)**: Trước khi chốt giá, hệ thống cung cấp 20 câu hỏi có sẵn xoay quanh 6 chủ đề (Thể trạng/Chấn thương, Lương thưởng, Lối chơi, Kỷ luật, Truyền thông...). Ở mỗi hiệp, bên đàm phán được quyền hỏi tối đa **4 câu hỏi**. Server sẽ nội suy câu trả lời thông minh dựa vào dữ liệu có thật trong CSDL (Vd: Dính thẻ đỏ nhiều thì Máy sẽ trả lời là "cầu thủ thường mất bình tĩnh").
- **`ACCEPTED` / `REJECTED` / `CANCELLED`**: Kết thúc đàm phán.

## 2. Luật Đàm Phán 3 Hiệp (Round Rules)
Mỗi bên có quyền nhượng bộ và điều chỉnh lại mức `offer` / `demand` của mình.
- Hệ thống duy trì một biến số đếm thời gian: `round_number`.
- Tố đa **3 Hiệp**. Khi bước sang hiệp 4 mà hai bên không chốt được nhau. Deal tự động bị `CANCELLED`.
- Nếu có một CLB chủ động ấn nút rút lui `cancel_negotiation`, tiến trình dừng lập tức.

## 3. Auto-Accept & Transfer (Chốt Giao Dịch)
Nếu CLB Mua trả một cái giá lớn hơn hoặc xấp xỉ ngưỡng Demand mà đối phương đưa ra (Độ tiệm cận `>= 95%`) thì thuật toán sẽ kích hoạt **Bắt Tay Thành Công**. Hàm `_execute_transfer` ngầm được chạy:
- Nó tự động trừ budget của người mua theo giá cuối cùng.
- Cộng tiền thẳng vào quỹ của bên bán.
- Sang tên đổi chủ cho Entity Cầu thủ, giải phóng hợp đồng cũ và cấp một hợp đồng mới toanh `4 năm`!
