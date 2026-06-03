# Skill: UI Components & App states

Dựa trên `role`, `interactive`, `touch_target`, `text`, candidate. Bắt:
- **Component**: touch target nhỏ; nút icon-only thiếu nhãn; nút/label bị cắt; thiếu component
  kỳ vọng (form không có nút submit); input thiếu label; tab/segment active không phân biệt;
  component trùng lặp.
- **App state**: skeleton/spinner đang hiện (đánh `temporal=true` — 1 frame không khẳng định "kẹt");
  empty state thiếu thông báo; lỗi thô lọt ra (stack trace, error code); render dở dang.
- **Môi trường nền tảng**: nội dung dưới notch/Dynamic Island/status bar; nút chạm home indicator;
  splash kẹt.

Với trạng thái "kẹt" (loading/skeleton/spinner): luôn `temporal=true` vì chỉ có 1 khung hình.
Platform & safe_area lấy từ `screen`.
