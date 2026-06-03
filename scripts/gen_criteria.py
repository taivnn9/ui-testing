#!/usr/bin/env python3
"""
Sinh tài liệu tiêu chí: 1 file tổng hợp (docs/tieu-chi/README.md) + 1 file/tiêu chí
(docs/tieu-chi/<ID>.md). NGUỒN SỰ THẬT = biến DATA trong file này — sửa ở đây rồi chạy lại:

    python scripts/gen_criteria.py

Nội dung rút từ catalog-tieu-chi-loi-ui.md (tên, severity, tags) + F0.4-thresholds.md (ngưỡng)
+ kiến trúc Codex (F1.1). Mỗi tiêu chí: dữ liệu dùng · kỹ thuật & ai đánh giá · đạt/không đạt.
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "tieu-chi"

GROUPS = {
    "CNT": "Content & Semantics — nội dung text nói gì",
    "TYP": "Typography & Text Rendering — text trông thế nào",
    "STY": "Color, Contrast & Visual Style — màu, tương phản, style",
    "LAY": "Layout & Spatial Geometry — bố cục, hình học",
    "IMG": "Images, Icons & Media — ảnh, icon, media",
    "CMP": "UI Components & Controls — thành phần điều khiển",
    "STATE": "State & Lifecycle — trạng thái màn",
    "ENV": "Platform & Environment — nền tảng, môi trường",
    "CONS": "Consistency xuyên màn — cần nhiều ảnh",
}

# who: rule | agent | both | phase2   → nhãn + cách đánh giá
WHO = {
    "rule":   "🟦 Rule tất định (code tính từ số/box/pixel)",
    "agent":  "🟥 Agent Codex (phán đoán text-only)",
    "both":   "🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác",
    "phase2": "⏳ Chưa triển khai (Phase 2 / cần nhiều ảnh hoặc tương tác)",
}
STATUS = {
    "rule":   "✅ Có rule tất định",
    "agent":  "🟥 Agent đánh giá (chưa có rule)",
    "both":   "✅ Rule + agent xác nhận",
    "phase2": "⏳ Phase 2 — chưa triển khai",
}

# Mỗi tiêu chí: (id, name, sev, range, tags, data, who, tech, fail, pass_, status)
# pass_ = "" → mặc định "Không có dấu hiệu ở mục 'Không đạt'."
def C(id, name, sev, rng, tags, data, who, tech, fail, pass_="", status=None):
    return dict(id=id, name=name, sev=sev, rng=rng, tags=tags, data=data,
                who=who, tech=tech, fail=fail, pass_=pass_, status=status or who)


DATA = [
    # ── A. CNT ────────────────────────────────────────────────────────────────
    C("CNT-01", "Placeholder/biến chưa render", "high", "medium→critical", "",
      "`element.text` (A5 OCR)", "rule", "R4 regex (`rules/patterns.py`)",
      "text khớp mẫu `undefined|null|NaN|%s|%@|{{...}}|${...}`",
      "text không khớp mẫu biến chưa render"),
    C("CNT-02", "i18n key lòi ra chưa dịch", "high", "medium→critical", "i18n",
      "`element.text`", "rule", "R4 regex",
      "text là key dot-notation (`home.title`, `btn_submit`) không phải từ thật",
      "text là câu/từ tự nhiên"),
    C("CNT-03", "Sai/lẫn ngôn ngữ", "medium", "low→high", "i18n",
      "`element.text`, `screen.locale`", "agent", "",
      "ngôn ngữ của text ≠ `locale` màn hình", "text đúng ngôn ngữ locale"),
    C("CNT-04", "Lorem ipsum / placeholder copy", "high", "medium→high", "",
      "`element.text`", "both", "R4 regex + agent",
      "chứa 'lorem ipsum' / 'your text here' …", "nội dung thật"),
    C("CNT-05", "Text debug/nội bộ lòi", "high", "medium→critical", "",
      "`element.text`", "both", "R4 regex + agent",
      "chứa `TODO|asdf|TEST|DO NOT SHIP` …", "không có text debug"),
    C("CNT-06", "Mojibake / entity thô", "medium", "low→high", "i18n",
      "`element.text`", "rule", "R4 regex",
      "chứa `Ã©|â€™|&amp;|&#39;` …", "text mã hoá đúng"),
    C("CNT-07", "Ký tự escape lòi như text", "medium", "low→high", "",
      "`element.text`", "rule", "R4 regex",
      "chứa literal `\\n` `\\t` `<br>` hiển thị như chữ", "không có escape lòi"),
    C("CNT-08", "Số/ngày/tiền sai định dạng locale", "medium", "low→high", "i18n",
      "`element.text`, `locale`", "agent", "",
      "epoch thô / `1234567.89` không format theo locale", "đúng định dạng locale"),
    C("CNT-09", "Lỗi chính tả / ngữ pháp", "low", "trivial→medium", "ctx",
      "`element.text`", "agent", "",
      "sai chính tả/ngữ pháp rõ ràng", "không phát hiện lỗi chính tả"),
    C("CNT-10", "Nội dung sai ngữ cảnh / nhầm dữ liệu user", "high", "medium→critical", "ctx,multi",
      "`element.text` + ngữ cảnh màn", "agent", "(confidence thấp — cần intent)",
      "nội dung vô lý so với màn/intent", "nội dung hợp lý"),
    C("CNT-11", "Text trùng lặp / mâu thuẫn", "medium", "low→high", "ctx",
      "toàn bộ `text` các element", "agent", "",
      "cùng giá trị hiển thị khác nhau ở 2 chỗ", "nhất quán"),
    C("CNT-12", "Đơn vị/ký hiệu sai hoặc thiếu", "medium", "low→high", "i18n",
      "`element.text`", "agent", "",
      "thiếu ký hiệu tiền tệ / sai đơn vị", "đủ & đúng đơn vị"),
    C("CNT-13", "Giá trị vô lý", "medium", "low→high", "ctx",
      "`element.text` + list quanh", "agent", "",
      "'0 sản phẩm' nhưng list có item; số âm sai chỗ", "giá trị hợp lý"),
    C("CNT-14", "Văn bản pháp lý/cảnh báo thiếu/sai", "high", "medium→critical", "ctx",
      "`element.text`", "agent", "(confidence thấp)",
      "thiếu/sai disclaimer kỳ vọng", "đủ & đúng"),

    # ── B. TYP ────────────────────────────────────────────────────────────────
    C("TYP-01", "Tofu / glyph thiếu", "high", "medium→critical", "i18n",
      "`has_replacement` (A5/A8)", "both", "A8 cờ → agent xác nhận",
      "segment có `has_replacement=true` (□ ▯ `�`)", "không có ký tự thay thế"),
    C("TYP-02", "Font chưa load / fallback sai", "medium", "low→medium", "",
      "`style.font_family`", "agent", "(yếu)",
      "font_family đổi bất thường / mất font brand", "font nhất quán"),
    C("TYP-03", "Chữ tràn/cắt cụt khỏi container", "medium", "trivial→critical", "i18n,ctx",
      "`text_truncated`, bbox vs parent", "both", "R4 + agent",
      "`text_truncated=true` không có '…' hoặc text cụt nghĩa", "đủ chữ / ellipsis chủ ý"),
    C("TYP-04", "Chữ đè lên chữ / phần tử khác", "high", "medium→critical", "",
      "`relations` (overlaps text-text)", "rule", "R1 overlap",
      "2 element text `overlaps`, iou > OVERLAP_IOU_MIN (0.05)", "không chồng"),
    C("TYP-05", "Cỡ chữ quá nhỏ", "medium", "low→high", "a11y",
      "`style.font_size`, `font_scale`", "rule", "ngưỡng F0.4 §4",
      "font_size < FONT_MIN_PX (11px device)", "≥ 14px"),
    C("TYP-06", "Ngắt dòng xấu", "low", "trivial→medium", "",
      "`text`, bbox dòng", "agent", "(yếu)",
      "gãy giữa từ / 1 từ mồ côi / hyphenation lỗi", "ngắt dòng ổn"),
    C("TYP-07", "Line-height sai", "low", "trivial→medium", "",
      "bbox các dòng", "phase2", "",
      "dòng dính nhau / cách quá xa", "line-height hợp lý"),
    C("TYP-08", "Letter/word-spacing vỡ", "low", "trivial→medium", "",
      "crop/pixel", "phase2", "",
      "kerning lỗi / giãn chữ bất thường", "spacing ổn"),
    C("TYP-09", "Chữ mờ / vỡ / răng cưa", "medium", "low→medium", "resp",
      "A8 Laplacian variance (F0.4 §5.3)", "rule", "A8",
      "Laplacian var < BLUR_WARN (50) trên crop text", "> 100 (rõ)"),
    C("TYP-10", "Căn lề text sai", "low", "trivial→medium", "",
      "bbox text trong container", "agent", "",
      "center nơi đáng left / justify tạo khe trắng", "căn lề hợp lý"),
    C("TYP-11", "Casing/transform sai", "low", "trivial→medium", "",
      "`element.text`", "agent", "",
      "ALL CAPS sai chỗ (body text)", "casing hợp lý"),
    C("TYP-12", "RTL/bidi hỏng", "high", "medium→critical", "i18n",
      "`script` (A5), `text`, bbox", "agent", "",
      "Ả Rập/Do Thái chạy sai chiều, dấu câu lệch", "đúng chiều RTL"),
    C("TYP-13", "Trộn nhiều font không chủ ý", "low", "trivial→medium", "multi",
      "`style.font_family` trong cụm", "agent", "",
      "font đổi bất thường trong 1 cụm text", "đồng nhất"),
    C("TYP-14", "Emoji/icon-font render sai", "low", "trivial→medium", "i18n",
      "`has_replacement`", "both", "A8 + agent",
      "emoji thành box / mất màu (has_replacement)", "emoji render đúng"),

    # ── C. STY ────────────────────────────────────────────────────────────────
    C("STY-01", "Contrast chữ/nền < WCAG", "high", "medium→high", "a11y",
      "`style.contrast_ratio` (A4)", "rule", "R2 (F0.4 §3)",
      "< 4.5 (text thường) hoặc < 3.0 (text lớn)", "≥ ngưỡng WCAG"),
    C("STY-02", "Chữ tàng hình (cùng màu nền)", "critical", "high→critical", "a11y,dark",
      "`contrast_ratio`", "rule", "R2",
      "< CONTRAST_INVISIBLE (1.5)", "contrast đủ thấy"),
    C("STY-03", "Dark-mode không đổi màu", "high", "medium→critical", "dark",
      "`color`, `screen.theme`", "both", "R2 + agent",
      "theme=dark mà element màu sáng / không adapt", "màu adapt theme"),
    C("STY-04", "Icon/viền tàng hình trong theme", "high", "medium→critical", "dark,a11y",
      "`contrast_ratio` icon", "rule", "R2",
      "icon contrast < 3.0 trong theme", "≥ 3.0"),
    C("STY-05", "Opacity sai", "medium", "low→high", "",
      "`style.opacity`", "agent", "",
      "element mờ/trong suốt ngoài ý muốn", "opacity đúng ý"),
    C("STY-06", "Lệch bảng màu / sai màu brand", "low", "trivial→medium", "multi",
      "`color`", "phase2", "(cần ref brand)",
      "màu lệch palette brand", "đúng palette"),
    C("STY-07", "Disabled không phân biệt enabled", "medium", "low→high", "a11y",
      "style states", "agent", "",
      "disabled & enabled nhìn giống nhau", "phân biệt rõ"),
    C("STY-08", "Focus/selected không nhìn thấy", "medium", "low→high", "a11y",
      "style states", "agent", "",
      "trạng thái focus/selected không nổi bật", "rõ ràng"),
    C("STY-09", "Thông tin chỉ truyền bằng màu", "medium", "low→medium", "a11y",
      "`color`, có icon/label?", "agent", "",
      "lỗi/cảnh báo chỉ đổi màu, không icon/label", "có dấu hiệu phụ"),
    C("STY-10", "Gradient/shadow/blur lỗi render", "low", "trivial→medium", "",
      "pixel/crop", "phase2", "",
      "banding / viền cứng / bóng lệch", "render mượt"),
    C("STY-11", "Viền/divider thiếu/thừa/đôi", "low", "trivial→medium", "",
      "bbox, A6", "agent", "",
      "divider nhân đôi / thiếu", "đúng số divider"),
    C("STY-12", "Màu nền sai vùng", "medium", "low→high", "",
      "`bg_color`, `bg_is_solid_px`", "agent", "",
      "vùng đáng trong suốt lại nền đặc", "nền đúng"),
    C("STY-13", "Contrast icon/đồ hoạ chức năng < 3:1", "medium", "low→high", "a11y",
      "`contrast_ratio` icon", "rule", "R2",
      "< 3.0", "≥ 3.0"),

    # ── D. LAY ────────────────────────────────────────────────────────────────
    C("LAY-01", "Overlap / va chạm phần tử vô lý", "high", "medium→critical", "",
      "`relations` iou", "both", "R1 + agent",
      "iou > OVERLAP_IOU_MIN (0.05) không chủ ý", "không chồng / chủ ý"),
    C("LAY-02", "Off-screen / cắt mép viewport", "high", "medium→critical", "resp",
      "bbox vs `viewport`", "rule", "R1 (F0.4 §8)",
      "bbox nằm ngoài viewport bất kỳ phía", "nằm trong viewport"),
    C("LAY-03", "Tràn ra ngoài container cha", "medium", "low→high", "i18n",
      "bbox child vs parent", "both", "R1 (OVERFLOW 4px) + agent",
      "child vượt parent > 4px", "trong parent"),
    C("LAY-04", "Lệch grid (không theo 8pt)", "low", "trivial→medium", "",
      "bbox", "rule", "R1 (GRID_TOLERANCE 2px)",
      "abs(pos mod 8) > 2px", "đúng grid 8pt"),
    C("LAY-05", "Lệch optical alignment", "low", "trivial→medium", "",
      "bbox cạnh", "both", "R1 (confidence thấp) + agent",
      "mép giữa các phần tử lệch nhẹ", "thẳng hàng"),
    C("LAY-06", "Z-order / occlusion", "high", "medium→critical", "",
      "overlap + `z`", "both", "R1 + agent",
      "nội dung quan trọng bị che sau phần tử khác", "không bị che"),
    C("LAY-07", "Quá chật / quá nhiều khoảng trắng", "low", "trivial→medium", "",
      "`relations.gap`", "agent", "",
      "gap bất thường lớn/nhỏ", "spacing đều"),
    C("LAY-08", "Lệch tâm / căn giữa sai", "low", "trivial→medium", "",
      "bbox trong container", "agent", "",
      "lệch tâm rõ", "căn giữa đúng"),
    C("LAY-09", "Reflow/wrap vỡ (responsive)", "high", "medium→critical", "resp,web",
      "bbox, wrap (cần multi-viewport)", "phase2", "",
      "cột sập / rớt dòng xấu khi đổi kích thước", "responsive ổn"),
    C("LAY-10", "Scroll lỗi", "high", "medium→critical", "resp",
      "bbox vs viewport", "phase2", "",
      "scroll ngang ngoài ý / double scrollbar", "scroll đúng"),
    C("LAY-11", "Sticky/fixed đè nội dung", "medium", "low→high", "",
      "bbox header/footer", "both", "R1 + agent",
      "fixed header/footer che nội dung", "không che"),
    C("LAY-12", "Tỉ lệ / kích thước container sai", "medium", "low→high", "",
      "bbox kích thước", "agent", "",
      "1 khối phình/teo bất thường", "tỉ lệ hợp lý"),
    C("LAY-13", "Vùng trống bất thường", "low", "trivial→medium", "ctx",
      "bbox, gap", "agent", "",
      "khoảng trống lớn giữa màn", "bố cục đầy đủ"),
    C("LAY-14", "Phần tử chồng vị trí (cùng toạ độ)", "medium", "low→high", "",
      "bbox", "rule", "R1",
      "2 element gần trùng toạ độ", "vị trí riêng biệt"),
    C("LAY-15", "Thứ tự sắp xếp sai", "medium", "low→high", "ctx",
      "thứ tự bbox + nội dung", "agent", "",
      "list lộn xộn / thứ tự đảo", "đúng thứ tự"),

    # ── E. IMG ────────────────────────────────────────────────────────────────
    C("IMG-01", "Ảnh vỡ / broken", "high", "medium→critical", "",
      "A9 blank/broken, A7", "both", "R3 + agent",
      "vùng đơn sắc bất thường / icon ảnh vỡ", "ảnh hiển thị bình thường"),
    C("IMG-02", "Méo / sai tỉ lệ", "medium", "low→high", "",
      "`image_meta` (A7)", "rule", "R3 (F0.4 §5.1)",
      "lệch ratio > 5% (warn) / > 15% (error)", "trong ngưỡng"),
    C("IMG-03", "Mờ / pixel hoá", "medium", "low→medium", "resp",
      "A8 Laplacian + A7 upscale", "rule", "R3/A8",
      "upscale (>1.5×) + blur dưới ngưỡng", "nét"),
    C("IMG-04", "Crop sai (cắt mất phần quan trọng)", "medium", "low→high", "ctx",
      "crop nội dung ảnh", "phase2", "(cần nhìn nội dung)",
      "cắt mất mặt người / chữ trên ảnh", "crop hợp lý"),
    C("IMG-05", "Thiếu ảnh (slot trống)", "medium", "low→high", "",
      "A9, role=image rỗng", "both", "R3 + agent",
      "slot ảnh trống nơi đáng có ảnh", "có ảnh"),
    C("IMG-06", "Icon sai ngữ nghĩa", "medium", "low→high", "ctx",
      "`role=icon`, ngữ cảnh", "agent", "(confidence < 0.5)",
      "icon không khớp chức năng", "icon đúng nghĩa"),
    C("IMG-07", "Icon lệch tâm trong nút", "low", "trivial→medium", "",
      "bbox icon vs nút", "both", "R1 + agent",
      "icon lệch tâm / lệch baseline với label", "căn đều"),
    C("IMG-08", "Icon placeholder / chưa load", "medium", "low→high", "",
      "A6 cờ, A9", "rule", "R3",
      "ô xám / dấu ? thay cho icon", "icon thật"),
    C("IMG-09", "Scale-mode sai", "medium", "low→high", "",
      "`image_meta.scale_mode`", "rule", "R3",
      "cover↔contain gây méo/cắt", "đúng scale mode"),
    C("IMG-10", "Sai phiên bản / lộn brand", "medium", "low→high", "ctx,multi",
      "nội dung ảnh", "phase2", "(cần nhìn nội dung)",
      "logo/ảnh sai brand", "đúng brand"),
    C("IMG-11", "Logo mờ/sai màu/tỉ lệ", "low", "trivial→medium", "",
      "image_meta + pixel", "phase2", "(cần nhìn)",
      "logo mờ / sai màu / sai tỉ lệ", "logo chuẩn"),
    C("IMG-12", "Ảnh trùng lặp ngoài ý muốn", "low", "trivial→medium", "",
      "A10 pHash", "both", "R3 + agent (F0.4 §6)",
      "Hamming ≤ 4 (giống hệt) không chủ ý", "khác nhau / chủ ý"),
    C("IMG-13", "Poster/thumbnail video vỡ", "medium", "low→high", "",
      "A9, A7", "both", "R3 + agent",
      "thumbnail trống / vỡ", "thumbnail ổn"),
    C("IMG-14", "Ảnh load dở (progressive kẹt)", "medium", "low→medium", "",
      "A9 (vùng dở)", "agent", "",
      "ảnh chỉ load 1 phần / progressive kẹt", "load đủ"),
    C("IMG-15", "Ảnh không khớp nội dung", "high", "medium→critical", "ctx",
      "nội dung ảnh + ngữ cảnh", "phase2", "(cần nhìn nội dung)",
      "sai ảnh sản phẩm", "ảnh khớp"),

    # ── F. CMP ────────────────────────────────────────────────────────────────
    C("CMP-01", "Touch target nhỏ", "high", "medium→high", "a11y,mob",
      "`touch_target`, `interactive` (A12)", "rule", "R1 (F0.4 §2)",
      "interactive & target < 44pt iOS / 48dp Android", "≥ ngưỡng"),
    C("CMP-02", "Control không nhãn", "medium", "low→high", "a11y",
      "role + `text` rỗng", "both", "R1 + agent",
      "nút icon-only không text/nhãn", "có nhãn"),
    C("CMP-03", "Không tap được do bị đè", "critical", "high→critical", "",
      "overlap + interactive", "rule", "R1",
      "element trên che control interactive", "không bị che"),
    C("CMP-04", "Control sai state", "high", "medium→critical", "ctx",
      "role toggle/checkbox/radio", "agent", "",
      "toggle/checkbox/radio sai trạng thái", "state đúng"),
    C("CMP-05", "Trùng component", "medium", "low→high", "ctx",
      "A10 + bbox + text", "both", "R3/R1 + agent",
      "2 nút giống hệt không chủ ý", "không trùng"),
    C("CMP-06", "Thiếu component kỳ vọng", "high", "medium→critical", "ctx",
      "tập role / ngữ cảnh", "agent", "",
      "form không có submit/back", "đủ component"),
    C("CMP-07", "Input lỗi (label/focus/placeholder)", "medium", "low→high", "a11y",
      "role=input, text", "agent", "",
      "label đè value / placeholder nhầm value / không focus", "input đúng"),
    C("CMP-08", "Text nút / label bị cắt cụt", "medium", "low→high", "i18n",
      "`text_truncated`", "both", "R4 + agent",
      "label nút bị cắt", "đủ chữ"),
    C("CMP-09", "Disabled sai", "high", "medium→critical", "ctx",
      "states", "agent", "",
      "đáng enable lại disable / ngược lại", "đúng trạng thái"),
    C("CMP-10", "Control lệch hàng trong nhóm", "low", "trivial→medium", "",
      "bbox nhóm", "both", "R1 + agent",
      "không thẳng hàng trong nhóm", "thẳng hàng"),
    C("CMP-11", "Dropdown/menu/tooltip lòi ra ngoài màn", "medium", "low→high", "resp",
      "bbox vs viewport", "both", "R1 + agent",
      "render ra ngoài màn", "trong màn"),
    C("CMP-12", "Progress/loading indicator sai/kẹt", "medium", "low→high", "",
      "role spinner/progress", "agent", "(temporal=true)",
      "indicator kẹt (1 frame → temporal)", "không kẹt"),
    C("CMP-13", "Badge/notification count sai vị trí/tràn", "low", "trivial→medium", "",
      "bbox badge", "agent", "",
      "badge lệch / '99+' tràn", "badge đúng"),
    C("CMP-14", "Tab/segment không rõ cái đang chọn", "medium", "low→high", "a11y",
      "states tab", "agent", "",
      "active/selected không phân biệt", "rõ active"),
    C("CMP-15", "Component khác cỡ (cùng loại)", "low", "trivial→medium", "multi",
      "bbox cùng role (cần multi-ảnh)", "phase2", "",
      "cùng nút khác cỡ giữa các nơi", "nhất quán"),
    C("CMP-16", "Khoảng tap chồng nhau", "medium", "low→high", "a11y,mob",
      "`relations.gap` interactive", "rule", "R1 (TOUCH_GAP_MIN)",
      "2 control interactive < 8pt gap", "≥ 8pt"),
    C("CMP-17", "Thiếu affordance cuộn/swipe", "low", "trivial→medium", "ctx",
      "bbox + ngữ cảnh", "agent", "",
      "không có dấu hiệu cuộn được", "có affordance"),

    # ── G. STATE ──────────────────────────────────────────────────────────────
    C("STATE-01", "Skeleton / loading kẹt", "high", "medium→critical", "",
      "role skeleton", "agent", "(temporal=true)",
      "có skeleton/shimmer (báo, đánh temporal)", "không có skeleton"),
    C("STATE-02", "Empty state trống trơn", "medium", "low→high", "ctx",
      "text + vùng trống", "agent", "",
      "vùng trống không có thông báo empty", "có empty message"),
    C("STATE-03", "Error/stack trace lòi", "high", "medium→critical", "",
      "`element.text`", "both", "R4 + agent",
      "text chứa stack trace / mã lỗi thô", "không lộ lỗi thô"),
    C("STATE-04", "Render dở dang", "medium", "low→high", "",
      "A9 + role", "agent", "",
      "một phần load, một phần chưa", "render đầy đủ"),
    C("STATE-05", "Stale data / placeholder còn sót", "medium", "low→high", "ctx",
      "`element.text`", "agent", "",
      "dữ liệu cũ / placeholder còn sót", "dữ liệu mới"),
    C("STATE-06", "Spinner/overlay đè không tắt", "medium", "low→high", "",
      "role overlay", "agent", "(temporal=true)",
      "overlay che nội dung", "không che"),
    C("STATE-07", "Modal/toast/snackbar kẹt", "medium", "low→high", "",
      "role modal/toast", "agent", "(temporal=true)",
      "kẹt / không tự tắt / đè sai", "hiển thị đúng"),
    C("STATE-08", "Pull-refresh/pagination kẹt", "medium", "low→high", "mob",
      "role + dup", "agent", "",
      "nhân đôi item / kẹt", "phân trang đúng"),
    C("STATE-09", "Animation/transition kẹt giữa chừng", "low", "trivial→medium", "",
      "frame (motion)", "phase2", "(1 frame yếu)",
      "frame dở giữa transition", "—"),
    C("STATE-10", "Trạng thái không khớp dữ liệu", "medium", "low→high", "ctx,multi",
      "badge vs list", "agent", "",
      "badge '3' nhưng list rỗng", "khớp dữ liệu"),
    C("STATE-11", "Offline / no-network không xử lý", "high", "medium→critical", "ctx",
      "màn trắng / text", "agent", "",
      "màn trắng khi no-network", "có xử lý offline"),

    # ── H. ENV ────────────────────────────────────────────────────────────────
    C("ENV-01", "Safe-area / notch che nội dung", "high", "medium→critical", "mob",
      "`safe_area` (A13), bbox", "rule", "R1 (F0.4 §8)",
      "bbox trong vùng notch/status/home indicator", "ngoài vùng safe-area"),
    C("ENV-02", "Status/nav bar đè hoặc lẫn màu", "medium", "low→high", "mob",
      "`safe_area`, color", "both", "R1 + agent",
      "nội dung đè status bar / lẫn màu", "không đè"),
    C("ENV-03", "Home indicator (iOS) đè nút", "medium", "low→high", "mob",
      "`safe_area.bottom`", "rule", "R1",
      "nút chạm vùng home indicator", "trên vùng"),
    C("ENV-04", "Bàn phím che input/submit", "high", "medium→critical", "mob",
      "(cần state bàn phím)", "phase2", "",
      "input/submit bị bàn phím che", "không che"),
    C("ENV-05", "Landscape / xoay màn vỡ layout", "medium", "low→high", "resp,mob",
      "(cần ảnh landscape)", "phase2", "",
      "layout vỡ khi xoay", "ổn khi xoay"),
    C("ENV-06", "Font-scale lớn làm vỡ layout", "high", "medium→critical", "a11y,mob",
      "`font_scale` + overflow", "both", "R1 + agent",
      "font_scale lớn gây tràn/cắt", "ổn khi scale"),
    C("ENV-07", "Vỡ ở thiết bị/độ phân giải khác", "medium", "low→high", "resp",
      "(cần multi-viewport)", "phase2", "",
      "vỡ ở size khác", "ổn mọi size"),
    C("ENV-08", "Web responsive breakpoint vỡ", "high", "medium→critical", "resp,web",
      "(cần multi-viewport)", "phase2", "",
      "tablet/desktop vỡ", "breakpoint ổn"),
    C("ENV-09", "Viewport-unit / 100vh lỗi mobile", "medium", "low→high", "resp,web",
      "(cần tương tác trình duyệt)", "phase2", "",
      "100vh lỗi do thanh trình duyệt", "—"),
    C("ENV-10", "Asset không đúng mật độ (@1x)", "low", "trivial→medium", "mob",
      "`image_meta` + dpr", "rule", "R3 (upscale)",
      "@1x trên màn @3x → mờ", "đúng @Nx"),
    C("ENV-11", "Foldable / cutout / multi-window vỡ", "low", "trivial→medium", "mob",
      "(cần thiết bị đặc biệt)", "phase2", "", "vỡ trên foldable/cutout", "—"),
    C("ENV-12", "Hover/cursor lỗi (web) / hover-only (mobile)", "low", "trivial→medium", "web",
      "(cần tương tác)", "phase2", "", "hover-only không tap được", "—"),
    C("ENV-13", "Splash / launch screen kẹt/sai tỉ lệ", "medium", "low→high", "mob",
      "role splash, image_meta", "agent", "",
      "splash kẹt / sai tỉ lệ", "splash đúng"),

    # ── I. CONS (đều cần nhiều ảnh — Phase 2) ──────────────────────────────────
    C("CONS-01", "Component khác cỡ giữa các màn", "low", "trivial→medium", "multi",
      "bbox cùng role (đa màn)", "phase2", "", "cùng component khác kích cỡ", "nhất quán"),
    C("CONS-02", "Lệch font giữa các màn", "low", "trivial→medium", "multi",
      "`font_family/size/weight` (đa màn)", "phase2", "", "font lệch giữa màn", "nhất quán"),
    C("CONS-03", "Lệch bảng màu / theme drift", "low", "trivial→medium", "multi",
      "`color` (đa màn)", "phase2", "", "palette lệch giữa màn", "nhất quán"),
    C("CONS-04", "Icon khác phong cách", "low", "trivial→medium", "multi",
      "`role=icon` (đa màn)", "phase2", "", "outline lẫn filled", "đồng nhất"),
    C("CONS-05", "Thuật ngữ/label không nhất quán", "medium", "low→high", "multi,ctx",
      "`text` cùng hành động (đa màn)", "phase2", "", "'Đăng xuất' vs 'Thoát'", "nhất quán"),
    C("CONS-06", "Spacing system không nhất quán", "low", "trivial→low", "multi",
      "`gap/grid` (đa màn)", "phase2", "", "spacing khác giữa màn", "nhất quán"),
    C("CONS-07", "Định dạng số/ngày/tiền khác nhau", "medium", "low→high", "multi,i18n",
      "`text` (đa màn)", "phase2", "", "format khác giữa màn", "nhất quán"),
    C("CONS-08", "Vị trí phần tử chung lệch", "medium", "low→high", "multi",
      "bbox nút back/nav (đa màn)", "phase2", "", "back lúc trái lúc phải", "nhất quán"),
    C("CONS-09", "Phong cách ảnh không đồng nhất", "low", "trivial→medium", "multi",
      "`image_meta` (đa màn)", "phase2", "", "tỉ lệ/bo góc/filter khác", "đồng nhất"),
]


def group_of(cid: str) -> str:
    return cid.split("-")[0]


def render_one(c: dict) -> str:
    g = group_of(c["id"])
    pass_ = c["pass_"] or "Không phát hiện dấu hiệu ở mục **Không đạt**."
    tags = c["tags"] or "—"
    tech = (WHO[c["who"]] + (f" — {c['tech']}" if c["tech"] else ""))
    return f"""# {c['id']} — {c['name']}

> **Nhóm:** {GROUPS[g]} (`{g}`)
> **Severity nền:** `{c['sev']}` (range `{c['rng']}`) · **Tags:** {tags}
> **Trạng thái:** {STATUS[c['status']]}
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
{c['data']}

## Kỹ thuật & ai đánh giá
{tech}

## ❌ Không đạt (fail) khi
{c['fail']}

## ✅ Đạt (pass) khi
{pass_}

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
"""


def render_index() -> str:
    lines = [
        "# Tổng hợp tiêu chí đánh giá lỗi UI",
        "",
        f"**{len(DATA)} tiêu chí / {len(GROUPS)} nhóm.** Mỗi tiêu chí có file chi tiết riêng "
        "(dữ liệu · kỹ thuật · đạt/không đạt). _Sinh tự động bởi `scripts/gen_criteria.py`._",
        "",
        "**Cột Kỹ thuật:** 🟦 rule tất định · 🟥 agent Codex (text-only) · 🟦🟥 rule+agent · ⏳ Phase 2.",
        "",
        "Liên quan: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) (danh sách gốc), "
        "[`../F0.4-thresholds.md`](../F0.4-thresholds.md) (ngưỡng), "
        "[`../F1.1-codex-cli-architecture.md`](../F1.1-codex-cli-architecture.md) (kiến trúc reasoning).",
        "",
    ]
    badge = {"rule": "🟦", "agent": "🟥", "both": "🟦🟥", "phase2": "⏳"}
    # đếm
    counts: dict[str, int] = {}
    for c in DATA:
        counts[c["who"]] = counts.get(c["who"], 0) + 1
    lines.append(
        f"> Phân bố: 🟦 rule {counts.get('rule',0)} · 🟦🟥 rule+agent {counts.get('both',0)} · "
        f"🟥 agent {counts.get('agent',0)} · ⏳ phase2 {counts.get('phase2',0)}."
    )
    lines.append("")
    for g, gname in GROUPS.items():
        rows = [c for c in DATA if group_of(c["id"]) == g]
        if not rows:
            continue
        lines.append(f"## {g} — {gname}")
        lines.append("")
        lines.append("| ID | Tiêu chí | Sev | Kỹ thuật | Chi tiết |")
        lines.append("|---|---|---|---|---|")
        for c in rows:
            lines.append(
                f"| `{c['id']}` | {c['name']} | {c['sev']} | {badge[c['who']]} | "
                f"[{c['id']}.md]({c['id']}.md) |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [c["id"] for c in DATA]
    assert len(ids) == len(set(ids)), "Trùng ID!"
    for c in DATA:
        (OUT / f"{c['id']}.md").write_text(render_one(c), encoding="utf-8")
    (OUT / "README.md").write_text(render_index(), encoding="utf-8")
    print(f"Đã sinh {len(DATA)} file tiêu chí + README.md vào {OUT}")


if __name__ == "__main__":
    main()
