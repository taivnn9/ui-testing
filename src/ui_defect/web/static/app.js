"use strict";

const SEV = {
  critical: { color: "#e53935", rank: 5 },
  high:     { color: "#fb8c00", rank: 4 },
  medium:   { color: "#fdd835", rank: 3 },
  low:      { color: "#42a5f5", rank: 2 },
  trivial:  { color: "#9e9e9e", rank: 1 },
};
const SEV_ORDER = ["critical", "high", "medium", "low", "trivial"];

const state = {
  file: null,
  objectUrl: null,
  issues: [],          // [{...issue, _num}]
  activeId: null,
  hiddenSev: new Set(),
};

const $ = (sel) => document.querySelector(sel);

function init() {
  const dz = $("#dropzone");
  const fileInput = $("#fileInput");
  dz.addEventListener("click", () => fileInput.click());
  dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("dragover"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault(); dz.classList.remove("dragover");
    if (e.dataTransfer.files.length) onFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) onFile(fileInput.files[0]);
  });
  $("#analyzeBtn").addEventListener("click", analyze);
  $("#toggleAdvanced").addEventListener("click", () => {
    $("#advanced").classList.toggle("hidden");
  });
  window.addEventListener("resize", positionOverlays);
}

function onFile(file) {
  if (!file.type.startsWith("image/")) {
    showBanner("File không phải ảnh hợp lệ.");
    return;
  }
  clearBanner();
  state.file = file;
  if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
  state.objectUrl = URL.createObjectURL(file);
  $("#dropzone").textContent = file.name;
  const img = $("#screenshot");
  img.onload = positionOverlays;
  img.src = state.objectUrl;
  $("#canvasWrap").classList.remove("hidden");
  $("#analyzeBtn").disabled = false;
  // reset kết quả cũ
  state.issues = [];
  state.activeId = null;
  document.querySelector("#summary").innerHTML = "";
  renderResults();
  clearOverlays();
}

async function analyze() {
  if (!state.file) { showBanner("Hãy chọn ảnh trước."); return; }
  clearBanner();
  const btn = $("#analyzeBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Đang phân tích…';

  const fd = new FormData();
  fd.append("screenshot", state.file);
  fd.append("platform", $("#platform").value);
  fd.append("min_severity", $("#minSeverity").value);
  fd.append("min_confidence", $("#minConfidence").value);
  fd.append("run_vlm", $("#runVlm").checked ? "true" : "false");

  try {
    const resp = await fetch("/analyze", { method: "POST", body: fd });
    if (!resp.ok) {
      const detail = await safeDetail(resp);
      showError(resp.status, detail);
      return;
    }
    const data = await resp.json();
    state.issues = data.issues.map((it, i) => ({ ...it, _num: i + 1 }));
    state.issues.sort((a, b) =>
      (SEV[b.severity]?.rank || 0) - (SEV[a.severity]?.rank || 0) ||
      b.confidence - a.confidence);
    state.issues.forEach((it, i) => { it._num = i + 1; });
    renderSummary(data.summary);
    renderResults();
    renderOverlays();
    // Cảnh báo nếu agent VLM lỗi nhưng pipeline vẫn chạy (HTTP 200)
    const agentErrors = (data.pipeline_meta && data.pipeline_meta.agent_errors) || [];
    if (agentErrors.length) showAgentErrors(agentErrors);
  } catch (e) {
    showBannerHtml("warn",
      `<strong>Không kết nối được server.</strong>` +
      `<pre>${esc(String(e && e.message || e))}</pre>`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Phân tích";
  }
}

async function safeDetail(resp) {
  // detail có thể là object (chi tiết) hoặc string (lỗi đơn giản)
  try { const j = await resp.json(); return j.detail !== undefined ? j.detail : j; }
  catch { try { return await resp.text(); } catch { return ""; } }
}

// Render lỗi chi tiết: chấp nhận detail là string hoặc object {error,stage,type,message,cause,traceback}
function showError(status, detail) {
  const head = {
    400: "Ảnh không hợp lệ",
    413: "Ảnh quá lớn (vượt giới hạn)",
    422: "Tham số gửi lên không hợp lệ",
    500: "Phân tích thất bại",
  }[status] || ("Lỗi không xác định (" + status + ")");

  if (detail && typeof detail === "object") {
    const rows = [];
    if (detail.stage) rows.push(`<div><b>stage:</b> ${esc(detail.stage)}</div>`);
    if (detail.type) rows.push(`<div><b>type:</b> ${esc(detail.type)}</div>`);
    if (detail.message) rows.push(`<div><b>message:</b> ${esc(detail.message)}</div>`);
    if (detail.cause) rows.push(`<div><b>cause:</b> ${esc(detail.cause)}</div>`);
    let tb = "";
    if (detail.traceback) {
      const lines = Array.isArray(detail.traceback) ? detail.traceback.join("\n") : String(detail.traceback);
      tb = `<details open><summary>Traceback</summary><pre>${esc(lines)}</pre></details>`;
    }
    showBannerHtml("error",
      `<strong>HTTP ${status} — ${esc(head)}</strong>${rows.join("")}${tb}`);
  } else {
    showBannerHtml("error",
      `<strong>HTTP ${status} — ${esc(head)}</strong><pre>${esc(String(detail || ""))}</pre>`);
  }
}

function showAgentErrors(agentErrors) {
  const lines = agentErrors
    .map((a) => `${esc(a.agent_id || "?")}: ${esc(a.error || "")}`).join("\n");
  showBannerHtml("warn",
    `<strong>⚠ ${agentErrors.length} agent VLM lỗi</strong> ` +
    `(pipeline vẫn chạy bằng rule — kiểm tra cấu hình LLM_BASE_URL/LLM_MODEL):` +
    `<pre>${lines}</pre>`);
}

function renderSummary(summary) {
  const el = $("#summary");
  if (!summary) { el.innerHTML = ""; return; }
  const chips = SEV_ORDER.map((s) => {
    const n = (summary.by_severity && summary.by_severity[s]) || 0;
    const off = state.hiddenSev.has(s) ? " off" : "";
    return `<span class="sev-chip${off}" data-sev="${s}">
      <span class="dot" style="background:${SEV[s].color}"></span>${s} ${n}</span>`;
  }).join("");
  el.innerHTML = `<div><strong>Tổng ${summary.total_issues} lỗi</strong>
    <span class="issue-conf"> · confidence TB ${(summary.confidence_avg || 0).toFixed(2)}</span></div>
    <div class="sev-chips">${chips}</div>`;
  el.querySelectorAll(".sev-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const s = chip.dataset.sev;
      if (state.hiddenSev.has(s)) state.hiddenSev.delete(s); else state.hiddenSev.add(s);
      chip.classList.toggle("off");
      renderResults(); renderOverlays();
    });
  });
}

function renderResults() {
  const list = $("#issueList");
  const visible = state.issues.filter((it) => !state.hiddenSev.has(it.severity));
  if (state.issues.length === 0) {
    list.innerHTML = `<div class="empty">Chưa có kết quả. Tải ảnh và ấn Phân tích.</div>`;
    return;
  }
  if (visible.length === 0) {
    list.innerHTML = `<div class="empty">Không phát hiện lỗi 🎉</div>`;
    return;
  }
  list.innerHTML = visible.map((it) => {
    const c = SEV[it.severity]?.color || "#999";
    const active = it.id === state.activeId ? " active" : "";
    const ev = it.evidence || {};
    const measured = ev.measured_value ? `<dt>Đo được</dt><dd>${esc(ev.measured_value)}</dd>` : "";
    const expected = ev.expected_value ? `<dt>Kỳ vọng</dt><dd>${esc(ev.expected_value)}</dd>` : "";
    const role = it.element_role ? `<dt>Element</dt><dd>${esc(it.element_role)}</dd>` : "";
    const txt = it.element_text ? `<dt>Text</dt><dd>${esc(it.element_text)}</dd>` : "";
    const tags = (it.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("");
    return `<div class="issue${active}" data-id="${it.id}" style="border-left-color:${c}">
      <div class="issue-head">
        <span class="issue-num" style="background:${c}">${it._num}</span>
        <span class="issue-title">${esc(it.title)}</span>
        <span class="badge" style="background:${c}">${it.severity}</span>
      </div>
      <div class="issue-conf">type: ${esc(it.issue_type)} · conf ${(it.confidence||0).toFixed(2)}</div>
      <div class="issue-detail">
        <div>${esc(it.description || "")}</div>
        <dl>${role}${txt}${measured}${expected}</dl>
        <div class="tags">${tags}</div>
      </div>
    </div>`;
  }).join("");
  list.querySelectorAll(".issue").forEach((node) => {
    node.addEventListener("click", () => setActive(node.dataset.id));
  });
}

function renderOverlays() {
  clearOverlays();
  const wrap = $("#canvasWrap");
  const visible = state.issues.filter(
    (it) => !state.hiddenSev.has(it.severity) && it.element_bbox);
  visible.forEach((it) => {
    const c = SEV[it.severity]?.color || "#999";
    const ov = document.createElement("div");
    ov.className = "overlay";
    ov.dataset.id = it.id;
    ov.style.borderColor = c;
    ov.innerHTML = `<span class="marker" style="background:${c}">${it._num}</span>`;
    ov.addEventListener("click", () => setActive(it.id));
    wrap.appendChild(ov);
  });
  positionOverlays();
}

function positionOverlays() {
  const img = $("#screenshot");
  if (!img.naturalWidth) return;
  const ratio = img.clientWidth / img.naturalWidth;
  document.querySelectorAll(".overlay").forEach((ov) => {
    const it = state.issues.find((x) => x.id === ov.dataset.id);
    if (!it || !it.element_bbox) return;
    const b = it.element_bbox;
    ov.style.left = (b.x * ratio) + "px";
    ov.style.top = (b.y * ratio) + "px";
    ov.style.width = (b.w * ratio) + "px";
    ov.style.height = (b.h * ratio) + "px";
  });
}

function setActive(id) {
  state.activeId = (state.activeId === id) ? null : id;
  renderResults();
  document.querySelectorAll(".overlay").forEach((ov) => {
    ov.classList.toggle("active", ov.dataset.id === state.activeId);
  });
  if (state.activeId) {
    const node = document.querySelector(`.issue[data-id="${state.activeId}"]`);
    if (node) node.scrollIntoView({ behavior: "smooth", block: "nearest" });
    const ov = document.querySelector(`.overlay[data-id="${state.activeId}"]`);
    if (ov) ov.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function clearOverlays() {
  document.querySelectorAll(".overlay").forEach((o) => o.remove());
}

function showBanner(msg) {
  const b = $("#banner");
  b.textContent = msg; b.className = "banner error";
}
// kind: "error" | "warn" — content là HTML đã escape ở caller
function showBannerHtml(kind, html) {
  const b = $("#banner");
  b.innerHTML = html;
  b.className = "banner " + (kind === "warn" ? "warn" : "error");
}
function clearBanner() {
  const b = $("#banner");
  b.textContent = ""; b.className = "hidden";
}
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

document.addEventListener("DOMContentLoaded", init);
