# Skill: Text & Semantics (nội dung chữ)

Dựa trên `text` của các element (OCR). Bắt:
- **Biến chưa render** (→ `CNT-01`): `undefined`, `null`, `NaN`, `%s`, `%@`, `{{var}}`, `${x}`,
  và các biến thể nối chuỗi như `"nullnull"`, `"nullNull"`, `"undefinedundefined"`.
  Nếu text chứa chuỗi "null" lặp lại hoặc nối liền → chắc chắn là CNT-01.
- **i18n key lòi ra** (→ `CNT-02`): dot-notation (`home.title`, `btn_submit`) — không phải từ thật.
- **Chưa dịch / sai ngôn ngữ**: text khác ngôn ngữ với `locale` màn hình.
- **Placeholder/debug lọt ra**: `lorem ipsum`, `TODO`, `asdf`, `TEST`, `xxx`.
- **Mojibake**: ký tự lỗi mã hoá ("Ã©" thay vì "é").
- **HTML/escape lòi text**: `\n`, `<br>`, `&amp;` hiện như chữ.
- **Giá trị vô lý / mâu thuẫn logic**: "0 items" nhưng có item; giá thiếu đơn vị tiền; cùng một
  giá trị hiển thị khác nhau ở 2 chỗ.
- **Text bị cắt** (truncated) không có dấu "…" — suy từ `text_truncated` hoặc text cụt nghĩa.

KHÔNG xét: màu/contrast, hình học layout, chất lượng ảnh (đã có skill khác).
