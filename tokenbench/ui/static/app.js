"use strict";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}
function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) {
    if (k === "text") e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  for (const kid of kids) e.append(kid);
  return e;
}
function copy(text) { navigator.clipboard && navigator.clipboard.writeText(text); }

// ---- Task queue page -------------------------------------------------------
async function initQueue() {
  const conds = await getJSON("/conditions");
  const sel = document.getElementById("condition_id");
  conds.forEach((c) => sel.append(el("option", { value: c.condition_id, text: c.condition_id })));

  const rows = await getJSON(`/suites/${encodeURIComponent(window.SUITE_ID)}/tasks`);
  const tbody = document.getElementById("task-rows");
  tbody.innerHTML = "";
  rows.forEach((t) => {
    const score = t.latest_score ? `${t.latest_score.final_score ?? ""}` : "";
    const start = el("button", { class: "btn primary", text: "Start" });
    start.onclick = () => startRun(t.task_rel);
    const view = t.latest_run_id
      ? el("a", { class: "btn", href: `/result/${t.latest_run_id}`, text: "Result" })
      : el("span", {});
    tbody.append(el("tr", {},
      el("td", { text: t.repo_id }),
      el("td", {}, el("code", { text: t.task_id })),
      el("td", { text: t.category }),
      el("td", { text: t.difficulty }),
      el("td", { text: t.status }),
      el("td", { text: score }),
      el("td", {}, start, document.createTextNode(" "), view),
    ));
  });
}
async function startRun(taskRel) {
  const body = {
    task_rel: taskRel,
    condition_id: document.getElementById("condition_id").value,
    ide_name: document.getElementById("ide_name").value,
    model_name: document.getElementById("model_name").value || "user-entered",
  };
  try {
    const r = await postJSON("/runs/manual/start", body);
    window.location = `/console/${r.run_id}`;
  } catch (e) { alert("Start failed: " + e.message); }
}

// ---- Run console page ------------------------------------------------------
async function initConsole() {
  const id = window.RUN_ID;
  const detail = await getJSON(`/runs/${id}`);
  document.getElementById("workspace_path").textContent =
    (detail.manual_ide && detail.manual_ide.workspace_path) || "";
  document.getElementById("status").textContent = detail.status;
  const visible = (detail.public && detail.public.visible_commands) || [];
  document.getElementById("visible").textContent = visible.join("\n") || "(none)";

  const p = await getJSON(`/runs/${id}/prompt`);
  document.getElementById("prompt").textContent = p.prompt;

  document.getElementById("copy-path").onclick = () =>
    copy(document.getElementById("workspace_path").textContent);
  document.getElementById("copy-prompt").onclick = () => copy(p.prompt);

  document.getElementById("submit").onclick = async () => {
    if (!confirm("Submit the workspace and run hidden tests?")) return;
    try {
      await postJSON(`/runs/${id}/submit`, {});
      window.location = `/result/${id}`;
    } catch (e) { alert("Submit failed: " + e.message); }
  };
}

// ---- Result page -----------------------------------------------------------
async function initResult() {
  const id = window.RUN_ID;
  const detail = await getJSON(`/results/${id}`);
  const box = document.getElementById("result");
  const s = detail.score;
  box.innerHTML = "";
  if (!s) {
    box.append(el("p", { class: "muted", text: "Not submitted yet." }));
  } else {
    box.append(
      el("p", {}, el("strong", { text: "Success: " }), document.createTextNode(s.success ? "yes" : "no")),
      el("p", {}, el("strong", { text: "Quality: " }), document.createTextNode(s.quality_score)),
      el("p", {}, el("strong", { text: "Final: " }), document.createTextNode(s.final_score)),
      el("p", {}, el("strong", { text: "Hidden: " }), document.createTextNode(`${s.hidden_tests.tests_passed}/${s.hidden_tests.tests_total}`)),
      el("p", {}, el("strong", { text: "Visible: " }), document.createTextNode(`${s.visible_tests.tests_passed}/${s.visible_tests.tests_total}`)),
      el("p", {}, el("strong", { text: "Status: " }), document.createTextNode(detail.status)),
    );
  }
  const form = document.getElementById("cost-form");
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    const num = (k) => (fd.get(k) === "" ? null : Number(fd.get(k)));
    const body = {
      cost_usd: num("cost_usd"),
      input_tokens: num("input_tokens"),
      output_tokens: num("output_tokens"),
      cache_read_tokens: num("cache_read_tokens"),
      cache_write_tokens: num("cache_write_tokens"),
      reasoning_tokens: num("reasoning_tokens"),
      total_tokens: num("total_tokens"),
      source: fd.get("source"),
      confidence: fd.get("confidence"),
      notes: fd.get("notes") || "",
    };
    try {
      const r = await postJSON(`/runs/${id}/cost`, body);
      document.getElementById("cost-result").textContent = JSON.stringify(r.provider_usage, null, 2);
    } catch (e) { alert("Cost attach failed: " + e.message); }
  };
}

// ---- Database admin page ---------------------------------------------------
let DB_STATE = { table: null, columns: [] };

async function initDatabase() {
  document.getElementById("rebuild").onclick = async () => {
    if (!confirm("Rebuild the DB from runs/? Overwrites manual edits.")) return;
    const r = await postJSON("/db/rebuild", {});
    alert(`Ingested ${r.run_dirs_scanned} run dir(s): runs=${r.runs} cost=${r.cost} manual=${r.manual} staged=${r.staged}`);
    await loadTables();
    if (DB_STATE.table) loadTable(DB_STATE.table);
  };
  await loadTables();
}

async function loadTables() {
  const tables = await getJSON("/db/tables");
  const box = document.getElementById("tables");
  box.innerHTML = "";
  tables.forEach((t) => {
    const b = el("button", { class: "btn", text: `${t.name} (${t.count})` });
    b.onclick = () => loadTable(t.name);
    box.append(b, document.createTextNode(" "));
  });
  if (!DB_STATE.table && tables.length) loadTable(tables[0].name);
}

async function loadTable(table) {
  const data = await getJSON(`/db/${table}`);
  DB_STATE = { table, columns: data.columns };
  document.getElementById("meta").textContent =
    `${table}: ${data.rows.length} row(s) shown. run_id is read-only (primary key).`;

  const thead = document.querySelector("#grid thead");
  const tbody = document.querySelector("#grid tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";

  const hr = el("tr");
  data.columns.forEach((c) => hr.append(el("th", { text: c })));
  hr.append(el("th", { text: "actions" }));
  thead.append(hr);

  data.rows.forEach((row) => tbody.append(rowEl(table, data.columns, row)));
}

function rowEl(table, columns, row) {
  const tr = el("tr");
  const inputs = {};
  columns.forEach((c) => {
    const td = el("td");
    if (c === "run_id") {
      td.append(el("code", { text: row[c] == null ? "" : String(row[c]) }));
    } else {
      const inp = el("input", { value: row[c] == null ? "" : String(row[c]) });
      inp.style.minWidth = "90px";
      inputs[c] = inp;
      td.append(inp);
    }
    tr.append(td);
  });
  const td = el("td");
  const save = el("button", { class: "btn", text: "Save" });
  save.onclick = async () => {
    const updates = {};
    for (const c in inputs) {
      const v = inputs[c].value;
      updates[c] = v === "" ? null : v;
    }
    try {
      const r = await postJSON("/db/update", { table, run_id: row.run_id, updates });
      save.textContent = r.changed ? "Saved" : "No change";
      setTimeout(() => (save.textContent = "Save"), 1200);
    } catch (e) { alert("Save failed: " + e.message); }
  };
  const del = el("button", { class: "btn", text: "Delete" });
  del.onclick = async () => {
    if (!confirm(`Delete ${table} row ${row.run_id}? (DB row only, run files kept)`)) return;
    try {
      await postJSON("/db/delete", { table, run_id: row.run_id });
      tr.remove();
    } catch (e) { alert("Delete failed: " + e.message); }
  };
  td.append(save, document.createTextNode(" "), del);
  tr.append(td);
  return tr;
}

// ---- Charts page -----------------------------------------------------------
let CHART_OBJ = null;
const CHART_SEL = new Set();

async function initCharts() {
  const opts = await getJSON("/charts/options");
  const metricSel = document.getElementById("metric");
  opts.metrics.forEach((m) =>
    metricSel.append(el("option", { value: m.key, text: m.label }))
  );
  // default to total tokens if available
  if (opts.metrics.some((m) => m.key === "total_tokens")) metricSel.value = "total_tokens";

  const condBox = document.getElementById("conditions");
  condBox.innerHTML = "";
  if (!opts.conditions.length) {
    condBox.append(el("span", { class: "muted", text: "No runs yet — run some, then Rebuild the DB." }));
  }
  opts.conditions.forEach((c) => {
    const b = el("button", { class: "btn", text: c });
    b.onclick = () => {
      if (CHART_SEL.has(c)) { CHART_SEL.delete(c); b.classList.remove("primary"); }
      else { CHART_SEL.add(c); b.classList.add("primary"); }
    };
    condBox.append(b, document.createTextNode(" "));
  });

  CHART_OBJ = new window.TBChart(document.getElementById("chart"));
  document.getElementById("draw").onclick = drawChart;
}

async function drawChart() {
  const metric = document.getElementById("metric").value;
  const mode = document.getElementById("mode").value;
  const x_mode = document.getElementById("x_mode").value;
  const agg = document.getElementById("agg").value;
  const type = document.getElementById("chart_type").value;
  const conds = [...CHART_SEL];

  const qs = new URLSearchParams({ metric, mode, x_mode, agg });
  if (conds.length) qs.set("conditions", conds.join(","));

  let data;
  try { data = await getJSON("/charts/data?" + qs.toString()); }
  catch (e) { alert("Chart failed: " + e.message); return; }

  const note = document.getElementById("chart-note");
  const flags = [];
  if (mode === "cumulative" && !data.additive)
    flags.push("note: cumulative of a non-additive metric (score/rate) is unusual");
  if (!data.series.length) flags.push("no data for this selection");
  note.textContent = flags.join(" · ");

  CHART_OBJ.render({
    type,
    metric_label: data.metric_label,
    mode: data.mode,
    series: data.series,
    xLabels: data.x_labels,
  });

  const legend = document.getElementById("legend");
  legend.innerHTML = "";
  data.series.forEach((s, i) => {
    const chip = el("span", { class: "legend-chip" });
    const sw = el("span", { class: "legend-swatch" });
    sw.style.background = window.TBPalette[i % window.TBPalette.length];
    chip.append(sw, document.createTextNode(" " + s.condition));
    legend.append(chip);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.CHARTS_PAGE) initCharts().catch((e) => alert(e.message));
  else if (window.DB_PAGE) initDatabase().catch((e) => alert(e.message));
  else if (window.SUITE_ID !== undefined) initQueue().catch((e) => alert(e.message));
  else if (window.RUN_ID !== undefined && document.getElementById("submit")) initConsole().catch((e) => alert(e.message));
  else if (window.RUN_ID !== undefined && document.getElementById("cost-form")) initResult().catch((e) => alert(e.message));
});
