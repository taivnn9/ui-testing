"""
R4 — Regex patterns và từ điển cho text rule engine.
Tất cả pattern được compile sẵn để tái sử dụng hiệu quả.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# R4-CNT01 — Placeholder / biến chưa render
# ---------------------------------------------------------------------------

PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    # Template engine: {{var}}, ${expr}
    re.compile(r"\{\{[^}]+\}\}"),
    re.compile(r"\$\{[^}]+\}"),
    # Printf-style: %s, %d, %i, %f, %@, %1$s, %2$d
    re.compile(r"%[@sdifu]|%\d+\$[@sdifu]"),
    # Positional: {0}, {name}, {first_name}
    re.compile(r"\{[a-zA-Z_]\w*\}"),
    re.compile(r"\{\d+\}"),
    # Literal null-like values (whole word)
    re.compile(r"\bundefined\b", re.IGNORECASE),
    re.compile(r"\bnull\b", re.IGNORECASE),
    re.compile(r"\bNaN\b"),
    re.compile(r"\bNone\b"),
    # Double-underscore placeholders: __PLACEHOLDER__, __NAME__
    re.compile(r"__\w+__"),
    # Square bracket templates: [[var]]
    re.compile(r"\[\[\w+\]\]"),
    # Android XML leak: @string/key_name
    re.compile(r"@string/\w+"),
    # iOS: NSLocalizedString
    re.compile(r"\bNSLocalizedString\b"),
    # Untranslated marker
    re.compile(r"\bUNTRANSLATED_\w+\b"),
]

# ---------------------------------------------------------------------------
# R4-CNT02 — i18n key lòi ra
# ---------------------------------------------------------------------------

I18N_KEY_PATTERNS: list[re.Pattern] = [
    # Dot-notation: home.title, btn.submit, error.network.timeout (2-5 segments)
    re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,4}$"),
    # SCREAMING_SNAKE_CASE: BTN_SUBMIT, HOME_TITLE (tối thiểu 4 ký tự sau chữ đầu)
    re.compile(r"^[A-Z][A-Z0-9_]{3,}$"),
    # snake_case thuần (không có space, không phải word): home_title, btn_submit (≥4 ký tự)
    re.compile(r"^[a-z][a-z_]{3,}$"),
]

# ---------------------------------------------------------------------------
# R4-CNT04 — Lorem ipsum / placeholder copy
# ---------------------------------------------------------------------------

LOREM_IPSUM_PHRASES: list[str] = [
    "lorem ipsum",
    "lorem ipsum dolor",
    "ipsum dolor sit",
    "consectetur adipiscing",
    "your text here",
    "text placeholder",
    "sample text",
    "dummy text",
    "placeholder text",
    "enter text",
    "write something here",
    "[placeholder]",
    "(text)",
    "[text]",
    "insert text here",
    "add text here",
]

# ---------------------------------------------------------------------------
# R4-CNT05 — Text debug / nội bộ
# ---------------------------------------------------------------------------

DEBUG_WORDS: list[str] = [
    "asdf",
    "qwerty",
    "foobar",
    "foo",
    "bar",
    "baz",
    "todo",
    "fixme",
    "hack",
    "xxx",
    "temp",
    "test",
    "do not ship",
    "debug",
    "dev only",
    "[test]",
    "[debug]",
    "[todo]",
    "dummy",
    "stub",
    "mock",
    "[wip]",
    "work in progress",
]

# Regex bổ sung cho debug text
_DEBUG_PATTERNS: list[re.Pattern] = [
    re.compile(r"\btest\d+\b", re.IGNORECASE),
    re.compile(r"\b(admin|password|123456)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# R4-CNT06 — Mojibake / HTML entity thô
# ---------------------------------------------------------------------------

MOJIBAKE_PATTERNS: list[re.Pattern] = [
    # Chuỗi ký tự Ã / â€ liên tiếp — dấu hiệu UTF-8 bị decode sai thành Latin-1
    re.compile(r"[ÃÂ]{2,}"),
    re.compile(r"â€[^\s]{1,3}"),
    # HTML entities thực sự trong text (không phải HTML content)
    re.compile(r"&(?:[a-z]{2,7}|#\d{1,5});"),
    # BOM và invisible chars
    re.compile(r"[﻿​‌‍�]"),
]

# ---------------------------------------------------------------------------
# R4-CNT07 — Escape literal
# ---------------------------------------------------------------------------

ESCAPE_PATTERNS: list[re.Pattern] = [
    # Escape sequences thô
    re.compile(r"\\n|\\t|\\r"),
    # HTML tags thô trong text
    re.compile(r"<br\s*/?>", re.IGNORECASE),
    re.compile(r"</?p>", re.IGNORECASE),
    re.compile(r"</?b>", re.IGNORECASE),
    re.compile(r"</?i>", re.IGNORECASE),
    re.compile(r"</?span[^>]*>", re.IGNORECASE),
    # Double-escaped HTML
    re.compile(r"&lt;|&gt;|&amp;"),
]

# ---------------------------------------------------------------------------
# R4-CNT08 — Epoch / format số sai
# ---------------------------------------------------------------------------

EPOCH_PATTERNS: list[re.Pattern] = [
    # UNIX timestamp giây (10 chữ số, từ khoảng 2001 đến 2286)
    re.compile(r"\b1[3-9]\d{8}\b"),
    # UNIX timestamp millisecond (13 chữ số)
    re.compile(r"\b[12]\d{12}\b"),
    # ISO datetime đầy đủ trong UI (thường không nên hiển thị raw)
    re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"),
    # Số lớn không định dạng (≥7 chữ số liên tiếp, không có dấu phân cách)
    re.compile(r"\b\d{7,}\b"),
]

# ---------------------------------------------------------------------------
# R4-STATE03 — Stack trace / raw error
# ---------------------------------------------------------------------------

STACKTRACE_PATTERNS: list[re.Pattern] = [
    # Java/Kotlin stack trace
    re.compile(r"at \w[\w.$]+\("),
    # Python traceback
    re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE),
    # JavaScript errors
    re.compile(r"\b(?:TypeError|ReferenceError|SyntaxError|RangeError|URIError):", re.IGNORECASE),
    re.compile(r"\bError:"),
    # iOS crash
    re.compile(r"Thread \d+.*crash", re.IGNORECASE),
    # Generic Java exception
    re.compile(r"Exception in thread", re.IGNORECASE),
    re.compile(r"\bjava\.lang\.\w+"),
    re.compile(r"\bNullPointerException\b"),
    re.compile(r"\bArrayIndexOutOfBoundsException\b"),
    # HTTP error codes (4xx/5xx standalone)
    re.compile(r"\b[45]\d{2}\b"),
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def match_any(text: str, patterns: list[re.Pattern]) -> list[str]:
    """Return list of all matched strings from any pattern in the list."""
    results: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            results.append(m.group(0))
    return results


def match_dict(text: str, words: list[str]) -> list[str]:
    """
    Case-insensitive substring match against a list of words/phrases.
    Returns matched words that appear in text.
    """
    text_lower = text.lower()
    return [w for w in words if w.lower() in text_lower]


def match_debug_patterns(text: str) -> list[str]:
    """Match debug regex patterns (test1, admin, password, etc.)."""
    return match_any(text, _DEBUG_PATTERNS)
