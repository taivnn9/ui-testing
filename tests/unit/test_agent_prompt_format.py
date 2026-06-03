"""Regression: prompt SYSTEM_G* chứa dấu ngoặc literal ('${x}', '{{var}}') không được
làm vỡ việc điền placeholder. Trước đây dùng str.format → KeyError: 'x' → 500."""
from __future__ import annotations

import json

from ui_defect.agents.runner import _fill, _issues_to_json

# Fixture: text chứa placeholder hợp lệ + dấu ngoặc literal (giống prompt/skill cũ)
_TPL = ("Screen locale: {locale} | Platform: {platform}. "
        "Unrendered examples: {{var}}, ${x}, %s, %@ — phải giữ nguyên.")


def test_fill_replaces_only_known_placeholders():
    out = _fill(_TPL, locale="vi-VN", platform="android")
    # placeholder đã biết được thay
    assert "{locale}" not in out
    assert "vi-VN" in out
    # dấu ngoặc literal trong ví dụ vẫn nguyên (không bị format nuốt / không ném lỗi)
    assert "${x}" in out
    assert "{{var}}" in out


def test_fill_does_not_raise_on_unescaped_braces():
    # str.format(_TPL) sẽ ném KeyError: 'x' — _fill thì không
    _fill(_TPL, locale="en-US", platform="web")


def test_fill_leaves_unrelated_braces_untouched():
    tpl = "Locale {locale}. Example unrendered: ${x}, {{var}}, %s. Keep {unknown}."
    out = _fill(tpl, locale="vi-VN")
    assert out == "Locale vi-VN. Example unrendered: ${x}, {{var}}, %s. Keep {unknown}."


def test_issues_to_json_accepts_dicts():
    # Regression: candidate_issues đi vào dạng list[dict] (qua filter_issues),
    # trước đây _issues_to_json đọc attribute → AttributeError: 'dict' has no 'rule'.
    issues = [
        {"rule": "R1.touch_target", "element": "e5", "severity": "high",
         "confidence": 0.876, "detail": "x" * 300},
        {"rule": "R2.contrast", "element": "e9", "severity": "medium"},  # thiếu field
    ]
    out = json.loads(_issues_to_json(issues))
    assert out[0]["rule"] == "R1.touch_target"
    assert out[0]["confidence"] == 0.88            # round 2 chữ số
    assert len(out[0]["detail"]) == 200            # cắt 200
    assert out[1]["confidence"] == 0.0             # default khi thiếu
    assert out[1]["detail"] == ""
