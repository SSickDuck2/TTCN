# Thị trường Chuyển nhượng & Đấu giá (Bước 5)

Module Quản lý Market tại `routers/market_router.py` đóng vai trò điều phối các luồng tiền tệ và phân tách các loại hình giao dịch thay vì gộp chung một cục như bản V1.

## 1. Đồng bộ Logic với Hệ thống Hợp đồng Kép
Tài nguyên từ **Bước 4 (Contract Engine)** đã được kết nối thẳng vào hàm `resolve_auction()` tại `utils/services.py`. 
- Khi một cuộc đấu giá kết thúc thành công với người thắng cuộc (`winning_club`), server sẽ trừ phí chuyển nhượng tự động, cộng lương vào `wage_spent` (Luật Công Bằng Tài Chính FFP).
- Sau đó, `contract_engine.create_contract(...)` được gọi. Nó sẽ kết thúc hợp đồng cũ (Chuyển sang `TRANSFERRED`) và ký một hợp đồng mới toanh thời hạn 4 năm giữa Cầu thủ và CLB trúng thầu. Mọi thứ được gói gọn trong 1 Transaction DB để không bị sai lệch dữ liệu.

## 2. Các luồng giao dịch độc lập
Giờ đây TTCN chia làm các luồng rõ ràng, phù hợp với Game Simulation:

- **Đấu giá (Auction / Bid)**: Cấu trúc tính Budget Lock và Bid được giữ nguyên độ ổn định. Nhưng API đã bị chặn khi TTCN (`TimeEngine`) phát tín hiệu đóng cửa.
- **Bán tháo nhanh (Quick Sell)** `POST /quick-sell`:
  - Người chơi / Bot có thể gọi API này để bán thẳng cầu thủ lấy tiền giải phóng quỹ lương.
  - Tuy nhiên, bị hệ thống "ép giá" mất 50% so với Giá Trị Thị Trường Thực Tế (`market_value` tính bằng Engine Bước 4). Tiền được hoàn trả tức thì và Hợp đồng cầu thủ rơi vào trạng thái bị huỷ.
- **Hỏi Mua Trực Tiếp (Inquiry)** `POST /inquire`:
  - Cho cầu thủ đang thuộc biên chế một đội bóng khác và đội đó chưa ném cầu thủ lên chợ đấu giá. CLB có thể trực tiếp gửi Inquiry. File sẽ Insert một tín hiệu vào Database đàm phán (`Negotiation`) với state = `INQUIRY`. (Là tiền đề để Bước 6 - Đàm chán hai bên diễn ra).
