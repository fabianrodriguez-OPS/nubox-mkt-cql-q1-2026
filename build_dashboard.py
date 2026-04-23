"""
Dashboard Marketing - CQL Low Touch 2026

Filtros base:
- pipeline = 17448034 (One Pipeline)
- xql_attribution_final = "Customer" (= Low Touch)
- dealtype IS NOT EMPTY (Tipo de negocio conocido)

Atribucion (toggle en UI):
- Por creacion: levantados y ganados se cuentan en el mes de createdate
- Por cierre: levantados por mes de createdate, ganados/UF por mes de closedate

Output: projects/CIA-Dashboard-MKT-CQL-Q12026/dashboard.html
"""
import os
import json
import datetime as dt
from pathlib import Path
import requests

TOKEN = os.environ["HUBSPOT_API_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
SEARCH_URL = "https://api.hubapi.com/crm/v3/objects/deals/search"

PIPELINE_ID = "17448034"
# Stages que el dashboard de HubSpot "CQL Equipo/negocio" cuenta como Ganado:
# - 17448040: Cerrado | Ganado
# - 213709702: Cerrado | Ganado Ejecutivo
# - 152925871: Intencion de No Venta (prob=1.0, isClosed=true â€” raro pero HubSpot lo incluye)
STAGES_WON = {"17448040", "213709702", "152925871"}
YEAR_START = "2026-01-01"
YEAR_END = "2027-01-01"
MONTHS = [f"2026-{m:02d}" for m in range(1, 13)]
MONTH_LABELS_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

ROOT = Path(__file__).resolve().parent
OUT_HTML = ROOT / "index.html"
OUT_JSON = ROOT / "data-snapshot.json"


def fetch_all_deals():
    base_filters = [
        {"propertyName": "pipeline", "operator": "EQ", "value": PIPELINE_ID},
        {"propertyName": "xql_attribution_final", "operator": "EQ", "value": "Customer"},
        {"propertyName": "dealtype", "operator": "HAS_PROPERTY"},
        {"propertyName": "createdate", "operator": "GTE", "value": YEAR_START},
        {"propertyName": "createdate", "operator": "LT", "value": YEAR_END},
    ]
    properties = ["dealname", "createdate", "closedate", "dealstage",
                  "dealtype", "amount_in_home_currency", "equipo_origen"]
    deals = []
    after = 0
    page = 0
    while True:
        page += 1
        body = {
            "filterGroups": [{"filters": base_filters}],
            "properties": properties,
            "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
            "limit": 200,
            "after": after,
        }
        r = requests.post(SEARCH_URL, headers=HEADERS, json=body, timeout=30)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("results", [])
        deals.extend(batch)
        print(f"  page {page}: +{len(batch)} (total {len(deals)} / {payload.get('total')})")
        paging = payload.get("paging", {}).get("next")
        if not paging:
            break
        after = paging["after"]
    return deals


def build_records(deals):
    """Convierte a lista compacta de registros para shipping al cliente."""
    recs = []
    equipos = set()
    dealtypes = set()
    for d in deals:
        p = d["properties"]
        created = (p.get("createdate") or "")[:7]
        closed = (p.get("closedate") or "")[:7]
        stage = p.get("dealstage")
        won = 1 if stage in STAGES_WON else 0
        equipo = p.get("equipo_origen") or "(sin equipo_origen)"
        dtype = p.get("dealtype") or "(sin tipo)"
        amount = float(p.get("amount_in_home_currency") or 0)
        equipos.add(equipo)
        dealtypes.add(dtype)
        recs.append({
            "e": equipo,
            "t": dtype,
            "cm": created,       # created month YYYY-MM
            "xm": closed if won else "",  # closed month (only si ganado)
            "w": won,
            "u": round(amount, 4) if won else 0,
        })
    return recs, sorted(equipos), sorted(dealtypes)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CQL Low Touch Â· 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
  :root {
    --bg: #0a0f1e;
    --bg-2: #0e152a;
    --card: #141c36;
    --card-2: #1a2347;
    --text: #e8ecf5;
    --muted: #8891aa;
    --border: #242d52;
    --lev: #5b8def;
    --gan: #7de2b4;
    --uf:  #ffb86b;
    --type: #b48cff;
    --shadow: 0 8px 24px rgba(0,0,0,0.25);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: radial-gradient(1200px 600px at 10% -10%, #13204a 0%, var(--bg) 60%) fixed;
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 32px 40px 48px;
    min-height: 100vh;
  }
  header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; gap: 24px; flex-wrap: wrap; }
  h1 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }
  .sub { color: var(--muted); font-size: 13px; margin-top: 6px; max-width: 720px; line-height: 1.5; }
  .brand { display: inline-flex; align-items: center; gap: 8px; padding: 4px 10px; background: var(--card); border: 1px solid var(--border); border-radius: 999px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
  .brand::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--gan); box-shadow: 0 0 8px var(--gan); }

  .filter-block { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; box-shadow: var(--shadow); }
  .filter-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 12px; flex-wrap: wrap; }
  .filter-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; }
  .filter-actions { display: flex; gap: 8px; }
  .btn-sm { background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 4px 10px; border-radius: 6px; font-size: 11px; cursor: pointer; font-family: inherit; font-weight: 500; transition: all 0.12s; }
  .btn-sm:hover { border-color: var(--lev); color: var(--text); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { cursor: pointer; user-select: none; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--border); background: var(--bg-2); color: var(--muted); font-size: 12px; font-weight: 500; transition: all 0.12s; white-space: nowrap; }
  .chip:hover { border-color: var(--lev); color: var(--text); }
  .chip.active { background: var(--lev); border-color: var(--lev); color: #fff; }
  .chip.active-gan { background: var(--gan); border-color: var(--gan); color: #0a0f1e; }

  .toggle-group { display: inline-flex; background: var(--bg-2); border: 1px solid var(--border); border-radius: 999px; padding: 3px; }
  .toggle-group button { background: transparent; border: none; color: var(--muted); padding: 6px 14px; border-radius: 999px; font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
  .toggle-group button.active { background: var(--lev); color: #fff; }

  .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
  .kpi { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px; box-shadow: var(--shadow); position: relative; overflow: hidden; }
  .kpi::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent, var(--lev)); }
  .kpi.lev { --accent: var(--lev); }
  .kpi.gan { --accent: var(--gan); }
  .kpi.uf  { --accent: var(--uf); }
  .kpi .label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
  .kpi .value { font-size: 34px; font-weight: 700; margin-top: 8px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .kpi.uf .value { color: var(--uf); }
  .kpi .hint { color: var(--muted); font-size: 12px; margin-top: 4px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .panel { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px; box-shadow: var(--shadow); }
  .panel.full { grid-column: 1 / -1; }
  .panel h3 { margin: 0 0 4px; font-size: 13px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
  .panel .subh { font-size: 11px; color: var(--muted); margin-bottom: 12px; opacity: 0.8; }
  .chart-wrap { position: relative; height: 320px; }
  .chart-wrap.tall { height: 420px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }
  th, td { padding: 10px 12px; text-align: right; border-bottom: 1px solid var(--border); }
  th:first-child, td:first-child { text-align: left; }
  th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
  tbody tr:hover { background: rgba(91,141,239,0.06); }
  tr.total td { font-weight: 700; border-top: 2px solid var(--border); border-bottom: none; background: var(--card-2); }
  tr.empty td { color: var(--muted); }

  .foot { color: var(--muted); font-size: 11px; margin-top: 24px; text-align: right; border-top: 1px solid var(--border); padding-top: 12px; }
  @media (max-width: 860px) {
    body { padding: 20px; }
    .kpis, .grid { grid-template-columns: 1fr; }
    .chart-wrap { height: 260px; }
    .chart-wrap.tall { height: 360px; }
  }
</style>
</head>
<body>
  <header>
    <div>
      <div class="brand">CUSTOMER INNOVATION Â· MKT</div>
      <h1 style="margin-top:10px;">CQL Low Touch Â· 2026</h1>
      <div class="sub">
        Negocios en <b>One Pipeline</b> con <b>XQL Attribution Final = Customer</b> y tipo de negocio conocido.
        Ganado = "Cerrado | Ganado" + "Cerrado | Ganado Ejecutivo" + "IntenciÃ³n de No Venta" (match HubSpot).
        UF = valor en divisa de la empresa.
      </div>
    </div>
  </header>

  <div class="filter-block">
    <div class="filter-header">
      <div class="filter-label">AtribuciÃ³n</div>
    </div>
    <div class="toggle-group" id="attr-toggle">
      <button data-mode="closed" class="active">Por Cierre (HubSpot)</button>
      <button data-mode="created">Por CreaciÃ³n</button>
    </div>
    <div class="subh" id="attr-desc" style="margin-top:8px;"></div>
  </div>

  <div class="filter-block">
    <div class="filter-header">
      <div class="filter-label">Equipo Origen</div>
      <div class="filter-actions">
        <button class="btn-sm" data-action="all-teams">Todos</button>
        <button class="btn-sm" data-action="none-teams">Ninguno</button>
      </div>
    </div>
    <div class="chips" id="chips-equipos"></div>
  </div>

  <div class="filter-block">
    <div class="filter-header">
      <div class="filter-label">Mes</div>
      <div class="filter-actions">
        <button class="btn-sm" data-action="all-months">Todos</button>
        <button class="btn-sm" data-action="ytd-months">YTD</button>
        <button class="btn-sm" data-action="none-months">Ninguno</button>
      </div>
    </div>
    <div class="chips" id="chips-months"></div>
  </div>

  <div class="kpis">
    <div class="kpi lev"><div class="label">Levantados</div><div class="value" id="kpi-lev">â€”</div><div class="hint" id="kpi-lev-hint"></div></div>
    <div class="kpi gan"><div class="label">Ganados</div><div class="value" id="kpi-gan">â€”</div><div class="hint" id="kpi-gan-hint"></div></div>
    <div class="kpi uf"><div class="label">UF Ganadas</div><div class="value" id="kpi-uf">â€”</div><div class="hint" id="kpi-uf-hint"></div></div>
  </div>

  <div class="grid">
    <div class="panel full">
      <h3>Levantados vs Ganados por mes</h3>
      <div class="subh" id="sub-counts"></div>
      <div class="chart-wrap"><canvas id="chart-counts"></canvas></div>
    </div>
    <div class="panel full">
      <h3>UF Ganadas por mes</h3>
      <div class="subh" id="sub-uf"></div>
      <div class="chart-wrap"><canvas id="chart-uf"></canvas></div>
    </div>
    <div class="panel full">
      <h3>DistribuciÃ³n por Tipo de Negocio (Ganados)</h3>
      <div class="subh">Cantidad y UF ganada de deals cerrados en los meses seleccionados.</div>
      <div class="chart-wrap tall"><canvas id="chart-dealtype"></canvas></div>
    </div>
    <div class="panel full">
      <h3>Detalle por mes</h3>
      <table id="tbl">
        <thead><tr><th>Mes</th><th>Levantados</th><th>Ganados</th><th>Conv %</th><th>UF Ganadas</th><th>UF / deal ganado</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div class="foot">Snapshot: <span id="ts"></span> Â· Fuente: HubSpot API Â· <span id="deal-count"></span> deals en 2026 Â· <span id="won-count"></span> ganados YTD</div>

<script>
const DATA = __DATA_JSON__;
const MONTHS = DATA.months;
const MONTH_LABELS = DATA.month_labels;
const EQUIPOS = DATA.equipos;
const DEALTYPES = DATA.dealtypes;
const RECS = DATA.records;

Chart.register(ChartDataLabels);

const fmtNum = n => new Intl.NumberFormat("es-CL").format(n);
const fmtUF  = n => new Intl.NumberFormat("es-CL",{maximumFractionDigits:1}).format(n);
const fmtPct = n => (isFinite(n) ? n.toFixed(1) : "0.0") + "%";

const state = {
  mode: "closed",
  equipos: new Set(EQUIPOS),
  months: new Set(DATA.months_with_data),
};

// Chips equipos
const chipsEquipos = document.getElementById("chips-equipos");
EQUIPOS.forEach(e => {
  const chip = document.createElement("span");
  chip.className = "chip active"; chip.textContent = e; chip.dataset.value = e;
  chip.addEventListener("click", () => {
    if (state.equipos.has(e)) { state.equipos.delete(e); chip.classList.remove("active"); }
    else { state.equipos.add(e); chip.classList.add("active"); }
    render();
  });
  chipsEquipos.appendChild(chip);
});

// Chips meses
const chipsMonths = document.getElementById("chips-months");
MONTHS.forEach((m, i) => {
  const chip = document.createElement("span");
  chip.className = state.months.has(m) ? "chip active-gan" : "chip";
  chip.textContent = MONTH_LABELS[i]; chip.dataset.value = m;
  chip.addEventListener("click", () => {
    if (state.months.has(m)) { state.months.delete(m); chip.classList.remove("active-gan"); }
    else { state.months.add(m); chip.classList.add("active-gan"); }
    render();
  });
  chipsMonths.appendChild(chip);
});

// Toggle attribution
document.querySelectorAll("#attr-toggle button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#attr-toggle button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.mode = btn.dataset.mode;
    render();
  });
});

// Action buttons
document.querySelectorAll("[data-action]").forEach(btn => {
  btn.addEventListener("click", () => {
    const a = btn.dataset.action;
    if (a === "all-teams") { state.equipos = new Set(EQUIPOS); setAllChips(chipsEquipos, true, "active"); }
    if (a === "none-teams") { state.equipos = new Set(); setAllChips(chipsEquipos, false, "active"); }
    if (a === "all-months") { state.months = new Set(MONTHS); setAllChips(chipsMonths, true, "active-gan"); }
    if (a === "ytd-months") { state.months = new Set(DATA.months_with_data); setSelectedChips(chipsMonths, DATA.months_with_data, "active-gan"); }
    if (a === "none-months") { state.months = new Set(); setAllChips(chipsMonths, false, "active-gan"); }
    render();
  });
});

function setAllChips(container, on, cls) {
  container.querySelectorAll(".chip").forEach(c => {
    if (on) c.classList.add(cls); else c.classList.remove(cls);
  });
}
function setSelectedChips(container, selectedValues, cls) {
  const set = new Set(selectedValues);
  container.querySelectorAll(".chip").forEach(c => {
    if (set.has(c.dataset.value)) c.classList.add(cls);
    else c.classList.remove(cls);
  });
}

// -------- Chart config --------
let chartCounts, chartUf, chartDealtype;
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = "#8891aa";
Chart.defaults.borderColor = "rgba(36,45,82,0.8)";

const commonScales = {
  x: { ticks: { color: "#8891aa" }, grid: { display: false } },
  y: { ticks: { color: "#8891aa" }, grid: { color: "rgba(36,45,82,0.5)" }, beginAtZero: true }
};
const tooltipStyle = {
  backgroundColor: "#0e152a", borderColor: "#242d52", borderWidth: 1, padding: 12,
  titleColor: "#e8ecf5", bodyColor: "#e8ecf5"
};

function render() {
  // Descripcion modo
  const modeDesc = state.mode === "created"
    ? "Levantados y Ganados se cuentan por mes de <b>creaciÃ³n</b> del deal (cohorte de creaciÃ³n)."
    : "Levantados por mes de <b>creaciÃ³n</b>; Ganados/UF por mes de <b>cierre</b> (view HubSpot dashboard).";
  document.getElementById("attr-desc").innerHTML = modeDesc;
  document.getElementById("sub-counts").innerHTML = state.mode === "created"
    ? "AtribuciÃ³n por creaciÃ³n â€” de lo creado en cada mes, cuÃ¡nto se ganÃ³."
    : "AtribuciÃ³n por cierre â€” ganados segÃºn el mes de cierre del deal.";
  document.getElementById("sub-uf").innerHTML = state.mode === "created"
    ? "UF de deals ganados, atribuida al mes de creaciÃ³n."
    : "UF de deals ganados, atribuida al mes de cierre.";

  const selectedMonths = MONTHS.filter(m => state.months.has(m));
  const selectedLabels = selectedMonths.map(m => MONTH_LABELS[MONTHS.indexOf(m)]);
  const monthSet = state.months;
  const equipoSet = state.equipos;

  // Aggregation por mes
  const per = {};
  selectedMonths.forEach(m => per[m] = { lev: 0, gan: 0, uf: 0 });

  // Para dealtype breakdown
  const perType = {};
  DEALTYPES.forEach(t => perType[t] = { gan: 0, uf: 0 });

  RECS.forEach(r => {
    if (!equipoSet.has(r.e)) return;

    // Levantados: siempre por createdate
    if (monthSet.has(r.cm) && per[r.cm]) per[r.cm].lev += 1;

    // Ganados: depende del modo
    if (r.w === 1) {
      const attrMonth = state.mode === "created" ? r.cm : r.xm;
      if (attrMonth && monthSet.has(attrMonth) && per[attrMonth]) {
        per[attrMonth].gan += 1;
        per[attrMonth].uf += r.u;
        perType[r.t].gan += 1;
        perType[r.t].uf += r.u;
      }
    }
  });

  const lev = selectedMonths.map(m => per[m].lev);
  const gan = selectedMonths.map(m => per[m].gan);
  const uf  = selectedMonths.map(m => per[m].uf);

  const totLev = lev.reduce((a,b)=>a+b,0);
  const totGan = gan.reduce((a,b)=>a+b,0);
  const totUf  = uf.reduce((a,b)=>a+b,0);
  const totConv = totLev ? (totGan/totLev*100) : 0;
  const ufPerWin = totGan ? (totUf/totGan) : 0;

  document.getElementById("kpi-lev").textContent = fmtNum(totLev);
  document.getElementById("kpi-gan").textContent = fmtNum(totGan);
  document.getElementById("kpi-uf").textContent  = fmtUF(totUf);
  document.getElementById("kpi-lev-hint").textContent = state.equipos.size + " equipo(s) Â· " + state.months.size + " mes(es)";
  document.getElementById("kpi-gan-hint").textContent = "conversiÃ³n " + fmtPct(totConv);
  document.getElementById("kpi-uf-hint").textContent  = totGan ? ("promedio " + fmtUF(ufPerWin) + " UF / win") : "â€”";

  // Tabla
  const tbody = document.querySelector("#tbl tbody");
  tbody.innerHTML = "";
  if (selectedMonths.length === 0) {
    const tr = document.createElement("tr");
    tr.className = "empty";
    tr.innerHTML = "<td colspan=6>Sin meses seleccionados</td>";
    tbody.appendChild(tr);
  } else {
    selectedMonths.forEach((m, i) => {
      const conv = lev[i] ? (gan[i]/lev[i]*100) : 0;
      const perWin = gan[i] ? (uf[i]/gan[i]) : 0;
      const tr = document.createElement("tr");
      if (lev[i] === 0 && gan[i] === 0) tr.className = "empty";
      tr.innerHTML = "<td>" + selectedLabels[i] + "</td>"
        + "<td>" + fmtNum(lev[i]) + "</td>"
        + "<td>" + fmtNum(gan[i]) + "</td>"
        + "<td>" + fmtPct(conv) + "</td>"
        + "<td>" + fmtUF(uf[i]) + "</td>"
        + "<td>" + fmtUF(perWin) + "</td>";
      tbody.appendChild(tr);
    });
    const trt = document.createElement("tr");
    trt.className = "total";
    trt.innerHTML = "<td>Total</td>"
      + "<td>" + fmtNum(totLev) + "</td>"
      + "<td>" + fmtNum(totGan) + "</td>"
      + "<td>" + fmtPct(totConv) + "</td>"
      + "<td>" + fmtUF(totUf) + "</td>"
      + "<td>" + fmtUF(ufPerWin) + "</td>";
    tbody.appendChild(trt);
  }

  // Datalabels helpers
  const dlCount = {
    color: "#ffffff", anchor: "end", align: "start", offset: -2,
    font: { weight: "600", size: 11 }, clamp: true,
    formatter: v => v > 0 ? fmtNum(v) : ""
  };
  const dlUF = Object.assign({}, dlCount, { formatter: v => v > 0 ? fmtUF(v) : "" });

  // Chart counts
  if (chartCounts) chartCounts.destroy();
  chartCounts = new Chart(document.getElementById("chart-counts"), {
    type: "bar",
    data: {
      labels: selectedLabels,
      datasets: [
        { label: "Levantados", data: lev, backgroundColor: "#5b8def", borderRadius: 6, maxBarThickness: 48, datalabels: dlCount },
        { label: "Ganados",    data: gan, backgroundColor: "#7de2b4", borderRadius: 6, maxBarThickness: 48,
          datalabels: Object.assign({}, dlCount, { color: "#0a0f1e" }) }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { color: "#e8ecf5", padding: 16, boxWidth: 12, usePointStyle: true, pointStyle: "rectRounded" } },
        tooltip: tooltipStyle,
        datalabels: dlCount
      },
      scales: commonScales
    }
  });

  // Chart UF
  if (chartUf) chartUf.destroy();
  chartUf = new Chart(document.getElementById("chart-uf"), {
    type: "bar",
    data: {
      labels: selectedLabels,
      datasets: [{ label: "UF Ganadas", data: uf, backgroundColor: "#ffb86b", borderRadius: 6, maxBarThickness: 48,
                   datalabels: Object.assign({}, dlUF, { color: "#0a0f1e" }) }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: Object.assign({}, tooltipStyle, { callbacks: { label: ctx => fmtUF(ctx.parsed.y) + " UF" } }),
        datalabels: dlUF
      },
      scales: commonScales
    }
  });

  // Chart dealtype (horizontal, ordered by count desc)
  const typeRows = DEALTYPES.map(t => ({ t, gan: perType[t].gan, uf: perType[t].uf }))
                             .filter(r => r.gan > 0)
                             .sort((a, b) => b.gan - a.gan);
  const tLabels = typeRows.map(r => r.t);
  const tGan = typeRows.map(r => r.gan);
  const tUf  = typeRows.map(r => r.uf);

  if (chartDealtype) chartDealtype.destroy();
  chartDealtype = new Chart(document.getElementById("chart-dealtype"), {
    type: "bar",
    data: {
      labels: tLabels,
      datasets: [
        {
          label: "Ganados", data: tGan, backgroundColor: "#7de2b4", borderRadius: 6, maxBarThickness: 28,
          datalabels: {
            color: "#0a0f1e", anchor: "end", align: "end", offset: 6,
            font: { weight: "700", size: 12 },
            formatter: (v, ctx) => {
              const ufVal = tUf[ctx.dataIndex];
              return v > 0 ? fmtNum(v) + "  Â·  " + fmtUF(ufVal) + " UF" : "";
            }
          }
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      layout: { padding: { right: 120 } },
      plugins: {
        legend: { display: false },
        tooltip: Object.assign({}, tooltipStyle, {
          callbacks: {
            label: ctx => {
              const g = ctx.parsed.x;
              const u = tUf[ctx.dataIndex];
              return fmtNum(g) + " ganados Â· " + fmtUF(u) + " UF";
            }
          }
        })
      },
      scales: {
        x: { ticks: { color: "#8891aa" }, grid: { color: "rgba(36,45,82,0.4)" }, beginAtZero: true },
        y: { ticks: { color: "#e8ecf5", font: { weight: "500" } }, grid: { display: false } }
      }
    }
  });
}

document.getElementById("ts").textContent = DATA.generated_at;
document.getElementById("deal-count").textContent = DATA.deal_count;
document.getElementById("won-count").textContent = DATA.won_count;
render();
</script>
</body>
</html>
"""


def main():
    print("Extrayendo deals 2026 (Customer / Low Touch)...")
    deals = fetch_all_deals()
    print(f"Total deals extraidos: {len(deals)}")

    records, equipos, dealtypes = build_records(deals)
    won_count = sum(r["w"] for r in records)

    months_with_data = sorted({r["cm"] for r in records if r["cm"] in MONTHS})

    snapshot = {
        "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "deal_count": len(deals),
        "won_count": won_count,
        "months": MONTHS,
        "month_labels": MONTH_LABELS_ES,
        "months_with_data": months_with_data,
        "equipos": equipos,
        "dealtypes": dealtypes,
        "records": records,
        "filters": {
            "pipeline_id": PIPELINE_ID,
            "pipeline_name": "One Pipeline",
            "xql_attribution_final": "Customer",
            "dealtype": "HAS_PROPERTY (Tipo de negocio conocido)",
            "stages_won": sorted(STAGES_WON),
            "stages_won_labels": ["Cerrado | Ganado", "Cerrado | Ganado Ejecutivo", "Intencion de No Venta"],
            "createdate_range": f"{YEAR_START} <= createdate < {YEAR_END}",
        },
    }
    OUT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot JSON: {OUT_JSON}")

    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(snapshot, ensure_ascii=False))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard HTML: {OUT_HTML} ({len(html):,} chars)")


if __name__ == "__main__":
    main()
