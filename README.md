# TTCN (Transfermarkt Club Network)

Repo này chứa mã nguồn để triển khai hệ thống mô phỏng Thị trường Chuyển nhượng Cầu thủ Bóng đá. Dự án đã được tái cấu trúc hoàn toàn với kiến trúc Server (FastAPI) đa module và Frontend hiện đại (Next.js + Ant Design).

Dưới đây là chi tiết chức năng của các file và thư mục có trong dự án:

## 1. Backend (FastAPI, WebSockets, SQLAlchemy)
Hệ thống backend đã được chia module chuẩn hóa để dễ dàng mở rộng và bảo trì.

- **`api.py`**: Trái tim khởi chạy server gốc. Thực hiện việc đăng ký Middleware (CORS) để liên kết với Next.js, cài đặt vòng lặp APScheduler (job đấu giá) và đăng ký các endpoints của hệ thống qua Routers.
- **Thư mục `backend/`**:
  - `auth.py`: Quản lý JWT token, mã hóa password và kiểm tra thông tin Club (CLB) đăng nhập.
  - `config.py`: File đọc tập trung các biến môi trường từ `.env` (như `DATABASE_URL`, Cấu hình ngân sách tối đa...).
  - `schemas.py`: Định nghĩa Pydantic Models để xác thực dữ liệu Input/Output của các Request và Response API chuẩn hoá.
  - `services.py`: Cung cấp hàm Logic hệ thống cốt lõi: xử lý check Công bằng tài chính (FFP), chuyển/khoá tiền budget, lên lịch phân luồng phiên thắng đấu giá hoặc bán nhanh.
  - `state.py`: Quản lý Local State nâng cao (Global RAM): `manager` cho các dòng dữ liệu WebSocket realtime, và `scheduler` phục vụ lên lịch nền (Background jobs).
- **Thư mục `routers/`**: Phân tách logic API ra các file nhỏ gọn thay vì gom chung:
  - `admin_router.py`: API dành riêng cho nội bộ quản lý hệ thống.
  - `auth_router.py`: Gồm endpoint `/login` và cấp token.
  - `market_router.py`: Thị trường chung, xử lý load thẻ cầu thủ và phiên đấu giá `/auctions`. Đặt bid.
  - `player_router.py`: Tra cứu chi tiết một thẻ cầu thủ.
  - `squad_router.py`: Thao tác mua bán, kiểm tra lực lượng đội hình riêng của Club đang đăng nhập.
  - `ws_router.py`: Trìu tượng endpoint Websocket để cập nhật thay đổi đấu giá trực tiếp đến Frontend.

## 2. Database & Data Scripts
- **Thư mục `database/`**:
  - `database.py`: Xử lý khởi tạo Engine và gán liên kết (Session) tới DB SQLite từ thư mục cục bộ hoặc PostgreSQL.
  - `models.py`: Chứa các lược đồ SQLAlchemy ORM chuẩn như Bảng `Club` (CLB đội), `PlayerInfo` (chỉ số Cầu thủ), `MarketListing` và `Bid` để phục vụ theo dấu phiên giao dịch diễn ra.
  - `ttcn.db`: CSDL (SQLite) hệ thống, lưu toàn bộ trạng thái tài nguyên của Server.
- **Thư mục `scripts/`**: Chứa công cụ thu thập thông tin và Reset dữ liệu ban đầu
  - `kaggle_soccerdata_merge.py`: Kéo và đồng bộ Data Matching giữa hệ số của **FBref** với mức định giá của mảng cầu thủ bóng đá **Transfermarkt**.
  - `import_playerinfo.py`: Đổ các dòng CSV vào thẳng CSDL bảng `player_info`.
  - `init_clubs.py`: Seed data CLB gốc (như Arsenal, Man City, Real...) kèm số tiền để mô phỏng ban đầu.
  - `update_tm_clubs.py`: Script chuẩn hoá format tên CLB gọn gàng hơn.
- **`merged_fbref_transfermarkt.csv`**: File dataset CSV lớn lưu cấu trúc sau khi scraping dùng làm dữ liệu Data Warehouse.

## 3. Frontend (Next.js App Router)
Thư mục **`frontend/`** thay thế hoàn toàn hệ thống giao diện mẫu (Jinja2) tĩnh cũ bằng Next.js sử dụng port `3000`.

- Giao tiếp với API FastAPI thông qua tệp `libs/api.ts` (Tự động nạp Auth Token).
- Tích hợp chuẩn giao diện UI từ **Ant Design (Antd)** kết hợp Layout Grid của **Bootstrap**.
- Hỗ trợ công nghệ **WebSockets Client** nhận Live updates 100% thời gian thực từ đấu giá chợ.
- **Luồng trang chính:**
  - `/`: Trang cổng đăng nhập (Login Page).
  - `/trade/market`: Layout thị trường mở, liệt kê Data thẻ cầu thủ có sẵn để định giá.
  - `/trade/squad`: Bảng điều khiển riêng của bạn (Thống kê đội hình của Club).
  - `/trade/auction`: Bảng tập trung quản lý các phiên Live Auction.
  - `/trade/player/[id]`: Giao diện soi chỉ số cá nhân, timeline Websocket giá được update liên tục.

## 4. Documentation & Files cấu hình khác
- **`.env`** & **`.env.example`**: Quản lý biến môi trường bảo mật (DB Url, JWT secret) cho FastAPI.
- **`requirements.txt`**: Danh sách modules của Python hỗ trợ server BE cài qua `pip`.
- **`API_README.md`**: Thông số đặc tả kỹ thuật chi tiết của các nhánh logic gọi API FastAPI.
- **Thư mục `docs/` & `archive/`**: Chứa tài liệu, file sơ đồ UML hoặc log code cũ nghiên cứu từ ban đầu.