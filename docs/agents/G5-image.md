# G5 — Image/Icon Agent

> ⚠️ **Lỗi thời:** VLM agent đã thay bằng **Codex CLI text-only** (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)).
> Tiêu chí vẫn dùng, nay ở `src/ui_defect/agents/skills/50-images.md`.

> **Nhiệm vụ:** xác nhận và phát hiện lỗi **ảnh, icon, media** — vỡ, méo,
> mờ, sai ngữ nghĩa, placeholder.
>
> **Tiêu chí:** IMG-01–15
>
> Đặc điểm: nhiều tiêu chí cần **ngữ cảnh** (IMG-04/06/10/15) → VLM phán đoán
> từ nhận dạng visual; một số không có reference → confidence giới hạn ở mức 0.6.

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G5.png",
  "screen": { "platform", "viewport" },
  "elements": [/* role=image|icon */],
  "image_meta": [/* từ A7: intrinsic/displayed, blur_score, scale_mode */],
  "icon_regions": [/* từ A6: subtype, color_count, edge_density, template_match, possible_placeholder */],
  "hash_results": [/* từ A10: duplicate pairs */],
  "candidate_issues": [/* prefix R3-IMG*, A6-*, A9-broken* */]
}
```

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận / bác bỏ R3 candidates

| Candidate | G5 làm gì |
|---|---|
| R3-IMG02 (méo) | Xác nhận: ảnh trông bị kéo giãn/bóp rõ ràng không? |
| R3-IMG03 (mờ) | Xác nhận: ảnh blur thật sự không? Hay style intentional (frosted glass)? |
| R3-IMG07 (icon lệch tâm) | Xác nhận: icon có bị lệch so với button container không? |
| R3-IMG08 (placeholder) | Xác nhận: đây là broken image hay icon thiết kế trông vậy? |
| R3-IMG12 (ảnh trùng) | Xác nhận: trùng là lỗi hay intentional (same thumbnail trong list)? |

### 2.2 Phát hiện mới

| Tiêu chí | G5 cần phán đoán |
|---|---|
| **IMG-01** Ảnh vỡ / broken | Slot ảnh trống, icon lỗi (alt text lòi), ô trắng/xám trống |
| **IMG-04** Crop sai (cắt mất quan trọng) | Mặt người bị cắt, chữ trên ảnh mất |
| **IMG-05** Thiếu ảnh (slot trống) | Container ảnh không có nội dung — trống tuyệt đối |
| **IMG-06** Icon sai ngữ nghĩa | Icon "share" ở chỗ đáng "save", icon ngược logic |
| **IMG-09** Scale-mode sai | cover/contain/stretch — ảnh bị crop sai hoặc show letterbox |
| **IMG-10** Sai phiên bản ảnh/logo | Logo cũ/sai brand (confidence thấp không có spec) |
| **IMG-11** Logo mờ/sai màu/sai tỉ lệ | Brand asset không đúng |
| **IMG-13** Video poster vỡ | Thumbnail video không load |
| **IMG-14** Ảnh load dở | Progressive image chỉ load 1 phần rõ ràng |
| **IMG-15** Ảnh sai sản phẩm | Thumbnail không khớp tên sản phẩm (confidence thấp) |

---

## 3. System Prompt G5

```
You are an image quality and visual assets expert reviewing a UI screenshot.
Your task: identify IMAGE and ICON defects.

Focus areas:
1. Broken images: empty image slots, broken image icons (□ with mountains/image icon), blank spaces
2. Distorted images: aspect ratio stretched or squished (compare object proportions)
3. Blurry/pixelated: genuinely low quality images (not intentional blur/frosted effects)
4. Wrong crop: important content cut off (faces cropped at chin, text cut)
5. Icon issues:
   - Placeholder/unloaded icons (gray boxes, question marks)
   - Icons misaligned within their container
   - Wrong semantic icon (share icon where save expected)
6. Duplicate images: same image appearing twice unexpectedly
7. Image-in-image: text or faces cut or hidden inside image regions
8. Video/media: broken posters, partially loaded progressive images

KEY NOTES:
- Intentional blur (frosted glass, background blur): NOT a defect
- Intentional dark overlay on images: NOT a defect  
- Art direction crops (face centered): usually intentional
- When unsure about semantic intent (IMG-06, IMG-15): use confidence < 0.5
```

---

## 4. User Prompt G5

```
Review for image and icon defects.

Image elements:
[JSON: {id, role, bbox, image_meta: {intrinsic_w, intrinsic_h, displayed_w, displayed_h, scale_mode, blur_score}}]

Icon detections:
[JSON: icon_regions từ A6]

Duplicate hash pairs (if any):
[JSON: từ A10]

Candidate issues:
[JSON: R3-IMG* candidates]

Instructions:
1. Confirm/reject R3 candidates with visual evidence.
2. Look for broken images: empty slots, error icons, missing thumbnails.
3. Check image distortion: trust the geometry measurements but confirm visually.
4. For semantic issues (IMG-06 wrong icon, IMG-15 wrong product image): mark confidence < 0.5 and note uncertainty.
5. Distinguish intentional effects (blur, overlay, art crop) from defects.
```

---

## 5. Few-shot examples

### Example 1 — IMG-02 méo confirmed

```
[Ảnh: e8 hiển thị ảnh người nhưng bị kéo ngang rõ ràng — khuôn mặt ellipse thay vì tròn]
image_meta: intrinsic_ratio=1.0 (vuông), displayed_ratio=1.7 (ngang)
Candidate: R3-IMG02, deviation=0.41

Expected:
{
  "findings": [{
    "issue_type": "IMG-02",
    "element_id": "e8",
    "severity": "medium",
    "confidence": 0.91,
    "verdict": "confirmed",
    "original_candidate_rule": "R3-IMG02",
    "evidence": {
      "measured_value": "intrinsic_ratio=1.0, displayed_ratio=1.7, deviation=41%",
      "description": "Avatar người dùng bị kéo ngang 41% — mặt trông bẹp"
    },
    "reasoning": "Ảnh vuông render theo width=1.7× → scale-mode=stretch gây méo rõ.",
    "severity_justification": "Medium — ảnh hưởng thẩm mỹ, không block task."
  }]
}
```

### Example 2 — IMG-01 phát hiện mới (broken image)

```
[Ảnh: e12 slot ảnh sản phẩm hiển thị icon ảnh vỡ (mountains + broken corner)]
Candidates: [] (A6/A9 có thể bắt nhưng không confirm với context này)

Expected:
{
  "findings": [{
    "issue_type": "IMG-01",
    "element_id": "e12",
    "severity": "high",
    "confidence": 0.90,
    "verdict": "new_finding",
    "evidence": {
      "element_ids": ["e12"],
      "description": "Product image slot shows broken image icon — image failed to load"
    },
    "reasoning": "Broken image icon rõ ràng trong slot ảnh sản phẩm — ảnh không tải được.",
    "severity_justification": "High — ảnh sản phẩm là thông tin quan trọng với user."
  }]
}
```

---

## 6. Ranh giới và confidence caps

| Tiêu chí | Confidence tối đa | Lý do |
|---|---|---|
| IMG-02 (méo có số) | 0.95 | Số học, ít mơ hồ |
| IMG-01 (ảnh vỡ rõ) | 0.90 | Visual rõ ràng |
| IMG-04 (crop sai) | 0.65 | Cần ngữ cảnh intent |
| IMG-06 (icon sai ngữ nghĩa) | 0.55 | Không có spec |
| IMG-10 (sai phiên bản logo) | 0.50 | Cần brand guide |
| IMG-15 (sai sản phẩm) | 0.45 | Cần data catalog |

## Trạng thái: spec ✅
