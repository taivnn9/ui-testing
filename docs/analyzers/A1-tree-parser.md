# A1 — Tree Parser (DOM/XML → Canonical Schema)

> Bóc tách chi tiết. Thuộc Phase 1, nhóm "dựng cấu trúc". Tech: **Python**.
> Liên quan: [`../development-plan.md`](../development-plan.md) · [`../buoc-2-kien-truc-xu-ly.md`](../buoc-2-kien-truc-xu-ly.md)

## 1. Trách nhiệm
Khi input **có cây** (Mode A), parse **DOM (web)** hoặc **XML (Android uiautomator / iOS
XCUITest)** thành `elements[]` của schema chung — **ground truth** cho hình học / role / text /
style / cấu trúc. **KHÔNG đụng pixel** (việc của analyzer khác). Output đẩy vào A0 Normalize.

## 2. Input — làm rõ "cây" tester gửi là gì (điểm dễ sai nhất)

### 2a. Web — KHÔNG dùng raw HTML làm chính
Raw HTML **không có geometry (bbox) và computed-style** nếu không render → vô dụng cho hình
học. → Yêu cầu tester gửi **structured DOM snapshot** do Playwright trích sẵn (ground truth
thật). Định nghĩa **Web Capture Contract v1** — mảng node JSON:
```jsonc
{
  "tag":"button", "role":"button",
  "bbox":{ "x":0,"y":0,"w":0,"h":0 },          // getBoundingClientRect (CSS px)
  "text":"Đăng nhập",
  "style":{ "fontSize":16,"fontFamily":"Inter","color":"rgb(17,17,17)",
            "backgroundColor":"rgb(255,255,255)","opacity":1,"borderRadius":4,
            "zIndex":2,"overflow":"hidden","textOverflow":"ellipsis",
            "display":"flex","visibility":"visible" },
  "attrs":{ "id":"","class":"","aria-label":"","alt":"","disabled":false,
            "type":"","href":"","src":"" },
  "imageMeta":{ "naturalWidth":0,"naturalHeight":0 },   // cho <img>
  "scroll":{ "scrollWidth":0,"scrollHeight":0,"clientWidth":0,"clientHeight":0 },
  "parent": 3                                            // index node cha, -1 nếu root
}
```
+ meta toàn cục: `viewport{w,h,dpr}`, `theme`, `locale`. Kèm **snippet Playwright mẫu** cho
tester chạy (trích `getBoundingClientRect` + `getComputedStyle` cho mọi node hiển thị).
> Nếu tester CHỈ gửi raw HTML → degrade sang **mixed**: lấy được role/text/cấu trúc, KHÔNG
> geometry/style → geometry phải từ pixel (analyzer B). Đánh dấu `source` rõ.

### 2b. Mobile XML
- **Android uiautomator dump:** attrs `bounds="[x1,y1][x2,y2]"`, `text`, `content-desc`,
  `class`, `resource-id`, `clickable`, `enabled`, `focused`, `scrollable`, `selected`,
  `password`, `index`. → **geometry + role + text + interactive CÓ**; **style KHÔNG** (font/màu)
  → `style.source = vision` (pixel bù).
- **iOS XCUITest tree:** `type`, `label`, `value`, `frame`, `enabled`, `accessible`... map tương tự.

## 3. Output — field schema mà A1 điền (kèm `source`)
| Field | Web capture | Android XML | iOS XML | source | Mode B (thiếu cây) |
|---|---|---|---|---|---|
| `bbox` | rect | bounds | frame | dom/xml | từ A3 Box Detector |
| `role` | aria/tag map | class map | type map | dom/xml | từ A3/A6 |
| `text` | text | text/content-desc | label/value | dom/xml | từ A5 OCR |
| `parent/children/z` | tree+zIndex | tree+index | tree | dom/xml | từ A0 (suy ra) |
| `style.*` | computed | ❌→pixel | ❌→pixel | dom / vision | A4/A8 |
| `interactive` | tag/role/handler | clickable | enabled+type | dom/xml | từ A12 (suy luận) |
| `image_meta` | naturalW/H | ❌→pixel | ❌→pixel | dom / vision | A7 (yếu) |
| `visible/offscreen` | style+bbox | bounds vs vp | frame | dom/xml | A0 |
| `clipped` | (gợi ý từ overflow) | — | — | — | xác nhận bằng pixel |

`confidence` cao (ground truth). Mỗi **field** gắn `source` riêng (mixed case).

## 4. Kỹ thuật / lib cần (Python) — *anh xem giúp*
| Việc | Lib Python đề xuất | Ghi chú |
|---|---|---|
| Parse XML (android/ios) | **`lxml.etree`** | nhanh, XPath sẵn; fallback `xml.etree.ElementTree` (stdlib) |
| Parse raw HTML (fallback) | **`selectolax`** (nhanh) hoặc `lxml.html`/`BeautifulSoup` | chỉ cho nhánh degrade |
| Validate web-capture JSON | **`pydantic` v2** | model hoá luôn Canonical Schema, tái dùng cả service |
| Parse màu CSS (`rgb()/#hex`) | **`tinycss2`** hoặc regex tự viết | chuẩn hoá về RGB tuple cho Pixel/Contrast |
| Toạ độ / chuẩn hoá | thuần Python (không cần numpy) | ×dpr, tính `bbox_norm` |
| Bảng map role | dict tĩnh trong code | xem mục 5 |

→ Không cần CV/ML cho A1 (đó là analyzer khác). A1 thuần parse + map.

## 5. Role mapping (heuristic — bảng tra tĩnh)
- **Web:** `button, a[href], [role=button]`→`button`; `input,textarea,select`→`input`;
  `img,svg,[role=img]`→`image`; `[role=switch], input[type=checkbox|radio]`→`toggle`;
  text node / `p,span,h1..h6,label`→`text`; còn lại→`container`.
- **Android class:** `*.Button`→`button`, `EditText`→`input`, `ImageView`→`image|icon`,
  `TextView`→`text`, `Switch/CheckBox`→`toggle`, `RecyclerView/ScrollView/*Layout`→`container`.
- **iOS type:** `Button`→`button`, `TextField/SecureTextField`→`input`, `Image`→`image`,
  `StaticText`→`text`, `Switch`→`toggle`, `ScrollView/Other`→`container`.

## 6. Thuật toán
1. **Detect format**: web-capture JSON / android-xml / ios-xml (theo dấu hiệu key/attr).
2. **Parse**: `lxml` (XML) hoặc `pydantic` (JSON).
3. **Traverse** cây → mỗi node → 1 element: gán `id` (`e0,e1...`), map `role`, copy
   `bbox/text/style/attrs`, set `parent/children`, `z` (zIndex web / index|thứ tự mobile),
   `interactive`.
4. **Chuẩn hoá toạ độ**: web CSS px ×`dpr` → device px (khớp ảnh); android bounds đã là px;
   tính `bbox_norm` (0–1 theo viewport).
5. **Cờ**: `visible/offscreen` từ bbox vs viewport; `clipped` để pixel xác nhận sau.
6. **Emit** `elements[]` + `source/confidence` theo field.

## 7. Tiêu chí được A1 cấp data nền (Mode A)
bbox→`LAY-*`, `CMP-01` touch-target; role/interactive→`CMP-*`; text→`CNT-*`,`TYP-03`;
style→`STY` contrast (khi nền solid), `TYP-05` font-size; parent→`LAY-03` overflow;
z→`LAY-06` occlusion; image_meta→`IMG-02` distortion. (Chi tiết mapping: buoc-2.)

## 8. Edge cases
- Web raw-HTML-only → mixed (no geometry) — đánh dấu, để pixel lo geometry.
- XML → style luôn thiếu → pixel bù; đừng để field style rỗng gây vỡ rule.
- Node ẩn (`display:none`/`visibility:hidden`/0×0) → **vẫn giữ**, `visible=false` (cần cho
  occlusion/duplicate), nhưng loại khỏi check thị giác.
- iframe / shadow DOM (web) → Phase 2.

## 9. Open decisions (cần anh chốt)
- [ ] **Web Capture Contract v1** như trên OK chứ? Em sẽ viết kèm **snippet Playwright** cho tester.
- [ ] Phase 1 có nhận **raw HTML (degrade)** không, hay **bắt buộc structured capture**?
      *(đề xuất: ưu tiên structured; raw-HTML để Phase 2.)*

## 10. TDD outline (khi vào code)
- test: android xml mẫu → đúng số element + bbox parse `[x1,y1][x2,y2]`.
- test: web-capture json → elements + style + ×dpr.
- test: role mapping cho cả 3 nền tảng.
- test: `bbox_norm` đúng theo viewport.
- test: node ẩn giữ `visible=false`, không bị loại.
- test: mixed (raw HTML) → style/geometry source đánh dấu đúng.

## Trạng thái: spec ✅ — chờ chốt mục 9, sau đó code.
