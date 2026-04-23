# Thiết kế state machine thời gian, transfer window, đàm phán và hợp đồng

## Checklist triển khai version 2

### 1. Chốt phạm vi và mô hình dữ liệu
- [x] Chốt các trạng thái hệ thống: `OFF_SEASON`, `TRANSFER_OPEN`, `TRANSFER_CLOSED`, `NEGOTIATION`, `SEASON_UPDATE`.
- [x] Chốt bộ trường dữ liệu hợp đồng cầu thủ: thời hạn, lương, thưởng, điều khoản giải phóng, phí phá hợp đồng.
- [x] Chốt phân quyền dữ liệu công khai và dữ liệu riêng tư của hợp đồng.
- [x] Chốt cách định giá cầu thủ dựa trên hợp đồng, phong độ và giá trị thị trường.
- [x] Chốt quy tắc mua bán chỉ hợp lệ trong transfer window.

### 2. Nền tảng dữ liệu và backend lõi
- [x] Thiết kế schema/bảng cho hợp đồng cầu thủ.
- [x] Thiết kế schema/bảng cho trạng thái mùa giải và lịch chuyển nhượng.
- [x] Thiết kế schema/bảng cho đàm phán hỏi mua và lịch sử trao đổi.
- [x] Thiết kế schema/bảng cho CLB mô phỏng và cấu hình hành vi.
- [x] Thêm migration/seed dữ liệu cho các bảng mới.
- [x] Tách service backend thành các module rõ ràng: time, contract, negotiation, season stats, simulation.

### 3. Time engine và transfer window
- [x] Tạo bộ điều phối thời gian dạng state machine.
- [x] Áp dụng timeskip theo trạng thái: ngoài TTCN, trong TTCN, và khi đàm phán.
- [x] Kiểm tra và khóa toàn bộ hành động chuyển nhượng ngoài transfer window.
- [x] Cho phép các hành động chỉ đọc khi thị trường đóng.
- [x] Tạo cơ chế chuyển trạng thái tự động theo lịch mùa giải.

### 4. Contract engine
- [x] Hiển thị thông tin công khai của cầu thủ cho CLB khác.
- [x] Hiển thị thông tin hợp đồng riêng tư cho CLB sở hữu.
- [x] Tính phí phá hợp đồng theo thời hạn còn lại và cấu trúc lương/thưởng.
- [x] Tính ngưỡng giá hợp lý cho hỏi mua và đấu giá.
- [x] Cập nhật trạng thái hợp đồng khi cầu thủ được bán hoặc giải phóng.

### 5. Transfer, market và auction
- [x] Khóa luồng đấu giá khi transfer window đóng.
- [x] Bảo đảm bid chỉ hợp lệ khi đủ budget và FFP.
- [x] Đồng bộ trạng thái đấu giá với dữ liệu cầu thủ và CLB.
- [x] Xử lý chốt deal, hoàn tiền/giải phóng budget lock và chuyển cầu thủ.
- [x] Thêm cơ chế quick sell, auction và hỏi mua trực tiếp thành các luồng riêng.

### 6. Negotiation engine
- [x] Tạo luồng `inquiry_sent` -> `inquiry_received` -> `negotiating`.
- [x] Thiết kế 3 vòng trao đổi có câu hỏi có/không.
- [x] Thiết kế pha đàm phán giá bằng thanh giá hai đầu.
- [x] Áp dụng timeout 30 giây cho pha đàm phán giá.
- [x] Thêm nút rút đàm phán cho cả hai phía.
- [x] Tự động chốt deal khi hai mức giá giao nhau trong ngưỡng cho phép.

### 7. CLB mô phỏng và thị trường sống động
- [x] Seed sẵn danh sách CLB để thị trường không bị rỗng.
- [x] Gán ngân sách, quỹ lương và chiến lược mua bán cho từng CLB mô phỏng.
- [x] Viết script/job nền tạo hành vi tự động: hỏi mua, phản giá, đấu giá, rút lui.
- [x] Cho phép chuyển giữa `manual mode` và `simulation mode`.
- [x] Bảo đảm 2 dev có thể đóng vai 2 CLB chính trong demo.

### 8. Seasonal stats engine
- [x] Xác định thời điểm cộng dồn chỉ số mùa giải.
- [x] Cập nhật dữ liệu trận, bàn thắng, kiến tạo, phút thi đấu, thẻ phạt, phong độ.
- [x] Đồng bộ stats mùa với định giá và điều khoản hợp đồng.
- [x] Không cập nhật nặng theo từng ngày để tránh tốn tài nguyên.

### 9. Frontend và trải nghiệm người dùng
- [x] Thiết kế màn chi tiết cầu thủ với thông tin công khai/riêng tư tách rõ.
- [x] Thiết kế màn transfer market với filter, giá, trạng thái chuyển nhượng.
- [x] Thiết kế màn đàm phán với tiến trình 3 vòng trao đổi và thanh giá.
- [x] Thiết kế UI cho trạng thái thị trường mở/đóng và trạng thái mùa giải.
- [x] Thiết kế dashboard cho CLB, ngân sách, hợp đồng và đội hình.

### 10. Admin, vận hành và kiểm soát dữ liệu
- [x] Thêm công cụ khởi tạo mùa giải, mở/đóng transfer window.
- [x] Thêm công cụ chạy/điều khiển simulation theo chu kỳ.
- [x] Thêm công cụ reset dữ liệu demo khi cần trình bày.
- [x] Thêm kiểm tra budget lock, hợp đồng và trạng thái cầu thủ.

### 11. Kiểm thử và validation
- [ ] Test đăng nhập, xác thực và phân quyền.
- [ ] Test các luồng market, bid, auction, sell, hỏi mua và đàm phán.
- [ ] Test khóa giao dịch khi transfer window đóng.
- [ ] Test chốt deal và cập nhật dữ liệu sau chuyển nhượng.
- [ ] Test mô phỏng CLB tự động trong nhiều kịch bản.
- [ ] Test seasonal stats sau mỗi mốc mùa giải.

### 12. Hoàn thiện tài liệu và báo cáo
- [ ] Viết lại mô tả nghiệp vụ version 2 thành bản ngắn gọn để báo cáo.
- [ ] Ghi rõ các quyết định thiết kế đã chọn và lý do chọn.
- [ ] Chụp màn hình/ghi hình các luồng chính để minh họa.
- [ ] Tổng hợp hạn chế hiện tại và hướng phát triển tiếp theo.

### 13. Thứ tự ưu tiên đề xuất
- [ ] P1: time engine, transfer window, contract engine.
- [ ] P2: market, auction, negotiation.
- [ ] P3: CLB mô phỏng, seasonal stats, admin tools.
- [ ] P4: hoàn thiện frontend, kiểm thử, báo cáo và trình bày.

## 1. Mục tiêu
Tài liệu này mô tả một lớp điều phối thời gian cho TTCN để:

- Chỉ cho phép giao dịch khi thị trường chuyển nhượng đang mở.
- Làm cho thời gian mùa giải có ý nghĩa thực tế hơn.
- Có mô hình hợp đồng đủ để định giá và xử lý cầu thủ hợp lý hơn.
- Hỗ trợ các pha đàm phán chuyển nhượng thay vì chỉ đấu giá đơn giản.
- Giảm tần suất cập nhật nặng, nhưng vẫn giữ được tiến trình mùa giải và thống kê cầu thủ.

## 2. Mô hình hợp đồng cầu thủ
Mỗi cầu thủ nên gắn với một bản hợp đồng tại CLB hiện tại. Hợp đồng được chia làm 2 lớp thông tin:

### 2.1. Thông tin công khai
CLB khác chỉ nên thấy các thông tin đủ để tham khảo thị trường:

- Tên cầu thủ.
- CLB hiện tại.
- Thời hạn hợp đồng còn lại.
- Mức lương tham khảo hoặc khoảng lương.
- Giá trị thị trường hiện tại.
- Tình trạng sẵn sàng chuyển nhượng.

### 2.2. Thông tin riêng tư
CLB sở hữu cầu thủ mới được thấy dữ liệu nội bộ:

- Mức lương thực trả.
- Các khoản thưởng.
- Phí trung thành.
- Điều khoản giải phóng.
- Phí phá hợp đồng sớm.
- Các ràng buộc đặc biệt.

### 2.3. Trường dữ liệu gợi ý
- `player_id`
- `club_id`
- `start_date`
- `end_date`
- `remaining_years`
- `base_salary`
- `signing_bonus`
- `performance_bonus`
- `loyalty_bonus`
- `release_clause`
- `early_termination_fee`
- `visibility_level`
- `status`

### 2.4. Tác động lên nghiệp vụ
Hợp đồng làm cho hệ thống có thêm 3 hành động quan trọng:

- Hỏi mua và đàm phán giá dựa trên thời hạn còn lại và lương.
- Đấu giá công khai như một cách chuyển nhượng mở.
- Phá hợp đồng trước hạn với phí đền bù thay đổi theo từng cầu thủ.

## 3. Trạng thái thời gian
Hệ thống nên coi thời gian trong game là một state machine, thay vì cho chạy tự do theo thời gian thực.

### 3.1. Các trạng thái chính
- `OFF_SEASON` - ngoài mùa hoặc ngoài giai đoạn vận hành chính.
- `TRANSFER_OPEN` - cửa sổ chuyển nhượng mở.
- `TRANSFER_CLOSED` - cửa sổ chuyển nhượng đóng.
- `NEGOTIATION` - đang đàm phán với một CLB khác.
- `SEASON_UPDATE` - mốc cập nhật chỉ số mùa giải.

### 3.2. Quy ước timeskip
- Khi thị trường đóng: `5 giây = 1 ngày`.
- Khi thị trường mở: `20 giây = 1 ngày`.
- Khi đang đàm phán với một CLB khác: `5 phút = 1 ngày`.

Mục tiêu của quy ước này là làm cho giai đoạn đàm phán đủ chậm để hai bên tương tác, nhưng các giai đoạn còn lại vẫn trôi đủ nhanh để demo mùa giải mà không phải chờ lâu.

## 4. Transfer window
Hệ thống chỉ nên cho chốt giao dịch trong 2 khoảng thời gian giống thực tế:

- Từ **1/6 đến 31/8**.
- Trong **tháng 1**.

### 4.1. Khi thị trường đóng
Khi ở trạng thái `TRANSFER_CLOSED`, hệ thống vẫn có thể:

- xem thông tin cầu thủ,
- gửi tín hiệu quan tâm,
- chuẩn bị đàm phán,
- theo dõi danh sách mục tiêu.

Nhưng không cho:

- chốt mua bán,
- đặt bid chính thức,
- đưa cầu thủ lên đấu giá,
- ký chuyển nhượng ngay lập tức.

### 4.2. Khi thị trường mở
Khi ở trạng thái `TRANSFER_OPEN`, hệ thống cho phép:

- hỏi mua trực tiếp,
- đàm phán giá,
- đấu giá,
- bán nhanh,
- phá hợp đồng theo điều khoản.

## 5. Nhánh hỏi mua và đàm phán
Nếu một CLB chủ động gửi lời đề nghị hỏi mua, hệ thống không đi thẳng sang chốt giá mà chuyển sang `NEGOTIATION`.

### 5.1. Ý tưởng tổng quát
Luồng nên chia thành 2 lớp:

1. **Trao đổi**: hai bên hỏi và trả lời các câu hỏi có/không để xác định thiện chí, thời hạn, mức sẵn sàng bán.
2. **Đàm phán giá**: hai bên điều chỉnh mức giá mong muốn cho đến khi hai bên “bắt tay” ở một mức chung.

### 5.2. Cấu trúc đàm phán
- Mỗi cuộc đàm phán có tối đa **3 vòng trao đổi**.
- Sau 3 vòng trao đổi, mới bước sang **pha đàm phán giá**.
- Pha đàm phán giá có tối đa **30 giây**.
- Nếu hết thời gian mà chưa chốt, cuộc đàm phán thất bại.

### 5.3. Cơ chế trao đổi
Mỗi vòng trao đổi nên là một chuỗi câu hỏi ngắn theo kiểu có/không, ví dụ:

- CLB mua có nghiêm túc không?
- CLB bán có sẵn sàng lắng nghe đề nghị không?
- Cầu thủ có nằm trong danh sách được phép bán không?
- Hai bên có muốn đi tiếp sang giai đoạn giá không?

Kết quả của pha trao đổi là một trong các trạng thái:

- `continue`
- `stop`
- `move_to_price`

### 5.4. Cơ chế đàm phán giá bằng thanh giá
Pha đàm phán giá nên dùng một thanh giá trực quan với 2 đầu tay:

- Bên trái là **CLB mua**.
- Bên phải là **CLB bán**.
- Mỗi bên có thể kéo tay của mình tới mức giá mong muốn.
- Giao dịch chỉ chốt khi hai tay gặp nhau hoặc chồng lên nhau trong một ngưỡng chấp nhận.

Cơ chế này nên hiển thị rõ:

- giá đề nghị của bên mua,
- giá yêu cầu của bên bán,
- khoảng cách còn lại giữa hai bên,
- độ nhượng bộ qua từng vòng.

Ý tưởng này có thể lấy cảm hứng từ các cơ chế `negotiation slider` thường gặp trong game mô phỏng thể thao, đặc biệt kiểu đàm phán chuyển nhượng trong các game bóng đá. Cái chính là giữ được cảm giác “hai bên kéo giá về phía mình” trước khi bắt tay.

### 5.5. Quy tắc chốt giá
- Nếu mức giá của bên mua >= mức giá tối thiểu của bên bán, chốt deal.
- Nếu bên bán hạ giá xuống gần tay bên mua trong ngưỡng chấp nhận, chốt deal.
- Nếu hai bên không gặp nhau trong 30 giây, đàm phán thất bại.

## 6. Hủy đàm phán
Cần có nút rút lui cho cả hai phía.

### 6.1. Người dùng rút đàm phán
Dev hoặc CLB người chơi có thể bấm rút để:

- hủy cuộc đàm phán hiện tại,
- trả trạng thái cầu thủ về trước đó,
- giải phóng các lock tạm thời nếu có.

### 6.2. Bên còn lại rút đàm phán
CLB đối phương cũng có thể rút lui nếu:

- giá quá cao,
- thay đổi chiến lược,
- cầu thủ không còn phù hợp,
- họ nhận đề nghị khác tốt hơn.

### 6.3. Nếu đàm phán với máy
Khi đối phương là CLB mô phỏng, cần có script/rule xử lý tự động:

- có xác suất đồng ý theo mức giá,
- có xác suất rút lui theo ngân sách và chiến lược,
- có xác suất phản giá nếu chênh lệch còn lớn.

## 7. Kết quả sau khi chốt deal
Nếu hai bên bắt tay thành công:

- cầu thủ chuyển nhượng ngay lập tức,
- hợp đồng cũ kết thúc hoặc được cập nhật trạng thái đã bán,
- CLB mua nhận cầu thủ mới,
- CLB bán nhận tiền theo mức chốt.

## 8. Cập nhật chỉ số mùa giải
Vì hệ thống dùng timeskip nên không nên cập nhật stats từng ngày. Chỉ nên cập nhật theo các mốc lớn.

### 8.1. Khi nào cập nhật
- Đầu mùa.
- Khi mở cửa TTCN.
- Sau khi kết thúc một giai đoạn mùa giải lớn.

### 8.2. Dữ liệu cần cộng dồn
- Số trận ra sân.
- Bàn thắng.
- Kiến tạo.
- Phút thi đấu.
- Thẻ vàng/thẻ đỏ.
- Phong độ tổng quan.

### 8.3. Mục đích
- Làm cho hợp đồng và định giá có ý nghĩa theo thời gian.
- Không tạo áp lực phải ghi dữ liệu liên tục từng ngày.
- Giữ cho mô phỏng đủ nhẹ để chạy ổn định trên máy cá nhân.

## 9. Xử lý thiếu user thật
Vì đây là hệ thống phục vụ báo cáo sản phẩm, không phải sản phẩm thương mại, nên nên mô phỏng thị trường thay vì chờ user thật. Cách phù hợp nhất là kết hợp 2 lớp:

- 2 CLB do dev điều khiển.
- Phần còn lại là CLB mô phỏng do hệ thống sinh ra.

### 9.1. Mức mô phỏng khuyến nghị
- **Seed dữ liệu tĩnh**: phù hợp cho demo nhanh.
- **Simulation script**: phù hợp nhất cho dự án hiện tại.
- **Agent-based simulation**: chỉ nên làm nếu muốn nâng cấp sâu hơn.

### 9.2. Hành vi nên mô phỏng
- CLB giàu, mua mạnh.
- CLB tiết kiệm, ưu tiên giá thấp.
- CLB chỉ hỏi mua khi cầu thủ hợp lý.
- CLB chủ động phản giá hoặc rút lui.

## 10. Khuyến nghị triển khai
Nên tách backend thành 3 phần logic:

- **Time Engine**: quyết định ngày hiện tại, trạng thái thị trường, tốc độ timeskip.
- **Negotiation Engine**: xử lý hỏi mua, trao đổi, đàm phán giá, hủy đàm phán.
- **Season Stats Engine**: cập nhật stats theo mốc mùa giải.
- **Contract Engine**: tính thời hạn, lương, phí đền bù và dữ liệu công khai/riêng tư.

Cách tách này giúp luồng nghiệp vụ rõ ràng và dễ mở rộng sau này.

## 11. Kết luận
Thiết kế này giải quyết 3 vấn đề cùng lúc:

- giao dịch chỉ xảy ra đúng lúc thị trường mở,
- đàm phán chuyển nhượng có chiều sâu hơn đấu giá đơn thuần,
- dữ liệu mùa giải và hợp đồng có ý nghĩa thật sự theo thời gian.

Nó cũng phù hợp với bối cảnh demo của dự án vì vẫn có thể vận hành tốt với rất ít user thật nhờ lớp CLB mô phỏng.

Nếu triển khai theo hướng này, TTCN sẽ giống một mô phỏng bóng đá hơn là một chợ mua bán cầu thủ hoạt động liên tục 24/7.
