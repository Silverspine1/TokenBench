"use strict";
// Dependency-free canvas chart renderer for TokenBench. Supports multi-series
// line and grouped-bar charts over a categorical/ordinal X axis, with axes,
// gridlines, legend, and hover tooltips. No external libraries.

const PALETTE = [
  "#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#475569", "#ea580c",
];

function niceCeil(v) {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / mag;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * mag;
}

class Chart {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.hover = null;
    canvas.addEventListener("mousemove", (e) => this._onMove(e));
    canvas.addEventListener("mouseleave", () => { this.hover = null; this._draw(); });
  }

  // payload: {type, metric_label, mode, series:[{condition, points:[{x,label,value}]}], xLabels:[...]}
  render(payload) {
    this.payload = payload;
    this._layout();
    this._draw();
  }

  _layout() {
    const p = this.payload;
    // Distinct x labels in order. time-mode: max length sequence; task-mode: shared.
    let labels = p.xLabels;
    if (!labels) {
      const n = Math.max(0, ...p.series.map((s) => s.points.length));
      labels = [];
      for (let i = 0; i < n; i++) {
        const any = p.series.find((s) => s.points[i]);
        labels.push(any ? any.points[i].label : String(i + 1));
      }
    }
    this.labels = labels;

    let max = 0, min = 0;
    p.series.forEach((s) => s.points.forEach((pt) => {
      if (pt.value == null) return;
      if (pt.value > max) max = pt.value;
      if (pt.value < min) min = pt.value;
    }));
    this.yMax = niceCeil(max || 1);
    this.yMin = min < 0 ? -niceCeil(-min) : 0;
  }

  _plot() {
    const pad = { l: 64, r: 20, t: 20, b: 78 };
    return {
      x: pad.l, y: pad.t,
      w: this.canvas.width - pad.l - pad.r,
      h: this.canvas.height - pad.t - pad.b,
    };
  }

  _xFor(i, area) {
    const n = this.labels.length;
    if (n <= 1) return area.x + area.w / 2;
    return area.x + (area.w * i) / (n - 1);
  }
  _xBand(i, area) {
    const n = this.labels.length || 1;
    const band = area.w / n;
    return area.x + band * i + band / 2;
  }
  _yFor(v, area) {
    const range = this.yMax - this.yMin || 1;
    return area.y + area.h - ((v - this.yMin) / range) * area.h;
  }

  _draw() {
    const ctx = this.ctx, p = this.payload, area = this._plot();
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (!p || !p.series.length) {
      ctx.fillStyle = "#6b7280";
      ctx.fillText("No data — pick a metric and conditions, then Draw.", 20, 30);
      return;
    }
    ctx.font = "12px system-ui, sans-serif";

    // Y gridlines + labels.
    const ticks = 5;
    ctx.strokeStyle = "#e5e7eb"; ctx.fillStyle = "#6b7280"; ctx.textAlign = "right";
    for (let i = 0; i <= ticks; i++) {
      const v = this.yMin + ((this.yMax - this.yMin) * i) / ticks;
      const y = this._yFor(v, area);
      ctx.beginPath(); ctx.moveTo(area.x, y); ctx.lineTo(area.x + area.w, y); ctx.stroke();
      ctx.fillText(fmtNum(v), area.x - 8, y + 4);
    }
    // Axis title.
    ctx.save(); ctx.translate(14, area.y + area.h / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center"; ctx.fillStyle = "#374151";
    ctx.fillText(p.metric_label + (p.mode === "cumulative" ? " (cumulative)" : ""), 0, 0);
    ctx.restore();

    // X labels (rotated).
    ctx.save(); ctx.fillStyle = "#6b7280"; ctx.textAlign = "right";
    const showEvery = Math.ceil(this.labels.length / 24) || 1;
    this.labels.forEach((lab, i) => {
      if (i % showEvery !== 0) return;
      const x = p.type === "bar" ? this._xBand(i, area) : this._xFor(i, area);
      ctx.save(); ctx.translate(x, area.y + area.h + 12); ctx.rotate(-Math.PI / 4);
      ctx.fillText(shorten(lab, 18), 0, 0); ctx.restore();
    });
    ctx.restore();

    // Series.
    p.series.forEach((s, si) => {
      const color = PALETTE[si % PALETTE.length];
      if (p.type === "bar") this._bar(s, si, color, area);
      else this._line(s, color, area);
    });

    this._tooltip(area);
  }

  _line(s, color, area) {
    const ctx = this.ctx;
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    s.points.forEach((pt) => {
      if (pt.value == null) { started = false; return; }
      const x = this._xFor(pt.x - 1, area), y = this._yFor(pt.value, area);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    });
    ctx.stroke();
    s.points.forEach((pt) => {
      if (pt.value == null) return;
      const x = this._xFor(pt.x - 1, area), y = this._yFor(pt.value, area);
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    });
  }

  _bar(s, si, color, area) {
    const ctx = this.ctx, nS = this.payload.series.length, n = this.labels.length || 1;
    const band = area.w / n, bw = (band * 0.8) / nS;
    ctx.fillStyle = color;
    s.points.forEach((pt) => {
      if (pt.value == null) return;
      const cx = this._xBand(pt.x - 1, area);
      const x = cx - (band * 0.4) + si * bw;
      const y = this._yFor(pt.value, area), y0 = this._yFor(0, area);
      ctx.fillRect(x, Math.min(y, y0), bw, Math.abs(y0 - y));
    });
  }

  _onMove(e) {
    const r = this.canvas.getBoundingClientRect();
    const mx = (e.clientX - r.left) * (this.canvas.width / r.width);
    const my = (e.clientY - r.top) * (this.canvas.height / r.height);
    const area = this._plot();
    let best = null, bestD = 18 * 18;
    (this.payload?.series || []).forEach((s, si) => {
      s.points.forEach((pt) => {
        if (pt.value == null) return;
        const x = this.payload.type === "bar" ? this._xBand(pt.x - 1, area) : this._xFor(pt.x - 1, area);
        const y = this._yFor(pt.value, area);
        const d = (x - mx) ** 2 + (y - my) ** 2;
        if (d < bestD) { bestD = d; best = { pt, s, si, x, y }; }
      });
    });
    this.hover = best; this._draw();
  }

  _tooltip(area) {
    if (!this.hover) return;
    const ctx = this.ctx, h = this.hover;
    const lines = [
      `${h.s.condition}`,
      `${h.pt.label}`,
      `${this.payload.metric_label}: ${fmtNum(h.pt.value)}`,
    ];
    ctx.font = "12px system-ui, sans-serif";
    const w = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 16;
    let bx = h.x + 10, by = h.y - 10 - lines.length * 16;
    if (bx + w > area.x + area.w) bx = h.x - w - 10;
    if (by < area.y) by = h.y + 10;
    ctx.fillStyle = "rgba(17,24,39,0.92)"; ctx.fillRect(bx, by, w, lines.length * 16 + 8);
    ctx.fillStyle = "#fff"; ctx.textAlign = "left";
    lines.forEach((l, i) => ctx.fillText(l, bx + 8, by + 16 + i * 16));
    ctx.fillStyle = PALETTE[h.si % PALETTE.length];
    ctx.beginPath(); ctx.arc(h.x, h.y, 4, 0, Math.PI * 2); ctx.fill();
  }
}

function fmtNum(v) {
  if (v == null) return "";
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (a >= 1e3) return (v / 1e3).toFixed(2) + "k";
  if (a < 1 && a > 0) return v.toFixed(4);
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}
function shorten(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }

window.TBChart = Chart;
window.TBPalette = PALETTE;
