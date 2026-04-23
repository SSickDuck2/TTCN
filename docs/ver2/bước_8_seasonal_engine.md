# Seasonal Stats Engine (Bước 8)

Module `services/seasonal_engine.py` là bộ máy "Kết toán Mùa Giải". Nó chạy **đúng một lần** vào thời điểm `TimeEngine` chuyển trạng thái sang `SEASON_UPDATE` (tháng 9 trong calendar của hệ thống).

## 1. Khi nào được kích hoạt?

`TimeEngine.trigger_season_update()` là điểm bắn, được móc vào `check_transitions()`. Khi ngày trong hệ thống bước sang Tháng 9 (mùa giải chính thức bắt đầu), `TimeEngine` sẽ tự động gọi:

```
TimeEngine → trigger_season_update()
               │
               ├── seasonal_engine.run_end_of_season(db)   # Tài chính
               └── contract.remaining_years -= 1           # Tuổi thọ HĐ
```

## 2. Công thức Tính Doanh Thu

Mỗi CLB nhận doanh thu từ **4 nguồn độc lập**, đều phụ thuộc vào thứ hạng cuối mùa (`season_position`):

| Nguồn | Công thức |
|---|---|
| **Tiền thưởng xếp hạng** | Bảng cố định: Hạng 1 = €100M, Hạng 20 = €15M |
| **Bản quyền phát sóng** | €50M × hệ số hạng (Top 4 UCL × 1.5, xuống hạng × 0.7) |
| **Doanh thu vé** | Số trận × €2.5M × tỉ lệ lấp đầy (dựa trên tỉ lệ thắng) |
| **Áo đấu & Merchandise** | €10M base + €500K × (10 - hạng) với Top 10 |

> [!NOTE]
> Bảng `PRIZE_MONEY_TABLE` được thiết kế tuân theo cơ chế phân phối tương đương EPL/La Liga và chuẩn hoá để áp dụng cho cả 5 giải.

## 3. Lịch sử Mùa Giải (ClubSeasonRecord)

Trước khi reset, toàn bộ dữ liệu mùa giải được **snapshot** vào bảng `club_season_records` gồm:
- Thành tích thi đấu: Hạng cuối, W/D/L, bàn thắng/thua
- Tài chính: Doanh thu từng nguồn, tổng doanh thu
- Budget đầu mùa vs Budget cuối mùa (biết được CLB đầu tư mạnh hay tích lũy)

## 4. Tự động hết hạn Hợp đồng

Sau khi tính tiền xong, `trigger_season_update()` quét **toàn bộ Contract ACTIVE** và giảm `remaining_years` đi 1. Nếu chạm `0`, hợp đồng tự động chuyển sang `TERMINATED`. Những cầu thủ hết hạn coi như tự do, sẵn sàng xuất hiện trên sàn Transfer kỳ tiếp theo với giá giảm mạnh (Contract Factor = 0.7).
