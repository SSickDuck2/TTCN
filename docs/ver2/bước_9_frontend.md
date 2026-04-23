# Bước 9: Kết nối Frontend & Backend V2

Bước 9 là bước cuối của giai đoạn Backend → Frontend integration. Toàn bộ logic được xây dựng từ Bước 3–8 được "đấu nối" với giao diện người dùng.

## 1. Bộ API Client Mở Rộng (`libs/api.ts`)

File `api.ts` được bổ sung đầy đủ các hàm gọi cho toàn bộ tính năng V2:

| Hàm | Mô tả |
|---|---|
| `getTimeStatus()` | Lấy ngày game + trạng thái TTCN |
| `sendInquiry(playerId)` | Gửi lời hỏi mua cầu thủ |
| `quickSellPlayer(playerId)` | Bán cầu thủ cho hệ thống |
| `getNegotiation(id)` | Chi tiết một phiên đàm phán |
| `respondToInquiry()` | Phản hồi Inquiry (Đồng ý/Từ chối) |
| `submitOffer()` | Gửi giá mua |
| `respondToOffer()` | Bên bán phản giá |
| `cancelNegotiation()` | Hủy đàm phán |
| `askNegotiationQuestion()` | Hỏi 1 trong 20 câu trong phiên đàm phán |
| `getNegotiationQuestions()` | Lấy danh sách 20 câu hỏi |

## 2. Component `TimeStatusBar`

Component nhỏ gọn được nhúng vào Header của `MainLayout`. Tự poll API `/time/status` mỗi 5 giây để cập nhật:
- **Trạng thái TTCN** (OPEN/CLOSED/SEASON_UPDATE) hiển thị bằng Tag màu động
- **Ngày hiện tại** trong game (định dạng dd/mm/yyyy)
- **Mùa giải** đang diễn ra

## 3. Trang Đàm phán (`/trade/negotiate`)

Giao diện đầy đủ gồm 3 phần:
- **Danh sách Card** — Tất cả phiên đàm phán đang diễn ra với tóm tắt giá + hiệp số
- **Modal chi tiết** — Khi bấm vào một Card, mở Modal với:
  - Thống kê round / giá (dạng Statistic card)
  - Giao diện trả lời Inquiry (Đồng ý kèm giá khởi điểm / Từ chối)
  - Giao diện Q&A với nút "Chọn câu hỏi" mở popup 20 câu
  - Thanh kéo giá (Slider) để Submit Offer / Counter
  - Nút hủy đàm phán có xác nhận
- **Log Q&A** — Hiển thị lịch sử hỏi đáp trong Modal

## 4. Backend Routers mới

| File | Prefix | Chức năng |
|---|---|---|
| `routers/negotiation_router.py` | `/api/negotiations` | Toàn bộ CRUD Negotiation |
| `routers/time_router.py` | `/api/time` | Endpoint trả về TimeEngine status |

Cả hai router đã được đăng ký vào `api.py`.
