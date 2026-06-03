"""
G0 — Prompt Framework chung: SoM renderer + Claude API call wrapper.
Spec: docs/agents/G0-prompt-framework.md
"""
from __future__ import annotations

import base64
import json
import os
from io import BytesIO
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

from ..schema.models import Element


# ── SoM color palette theo role ──────────────────────────────────────────────

_ROLE_COLORS: dict[str, str] = {
    "text": "#1a56db",
    "button": "#1a56db",
    "image": "#f05252",
    "icon": "#7e3af2",
    "input": "#057a55",
    "container": "#6b7280",
    "list": "#6b7280",
    "nav": "#92400e",
    "tab": "#92400e",
    "skeleton": "#c27803",
    "spinner": "#c27803",
    "modal": "#374151",
    "unknown": "#111827",
}


def _hex_to_rgba(hex_color: str, alpha: int = 200) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r, g, b, alpha


def render_som(
    img: Image.Image,
    elements: list[Element],
    show_bbox: bool = True,
    show_label: bool = True,
) -> Image.Image:
    """
    Vẽ Set-of-Marks lên ảnh.
    Trả ảnh mới (không modify original).
    """
    out = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.load_default(size=10)
    except Exception:
        font = ImageFont.load_default()

    for elem in elements:
        if not elem.visible:
            continue
        color_hex = _ROLE_COLORS.get(elem.role, "#111827")
        r, g, b, _ = _hex_to_rgba(color_hex)
        bbox_color = (r, g, b, 180)
        label_bg = (r, g, b, 210)

        x = int(elem.bbox.x)
        y = int(elem.bbox.y)
        w = int(elem.bbox.w)
        h = int(elem.bbox.h)

        if show_bbox and w > 0 and h > 0:
            draw.rectangle([x, y, x + w, y + h], outline=bbox_color, width=1)

        if show_label:
            label = elem.id
            pad = 2
            label_x = x + pad
            label_y = y + pad
            # Ước tính kích thước text
            char_w, char_h = 6, 10
            label_w = len(label) * char_w + pad * 2
            label_h = char_h + pad * 2
            draw.rectangle(
                [label_x, label_y, label_x + label_w, label_y + label_h],
                fill=label_bg,
            )
            draw.text((label_x + pad, label_y + pad), label, fill=(255, 255, 255, 255), font=font)

    result = Image.alpha_composite(out, overlay).convert("RGB")
    return result


def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


# ── Tool schema ───────────────────────────────────────────────────────────────

REPORT_TOOL = {
    "name": "report_ui_defects",
    "description": "Báo cáo các lỗi UI phát hiện được trong ảnh.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["issue_type", "severity", "confidence", "verdict", "evidence", "reasoning"],
                    "properties": {
                        "issue_type": {"type": "string"},
                        "element_id": {"type": ["string", "null"]},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "trivial"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "verdict": {"type": "string", "enum": ["confirmed", "new_finding", "rejected", "uncertain"]},
                        "original_candidate_rule": {"type": ["string", "null"]},
                        "evidence": {
                            "type": "object",
                            "properties": {
                                "element_ids": {"type": "array", "items": {"type": "string"}},
                                "measured_value": {"type": ["string", "null"]},
                                "expected_value": {"type": ["string", "null"]},
                                "description": {"type": "string"},
                            },
                        },
                        "reasoning": {"type": "string"},
                        "severity_justification": {"type": ["string", "null"]},
                    },
                },
            },
            "self_critique": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_index": {"type": "integer"},
                        "concern": {"type": "string"},
                        "decision": {"type": "string", "enum": ["keep", "downgrade", "remove"]},
                        "new_confidence": {"type": ["number", "null"]},
                    },
                },
            },
            "summary": {"type": "string"},
        },
        "required": ["findings", "self_critique", "summary"],
    },
}


# ── JSON schema nhúng vào system prompt (thay tool_use) ──────────────────────

_OUTPUT_SCHEMA_INSTRUCTION = """
Respond ONLY with valid JSON matching this exact schema (no markdown, no explanation outside JSON):

{
  "findings": [
    {
      "issue_type": "STY-01",          // catalog code
      "element_id": "e7",              // ID from marked image, or null
      "severity": "high",              // critical|high|medium|low|trivial
      "confidence": 0.9,               // 0.0–1.0
      "verdict": "confirmed",          // confirmed|new_finding|rejected|uncertain
      "original_candidate_rule": "R2-STY01",  // rule that flagged this, or null
      "evidence": {
        "element_ids": ["e7"],
        "measured_value": "contrast=2.8",
        "expected_value": ">=4.5",
        "description": "short description"
      },
      "reasoning": "why this is a real defect",
      "severity_justification": "why this severity level"
    }
  ],
  "self_critique": [
    {
      "issue_index": 0,
      "concern": "might be intentional design",
      "decision": "keep",             // keep|downgrade|remove
      "new_confidence": 0.75
    }
  ],
  "summary": "one sentence summary"
}
"""


# ── llama.cpp call wrapper ─────────────────────────────────────────────────────

def call_agent(
    marked_image: Image.Image,
    system_prompt: str,
    user_text: str,
    model: str | None = None,
    max_tokens: int = 1500,
) -> dict[str, Any]:
    """
    Gọi llama.cpp /v1/chat/completions với vision + JSON output.
    Trả dict findings đã parse.
    """
    from .llm_client import call_llm

    full_system = system_prompt + "\n\n" + _OUTPUT_SCHEMA_INSTRUCTION

    try:
        return call_llm(
            system_prompt=full_system,
            user_text=user_text,
            image=marked_image,
            max_tokens=max_tokens,
            model=model,
        )
    except Exception as exc:
        # Degrade graceful (không kéo sập cả pipeline) NHƯNG surface lỗi qua key `_error`
        # để runner đẩy lên agent_errors → người dùng thấy lý do (vd cấu hình LLM sai).
        return {
            "findings": [],
            "self_critique": [],
            "summary": f"llm_error: {exc}",
            "_error": f"{type(exc).__name__}: {exc}",
        }


# ── Context trimming helpers ──────────────────────────────────────────────────

_AGENT_ROLE_FILTER: dict[str, list[str] | None] = {
    "G1": ["text", "button", "input", "nav", "tab"],
    "G2": ["text", "button", "input"],
    "G3": ["text", "button", "icon", "input", "toggle", "nav"],
    "G4": None,
    "G5": ["image", "icon"],
    "G6": ["button", "input", "toggle", "tab", "nav", "container", "skeleton", "spinner"],
}

_AGENT_ISSUE_PREFIXES: dict[str, list[str]] = {
    "G1": ["CNT", "TYP-03", "TYP-06", "TYP-07", "TYP-10", "TYP-11", "R4"],
    "G2": ["TYP-01", "TYP-02", "TYP-04", "TYP-05", "TYP-09", "TYP-12", "TYP-13", "TYP-14", "A8"],
    "G3": ["STY", "R2"],
    "G4": ["LAY", "ENV-04", "ENV-05", "ENV-06", "R1-LAY"],
    "G5": ["IMG", "R3"],
    "G6": ["CMP", "STATE", "ENV-01", "ENV-02", "ENV-03", "R1-CMP", "R1-ENV", "A9"],
}


def filter_elements(elements: list[Element], agent_id: str) -> list[Element]:
    roles = _AGENT_ROLE_FILTER.get(agent_id)
    if roles is None:
        return elements
    return [e for e in elements if e.role in roles]


def filter_issues(issues: list[dict], agent_id: str) -> list[dict]:
    prefixes = _AGENT_ISSUE_PREFIXES.get(agent_id, [])
    if not prefixes:
        return issues
    return [
        i for i in issues
        if any(i.get("rule", "").startswith(p) for p in prefixes)
    ]
