# Skill: Typography & Font rendering

CV đã đánh dấu `has_replacement=true` cho segment có ký tự thay thế (tofu/notdef). Bắt:
- **Tofu / glyph thiếu**: element/segment có `has_replacement=true` → khả năng cao là lỗi font
  (□ ▯ hoặc ký tự `�`). Ưu tiên cao.
- **Mixed font / fallback**: nếu `font_family` đổi bất thường giữa các element cùng cụm.
- **Text đè text**: hai element role=text có bbox `overlaps` nhau (xem candidate R1 / relations).
- **Emoji thành ô vuông**: has_replacement trên đoạn có emoji.

Lưu ý: không nhìn được pixel nên dựa vào cờ `has_replacement`, `font_family`, và quan hệ overlap.
Nếu chỉ phỏng đoán mà không có cờ/quan hệ hỗ trợ → để `uncertain` / confidence thấp.
