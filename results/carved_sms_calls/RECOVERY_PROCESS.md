# Nhật ký khôi phục bản ghi WhatsApp — phần Linh

- Thời điểm chạy (UTC): `2026-11-09T11:39:02.366573+00:00`
- Thư mục chứng cứ: `C:\Documents\IT_documents\20261\Digital forensics\Project\for_linh`
- Chứng cứ gốc được mở chỉ đọc; phép đọc WAL-aware chỉ chạy trên bản sao tạm.

## 1. Nhiệm vụ được giao

Tìm lại các bản ghi WhatsApp đã bị xóa khỏi trạng thái hiện hành:

1. Tin nhắn `message._id=6` trong `msgstore.db`.
2. Cuộc gọi `call_log._id=2` trong `wa_calllog_dummy.db`.
3. Cuộc gọi nhỡ `call_log._id=4` từ dữ liệu SQLite còn sót trên trang B-tree.

Mục tiêu là ghi lại dữ liệu, nguồn và vị trí khôi phục để người khác có thể kiểm tra lại. Không khôi phục hay ghi ngược vào database gốc, không làm báo cáo LaTeX trong bước này.

## 2. Dump được giao: có gì và dùng để làm gì

Thư mục `for_linh/` chứa các file liên quan đến cả WhatsApp và nhật ký SMS/cuộc gọi Android. Phạm vi bài của Linh là dữ liệu WhatsApp; `mmssms.db` và `calllog.db` không được dùng cho ba bản ghi dưới đây.

| File | Nội dung / vai trò trong quá trình |
|---|---|
| `msgstore.db` | Database WhatsApp chính: bảng `message` có bản tin còn ở trang DB chính; dùng làm snapshot trước khi WAL áp dụng thao tác xóa. |
| `msgstore.db-wal` | Nhật ký ghi trước (Write-Ahead Log) đi kèm DB tin nhắn; chứa các trang thay đổi mới hơn, SQLite dùng để dựng trạng thái hiện hành. |
| `msgstore.db-shm` | File chia sẻ trạng thái/bộ nhớ phối hợp WAL; đi cùng DB khi mở bản sao WAL-aware. Không phải bản ghi tin nhắn độc lập. |
| `wa_calllog_dummy.db` | DB bảng `jid` và `call_log`; chứa bản ghi gọi hiện hành và dữ liệu trang còn sót của cuộc gọi đã xóa. Tên `dummy` cho biết đây là DB call-log minh họa trong bộ dump. |
| `wa_calllog_dummy.db-wal` | WAL của DB call-log; thể hiện trạng thái sau thao tác xóa `call_id=2`. |
| `wa_calllog_dummy.db-shm` | Trạng thái phối hợp WAL cho DB call-log; dùng cùng DB/WAL trên bản sao tạm. |
| `mmssms.db`, `calllog.db` | DB SMS/cuộc gọi hệ thống Android. Có mặt trong thư mục nhưng không được dùng vì nhiệm vụ này truy hồi message/call bên trong WhatsApp. |

Cặp `.db` + `-wal` quan trọng: chỉ mở `.db` đơn lẻ có thể cho thấy một trạng thái cũ; ứng dụng SQLite bình thường ghép các frame WAL hợp lệ để hiển thị trạng thái mới nhất. File `-shm` hỗ trợ phối hợp WAL và được giữ nguyên trong bản sao để SQLite đọc cặp này theo cách thông thường.

## 3. Phương pháp — giải thích trước khi xem kết quả

### 3.1 So sánh snapshot DB chính với snapshot đã áp WAL

- **Snapshot DB chính (`immutable=1`)**: mở file bằng SQLite ở chế độ chỉ đọc, đánh dấu immutable để SQLite không xử lý WAL bên cạnh. Điều này cho phép xem trạng thái đang nằm trong chính file `.db` mà không cập nhật nó.
- **Snapshot WAL-aware (`mode=ro`)**: sao chép `.db`, `.db-wal`, `.db-shm` vào thư mục tạm rồi mở bản sao chỉ đọc, không đặt immutable. SQLite ghép những thay đổi đã commit trong WAL vào kết quả truy vấn.
- Nếu một `_id` có trong snapshot DB chính nhưng không có trong snapshot WAL-aware, đó là bằng chứng bản ghi còn trong trạng thái nền nhưng đã bị xóa khỏi trạng thái logic mới hơn. Giá trị được lấy từ snapshot DB chính. Cách này không khẳng định WAL chứa nguyên văn nội dung đã xóa.

Mở WAL-aware trực tiếp trên file gốc là không phù hợp cho quy trình bảo toàn: SQLite có thể tạo/cập nhật file phối hợp hoặc checkpoint. Vì thế mọi phép đọc WAL-aware được thực hiện trên bản sao trong thư mục tạm; các bản sao tự dọn khi chương trình kết thúc.

#### Vì sao một bản ghi đã xóa vẫn còn trong `.db`?

WAL không phải bản sao đầy đủ của database. Nó là chuỗi các trang database đã được cập nhật. Khi ứng dụng xóa một hàng trong chế độ WAL, SQLite ghi phiên bản mới của trang có chứa hàng đó vào WAL. File `.db` chính có thể vẫn giữ nguyên phiên bản trang cũ cho đến khi checkpoint.

Có thể hình dung `.db` là cuốn sổ đã lưu lần trước, còn WAL là tờ đính chính mới hơn. Nếu chỉ đọc cuốn sổ cũ, ta có thể nhìn thấy hàng trước khi xóa. SQLite bình thường ghép tờ đính chính và trả về trạng thái mới hơn, trong đó hàng không còn. So sánh hai cách đọc cho thấy **hàng nào còn trong snapshot nền nhưng bị loại khỏi trạng thái hiện hành**. Nội dung được lấy từ snapshot nền, không nhất thiết phải “đào” nguyên văn nội dung hàng trong WAL.

Điều này cũng giải thích vì sao mở riêng `.db` bằng công cụ thông thường có thể gây hiểu nhầm: nhiều SQLite client tự động áp WAL và chỉ hiện trạng thái mới, khiến người phân tích tưởng hàng chưa từng có trong file chính. Tham số `immutable=1` được dùng có chủ đích để xem riêng snapshot nền; bản WAL-aware được mở riêng trên bản sao tạm để không đụng vào chứng cứ gốc.

#### WAL gồm những gì?

WAL có header chung rồi nhiều **frame**. Mỗi frame gồm metadata và một ảnh trang database có kích thước 4096 byte trong bộ chứng cứ này. Metadata cho biết trang số mấy được thay thế. Frame có dấu commit đánh dấu một nhóm cập nhật hoàn tất; các thay đổi chưa commit không được coi là trạng thái database hợp lệ. SQLite kiểm tra frame và áp các thay đổi hợp lệ theo đúng thứ tự, thay vì ghép bytes tùy tiện.

Trong kết quả này, root page của bảng `message` là trang 98; WAL tin nhắn có các frame ghi trang 98 ở frame 21, 60, 75 và 98. WAL call-log chỉ có một frame: frame 1 ghi trang 4, cũng là root page của `call_log`, và frame đó là commit. Đây là dấu vết phù hợp với việc trang chứa các hàng đã được cập nhật. Việc kết luận một `_id` bị xóa vẫn dựa vào truy vấn đối chiếu qua SQLite trên hai snapshot, không chỉ dựa vào số frame.

### 3.2 Carving record từ trang B-tree SQLite

SQLite chia DB thành các trang. Bảng dạng rowid thường có các trang lá B-tree; mỗi cell trên trang có thể mô tả một hàng bằng payload size, rowid, header và các giá trị cột. Header dùng SQLite varint và serial type để cho biết kiểu/độ dài từng giá trị. Carver đọc các cấu trúc này từ bytes, rồi kiểm tra hàng giải mã có đúng schema, `_id` và chuỗi nhận dạng mong đợi không.

- **Freeblock** là đoạn trống được liên kết rõ ràng bằng con trỏ trong header trang sau khi xóa cell.
- **Unallocated page space** là vùng chứa bytes chưa được cấu trúc trang hiện tại đánh dấu là cell đang sử dụng; dấu vết cũ đôi khi vẫn còn ở đó.
- Hai khái niệm không đồng nghĩa. Chỉ gọi là phục hồi từ freeblock nếu header trang thật sự dẫn tới freeblock chứa cell.

Trong dump này, `call_id=4` được giải mã ở vùng unallocated của trang lá, còn freeblock head bằng 0. Vì vậy kết quả được mô tả chính xác là B-tree page carving, dù nhãn record mẫu có chữ `FREEBLOCK`.

#### Vì sao bytes trong vùng trống có thể trở thành một hàng?

Khi SQLite xóa một cell, nó cập nhật cấu trúc trang để cell đó không còn là hàng đang hoạt động. Tùy vị trí/kích thước cell và thao tác khác về sau, bytes cũ có thể bị ghi đè, được nối vào freeblock, hoặc còn nguyên trong vùng trang không còn được dùng. Việc “xóa hàng” vì vậy không đồng nghĩa với việc mọi bytes của hàng lập tức bị xóa sạch.

Carving tìm dấu vết ở mức bytes, nhưng chỉ tìm chuỗi nhận diện là chưa đủ: chuỗi đó có thể xuất hiện ngẫu nhiên hoặc trong hàng khác. Để chấp nhận kết quả ở đây, các bytes xung quanh phải đồng thời:

1. Nằm trong đúng trang lá của bảng `call_log`.
2. Đọc được theo định dạng cell của SQLite: kích thước payload, rowid, header và đủ 21 serial type cho schema bảng.
3. Có rowid `4` và giá trị cột `call_id` đúng `WA_CALL_DEL_FREEBLOCK_04`.
4. Có các kiểu/độ dài dữ liệu hợp lệ; các trường số, text và NULL được giải mã đúng ranh giới payload.
5. Phù hợp với quan hệ bảng `jid`: `jid_row_id=3` nối tới `84909888777@s.whatsapp.net`.

Các kiểm tra chéo này làm cho việc chấp nhận record đáng tin hơn việc chỉ grep một chuỗi. Tuy nhiên, carving vẫn là phục hồi từ dấu vết còn lại: nó không tự chứng minh danh tính người dùng, ngữ cảnh đầy đủ, hay thời điểm xóa nếu dữ liệu nguồn không cung cấp điều đó.

## 4. Quy trình đã thực hiện

1. Tính SHA-256 cho file dump hiện có và đối chiếu với manifest thu thập ban đầu.
2. Đọc header thô để kiểm tra SQLite/WAL và page size; hai DB có page size 4096 byte, hai WAL có page size tương ứng 4096 byte.
3. Mở `msgstore.db` và `wa_calllog_dummy.db` bằng immutable read-only; lấy `message._id=6` và `call_log._id=2` từ trạng thái DB chính.
4. Tạo bản sao tạm gồm từng `.db`, `-wal`, `-shm`; mở bản sao theo WAL-aware read-only và xác nhận hai `_id` đó không còn trong trạng thái đã áp WAL.
5. Phân tích root page của bảng `call_log`, tìm chuỗi nhận diện của `call_id=4`, thử giải mã cấu trúc cell theo schema 21 cột, rồi xác nhận rowid và toàn bộ payload hợp lệ.
6. Tính lại hash chứng cứ sau khi phân tích và so với hash trước khi chạy để xác nhận file gốc không bị thay đổi.
7. Xuất dữ liệu cùng phương pháp, vị trí byte và cảnh báo hash vào JSON và file Markdown này.

Mấu chốt của quy trình không phải là “SQLite tự undelete dữ liệu”, mà là sử dụng hai trạng thái khác nhau của chứng cứ: file DB nền vẫn giữ một số bytes cũ; WAL mô tả trạng thái mới hơn sau thao tác xóa. Với cuộc gọi số 4, trạng thái bảng không còn trỏ tới cell, nhưng payload của cell vẫn chưa bị ghi đè nên có thể giải mã trực tiếp.

## 5. Đối chiếu WAL và kết quả

| Bản ghi | Chỉ đọc DB chính | Đọc bản sao có WAL | Kết luận |
|---|---:|---:|---|
| `msgstore.db` / `message._id=6` | có; hàng đầy đủ và text còn đọc được | không | Hàng còn trong trang DB nền, nhưng trạng thái có WAL không còn hàng `_id=6`; lấy giá trị từ snapshot nền và xác nhận xóa bằng phép so sánh. |
| `wa_calllog_dummy.db` / `call_log._id=2` | có; hàng đầy đủ còn đọc được | không | Cùng cách: lấy hàng từ file DB nền, còn snapshot WAL-aware xác nhận call `_id=2` đã bị xóa khỏi trạng thái hiện hành. |

WAL được phân tích theo header và frame. Một frame mang số trang DB; commit frame cho biết điểm kết thúc một nhóm thay đổi hoàn chỉnh. SQLite cũng đọc thành công các bản sao WAL-aware.

| WAL | Kích thước | Page size | Số frame | Root page bảng / frame cập nhật |
|---|---:|---:|---:|---|
| `msgstore.db-wal` | 465592 B | 4096 B | 113 | 98 / 21, 60, 75, 98 |
| `wa_calllog_dummy.db-wal` | 4152 B | 4096 B | 1 | 4 / 1 |

WAL `msgstore.db-wal` có 13 commit frame; `wa_calllog_dummy.db-wal` có 1 commit frame. Root page là trang bắt đầu của bảng trong B-tree; số frame liệt kê là các frame chạm root page, không phải toàn bộ frame WAL.

## 6. Chi tiết từng bản ghi khôi phục

### Tin nhắn `_id=6`

**Cách đọc kết quả:** `text_data` là nội dung tin nhắn. `_id=6` là khóa hàng; `chat_row_id=2` chỉ tới cuộc hội thoại trong database; `from_me=1` cho biết record được đánh dấu là tin nhắn gửi từ tài khoản trên thiết bị. `timestamp` là thời gian Unix epoch tính bằng mili giây. Các mã trạng thái/loại khác được giữ nguyên theo giá trị database, không tự gán nghĩa nghiệp vụ nếu chưa có tài liệu schema tương ứng.

```json
{
  "_id": 6,
  "chat_row_id": 2,
  "from_me": 1,
  "key_id": "ACDBDBF6A66CAD14468E248005ECA3CB",
  "sender_jid_row_id": 0,
  "status": 13,
  "broadcast": 0,
  "recipient_count": 0,
  "participant_hash": null,
  "origination_flags": 0,
  "origin": 0,
  "timestamp": 1794214023112,
  "received_timestamp": 0,
  "receipt_server_timestamp": -1,
  "message_type": 0,
  "text_data": "Delete this temporary access code: 849201",
  "starred": 0,
  "lookup_tables": 0,
  "message_add_on_flags": 0,
  "view_mode": 0,
  "sort_id": 6,
  "translated_text": null,
  "view_replies_thread_id": null,
  "server_sts": null
}
```

### Cuộc gọi `_id=2`

**Cách đọc kết quả:** `from_me=0` cho biết cuộc gọi đến theo cờ lưu trong hàng; `jid_row_id=2` liên kết tới người liên hệ trong bảng `jid`. `timestamp` là epoch mili giây, `duration=142` là giá trị duration được lưu, còn `video_call=0` đánh dấu cuộc gọi thoại. `call_result=5` là mã enum của ứng dụng; báo cáo giữ mã thô vì chưa xác minh bảng diễn giải mã này.

```json
{
  "_id": 2,
  "jid_row_id": 2,
  "from_me": 0,
  "call_id": "WA_CALL_DEL_WAL_02",
  "transaction_id": 102,
  "timestamp": 1794213800000,
  "video_call": 0,
  "duration": 142,
  "call_result": 5,
  "is_dnd_mode_on": 0,
  "bytes_transferred": 894120,
  "group_jid_row_id": 0,
  "is_joinable_group_call": 0,
  "call_creator_device_jid_row_id": 0,
  "call_random_id": "rnd02",
  "call_link_row_id": 0,
  "call_type": 0,
  "offer_silence_reason": 0,
  "scheduled_id": null,
  "telecom_uuid": "uuid-wa-02",
  "terminated_by_device_switch": 0
}
```

### Carving cuộc gọi nhỡ `_id=4`

- Bảng: `call_log`; root page: 4; loại trang: `0x0d` (table leaf).
- Cell bắt đầu tại offset 3811 trong trang (offset 16099 trong file); payload 72 byte.
- Chuỗi nhận diện `WA_CALL_DEL_FREEBLOCK_04` tại offset 3836 trong trang.
- Freeblock head = 0; số freeblock liên kết = 0.
- Phân loại vị trí cell: **`unallocated_page_space`**.

Lưu ý về thuật ngữ: header trang hiện tại không có freeblock nào được liên kết (freeblock head bằng 0). Cell được giải mã nằm trong vùng chưa cấp phát giữa mảng cell pointer và cell content đang hoạt động, không nằm trong một freeblock được liên kết. Vì vậy kết quả được ghi là carving vùng chưa cấp phát của trang B-tree, không khẳng định có freeblock chain.

Record được giải mã theo định dạng cell của SQLite table-leaf: payload size, rowid, record header, serial types và các giá trị. `_id` INTEGER PRIMARY KEY được khôi phục từ rowid; `peer_jid` được nối từ bảng `jid`.

**Cách xác định vị trí:** SQLite dùng page size 4096 byte. Trang số 4 bắt đầu tại offset `(4 - 1) × 4096 = 12288` trong file. Cell bắt đầu tại offset 3811 bên trong trang, nên offset tuyệt đối là `12288 + 3811 = 16099`. Header trang ghi nhận 3 cell đang hoạt động, với cell pointer ở các offset 4027, 3956 và 3885; mảng con trỏ kết thúc tại offset 14, còn nội dung cell đang hoạt động bắt đầu tại offset 3885. Cell nghi vấn bắt đầu ở 3811 — sau mảng con trỏ nhưng trước ranh giới nội dung đang hoạt động — nên bytes nằm trong vùng chưa cấp phát theo cấu trúc trang hiện tại và không được pointer array liệt kê như một hàng đang hoạt động.

Header trang có `freeblock head = 0`, nghĩa là không có freeblock nào được liên kết để lần theo. Do đó không thể gọi đây là “cell nằm trong freeblock”. Bản ghi còn sót vì bytes payload chưa bị ghi đè, dù cell pointer của nó đã không còn trong danh sách cell đang hoạt động. Cách phân loại chính xác là carving từ unallocated page space.

**Cách giải mã bytes:** Cell bắt đầu bằng varint payload size `72` (`0x48`), tiếp theo varint rowid `4` (`0x04`). Record header bắt đầu bằng kích thước header `22` byte (`0x16`), gồm 1 byte kích thước header và 21 serial type — một type cho mỗi cột trong schema `call_log`. Còn lại 50 byte trong payload là dữ liệu cột. Serial type mô tả kiểu và số byte của từng giá trị: số nguyên, text hoặc NULL. Carver tuần tự đọc đúng độ dài để không nhầm ranh giới các cột; tổng phần header và dữ liệu phải khớp payload size 72. Tính cả hai varint mở đầu, cell chiếm 74 byte. Vì `_id` được khai báo `INTEGER PRIMARY KEY`, giá trị khóa là rowid `4`. Sau đó kết quả được kiểm tra thêm theo chuỗi `call_id` tại offset 3836 và nối `jid_row_id=3` qua bảng `jid`.

Tóm lại, call `_id=4` không được lấy từ một truy vấn `SELECT` bình thường vì SQLite không còn coi nó là hàng hoạt động. Nó được khôi phục vì nội dung cell cũ vẫn còn ở trang 4 và bytes đó vượt qua kiểm tra cấu trúc/schema/rowid/chuỗi nhận diện.

**Cách đọc kết quả:** `from_me=0` là cờ cuộc gọi đến; `duration=0` và `call_result=2` giữ nguyên giá trị lưu trong dump (không tự diễn giải mã kết quả); `video_call=0` đánh dấu thoại; `peer_jid` được nối từ bảng `jid`. Dùng các trường này như dữ liệu đã giải mã, không suy luận thêm ngoài schema đã biết.

```json
{
  "artifact": "deleted_whatsapp_missed_call",
  "record_id": 4,
  "recovery_method": "sqlite_table_leaf_record_carving",
  "source_file": "wa_calllog_dummy.db",
  "source_sha256": "ad591a6c4b3e247c0e6a5cf2d5fefc2318bb860b993a07b67d0444c532fe8b05",
  "evidence_location": {
    "page_number": 4,
    "cell_offset_in_page": 3811,
    "cell_offset_in_file": 16099,
    "cell_region": "unallocated_page_space"
  },
  "record": {
    "_id": 4,
    "jid_row_id": 3,
    "from_me": 0,
    "call_id": "WA_CALL_DEL_FREEBLOCK_04",
    "transaction_id": 104,
    "timestamp": 1794214150000,
    "video_call": 0,
    "duration": 0,
    "call_result": 2,
    "is_dnd_mode_on": 0,
    "bytes_transferred": 12400,
    "group_jid_row_id": 0,
    "is_joinable_group_call": 0,
    "call_creator_device_jid_row_id": 0,
    "call_random_id": "rnd04",
    "call_link_row_id": 0,
    "call_type": 0,
    "offer_silence_reason": 0,
    "scheduled_id": null,
    "telecom_uuid": "uuid-wa-04",
    "terminated_by_device_switch": 0,
    "peer_jid": "84909888777@s.whatsapp.net"
  }
}
```

## 7. Hash, giới hạn và file đầu ra

| File | SHA-256 lúc thu thập (manifest gốc) | SHA-256 hiện tại | Revalidation bổ sung | Trạng thái so với lần thu thập |
|---|---|---|---|---|
| `msgstore.db` | `85bd6b0411fb74753899f45e71976f2a34618ea0032bf4fb042ab4ed49672b57` | `85bd6b0411fb74753899f45e71976f2a34618ea0032bf4fb042ab4ed49672b57` | `chưa có` (—) | **MATCH** |
| `msgstore.db-wal` | `e77a9f0b21847170bd4836bf099df381f0e7e1210a0bcaddcc5bbb47afc94589` | `e77a9f0b21847170bd4836bf099df381f0e7e1210a0bcaddcc5bbb47afc94589` | `chưa có` (—) | **MATCH** |
| `wa_calllog_dummy.db` | `ad591a6c4b3e247c0e6a5cf2d5fefc2318bb860b993a07b67d0444c532fe8b05` | `ad591a6c4b3e247c0e6a5cf2d5fefc2318bb860b993a07b67d0444c532fe8b05` | `chưa có` (—) | **MATCH** |
| `wa_calllog_dummy.db-wal` | `ad8a38eff610717d43ec910beaee98749efd9d71071dec286b76992b5832860a` | `eec6e9816f7d8f00a94a995fbbcece280f3701cffa31fa1e457eb24cde11e287` | `eec6e9816f7d8f00a94a995fbbcece280f3701cffa31fa1e457eb24cde11e287` (MATCH) | **MISMATCH** |

Hash SHA-256 là dấu vân tay của từng file: cùng bytes cho cùng hash; đổi dù một byte thường tạo hash khác. Bản ghi thu thập ban đầu được giữ nguyên. Với `wa_calllog_dummy.db-wal`, hash gốc trong manifest là `ad8a38eff610717d43ec910beaee98749efd9d71071dec286b76992b5832860a`, còn file hiện tại là `eec6e9816f7d8f00a94a995fbbcece280f3701cffa31fa1e457eb24cde11e287`. Một dòng revalidation mới được thêm vào `results/hash_table.csv`; dòng đó ghi hash hiện tại mà không ghi đè lịch sử thu thập. Sai khác giữa hash lúc thu thập và hiện tại vẫn cần xác minh nguồn gốc; revalidation chỉ xác nhận giá trị hash của file tại thời điểm kiểm tra.

Các file gốc không bị sửa. Kết quả là bản phân tích trên dump hiện có; sai khác hash làm giảm khả năng khẳng định WAL hiện tại giống hệt WAL tại thời điểm thu thập, nên cần nêu hạn chế này khi sử dụng kết quả.

- `recovered_records.json`: metadata, hash, so sánh WAL và ba bản ghi.
- `RECOVERY_PROCESS.md`: nhiệm vụ, mô tả dump, giải thích phương pháp, quy trình và kết quả chi tiết.
