"use strict";

const state = { scenario: null, demands: [], quotes: [], result: null };
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const money = value => new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR" }).format(Number(value || 0)).replace("ZAR", "R");
const pct = value => `${(Number(value || 0) * 100).toFixed(1)}%`;
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

async function api(url, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") headers["X-CSRF-Token"] = csrfToken;
  const response = await fetch(url, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

function showToast(message, error = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast show${error ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.className = "toast", 3200);
}

function formObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function loadScenario(evaluateNow = true) {
  const id = document.getElementById("scenarioSelect").value;
  try {
    const payload = await api(`/api/scenarios/${id}`);
    state.scenario = payload.scenario;
    state.demands = payload.demands;
    state.quotes = payload.quotes;
    renderInputs();
    renderScenarioMeta();
    await loadPerformance();
    if (evaluateNow) await runEvaluation();
  } catch (error) { showToast(error.message, true); }
}

function renderScenarioMeta() {
  const s = state.scenario;
  document.getElementById("scenarioMeta").innerHTML = [
    s.product,
    `Window closes ${s.window_close}`,
    `${s.compatibility_days}-day compatibility`,
    `Service floor ${pct(s.minimum_fill_rate)} fill / ${pct(s.minimum_on_time_rate)} on-time`,
  ].map(item => `<span>${escapeHtml(item)}</span>`).join("");
}

async function runEvaluation() {
  const button = document.getElementById("runEvaluation");
  button.disabled = true;
  button.textContent = "Evaluating…";
  try {
    state.result = await api(`/api/scenarios/${state.scenario.id}/evaluate`, { method: "POST" });
    renderResult();
    showToast("Comparison completed and saved as an evaluation run.");
  } catch (error) {
    showToast(error.message, true);
    document.getElementById("decisionTitle").textContent = "Evaluation could not run";
    document.getElementById("decisionRationale").textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Run validated comparison";
  }
}

function renderResult() {
  const r = state.result;
  const recommendation = r.recommendation;
  const accepted = r.decision.startsWith("ACCEPT");
  document.getElementById("decisionTitle").textContent = r.decision.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  document.getElementById("decisionRationale").textContent = r.rationale;
  const badge = document.getElementById("decisionBadge");
  badge.textContent = accepted ? "Recommended" : r.decision === "REJECT_AGGREGATION" ? "Do not aggregate" : "No feasible option";
  badge.className = `status ${accepted ? "success" : "danger"}`;
  document.getElementById("recommendedCost").textContent = recommendation ? `${money(recommendation.landed_cost_per_kg)}/kg` : "—";
  document.getElementById("recommendedType").textContent = recommendation?.label || "No recommendation";

  const kpi = r.recommended_kpis;
  document.getElementById("kpiDemand").textContent = `${r.compatible_demand.quantity_kg.toFixed(0)} kg`;
  document.getElementById("kpiRetailers").textContent = `${r.compatible_demand.retailer_count} committed retailers`;
  document.getElementById("kpiCost").textContent = kpi ? money(kpi.landed_cost_per_kg) : "—";
  document.getElementById("kpiSaving").textContent = kpi ? `${kpi.saving_vs_baseline_pct.toFixed(1)}% vs recorded baseline` : "No option";
  document.getElementById("kpiLogistics").textContent = kpi ? money(kpi.logistics_cost_per_kg) : "—";
  document.getElementById("kpiTrips").textContent = kpi ? String(kpi.trips_avoided) : "—";
  document.getElementById("kpiDistance").textContent = kpi ? `${kpi.distance_change_km > 0 ? "+" : ""}${kpi.distance_change_km.toFixed(0)} km vs baseline` : "—";
  document.getElementById("kpiFill").textContent = kpi ? pct(kpi.expected_fill_rate) : "—";
  document.getElementById("baselineFill").textContent = `Baseline ${pct(r.baseline.fill_rate)}`;
  document.getElementById("kpiOnTime").textContent = kpi ? pct(kpi.expected_on_time_rate) : "—";
  document.getElementById("baselineOnTime").textContent = `Baseline ${pct(r.baseline.on_time_rate)}`;
  renderFeasibility(); renderOptions(); renderCostBars(); renderTradeoff();
  document.getElementById("rulesList").innerHTML = r.rules_applied.map(rule => `<li>${escapeHtml(rule)}</li>`).join("");
}

function renderFeasibility() {
  const byName = Object.fromEntries(state.quotes.map(q => [q.supplier_name, q]));
  const rows = state.result.supplier_feasibility;
  document.getElementById("feasibleCount").textContent = `${rows.filter(x => x.feasible).length} of ${rows.length} feasible`;
  document.getElementById("feasibleCount").className = `status ${rows.some(x => x.feasible) ? "success" : "danger"}`;
  document.getElementById("feasibilityRows").innerHTML = rows.map(item => {
    const q = byName[item.supplier_name];
    return `<tr><td><b>${escapeHtml(item.supplier_name)}</b></td><td>${escapeHtml(q.product)}</td><td>${q.capacity_kg} kg</td><td>${q.service_areas.map(escapeHtml).join(", ")}</td><td>${q.lead_time_days} days</td><td><span class="status ${item.feasible ? "success" : "danger"}">${item.feasible ? "Feasible" : "Blocked"}</span>${item.reasons.length ? `<span class="cell-detail">${item.reasons.map(escapeHtml).join("; ")}</span>` : ""}</td></tr>`;
  }).join("");
}

function evaluatedOptions() {
  const r = state.result;
  return [...r.collective_options, ...(r.coordinated_split_option ? [r.coordinated_split_option] : []), ...(r.individual_option ? [r.individual_option] : [])];
}

function renderOptions() {
  const recommendation = state.result.recommendation;
  document.getElementById("optionRows").innerHTML = evaluatedOptions().sort((a,b) => a.landed_cost_per_kg - b.landed_cost_per_kg).map(option => {
    const selected = recommendation && option.type === recommendation.type && Math.abs(option.total_cost - recommendation.total_cost) < .01;
    return `<tr class="${selected ? "recommended-row" : ""}"><td><b>${escapeHtml(option.label)}</b>${selected ? '<span class="cell-detail">Recommended</span>' : ""}</td><td>${option.suppliers.map(x => escapeHtml(x.supplier_name)).join(" + ")}</td><td>${money(option.total_cost)}</td><td><b>${money(option.landed_cost_per_kg)}</b></td><td>${money(option.logistics_cost_per_kg)}</td><td>${option.lead_time_days} days</td><td>${pct(option.expected_fill_rate)}</td><td>${option.saving_vs_baseline_pct.toFixed(1)}%</td></tr>`;
  }).join("") || '<tr><td colspan="8" class="empty-cell">No feasible options.</td></tr>';
}

function renderCostBars() {
  const r = state.result;
  const options = [{ label: "Recorded baseline", value: r.baseline.cost_per_kg, type: "baseline" }, ...evaluatedOptions().map(o => ({ label: o.label, value: o.landed_cost_per_kg, type: r.recommendation && o.type === r.recommendation.type && Math.abs(o.total_cost-r.recommendation.total_cost)<.01 ? "recommended" : "" }))];
  const max = Math.max(...options.map(o => o.value), 1);
  const el = document.getElementById("costBars"); el.className = "cost-bars";
  el.innerHTML = options.map(o => `<div class="cost-bar-row ${o.type}"><span>${escapeHtml(o.label)}</span><div class="cost-bar-track"><i class="cost-bar-fill" style="width:${(o.value/max)*100}%"></i></div><b>${money(o.value)}</b></div>`).join("");
}

function renderTradeoff() {
  const points = state.result.cost_responsiveness_tradeoff;
  const el = document.getElementById("tradeoffChart");
  if (!points.length) { el.className = "tradeoff-chart empty-state"; el.textContent = "No feasible options."; return; }
  const width=520,height=230,pad={l:45,r:18,t:18,b:36};
  const maxX=Math.max(...points.map(p=>p.lead_time_days),1),minY=Math.min(...points.map(p=>p.landed_cost_per_kg)),maxY=Math.max(...points.map(p=>p.landed_cost_per_kg));
  const spanY=Math.max(maxY-minY,1), x=v=>pad.l+(v/maxX)*(width-pad.l-pad.r), y=v=>height-pad.b-((v-(minY-spanY*.15))/(spanY*1.3))*(height-pad.t-pad.b);
  const grid=[0,.25,.5,.75,1].map(t=>`<line class="chart-grid" x1="${pad.l}" y1="${pad.t+t*(height-pad.t-pad.b)}" x2="${width-pad.r}" y2="${pad.t+t*(height-pad.t-pad.b)}"/>`).join("");
  const marks=points.map((p,i)=>`<g><circle class="chart-point ${p.recommended?'recommended':''}" cx="${x(p.lead_time_days)}" cy="${y(p.landed_cost_per_kg)}" r="${p.recommended?7:5}"><title>${escapeHtml(p.label)}: ${money(p.landed_cost_per_kg)}/kg, ${p.lead_time_days} days</title></circle><text class="chart-label" x="${x(p.lead_time_days)+7}" y="${y(p.landed_cost_per_kg)-7}">${i+1}</text></g>`).join("");
  el.className="tradeoff-chart"; el.innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Landed cost per kilogram versus lead time chart">${grid}<line class="chart-axis" x1="${pad.l}" y1="${height-pad.b}" x2="${width-pad.r}" y2="${height-pad.b}"/><line class="chart-axis" x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${height-pad.b}"/>${marks}<text class="chart-label" x="${width/2-20}" y="${height-8}">Lead time (days) →</text><text class="chart-label" transform="translate(11 ${height/2+28}) rotate(-90)">Landed cost / kg →</text></svg><div class="chart-key">${points.map((p,i)=>`${i+1}. ${escapeHtml(p.label)}`).join(" · ")}</div>`;
}

function renderInputs() {
  document.getElementById("demandRows").innerHTML = state.demands.map(d => {
    const baseline = (d.baseline_price_per_kg*d.quantity_kg+d.baseline_logistics_cost+d.baseline_handling_cost)/d.quantity_kg;
    const action = d.status === "withdrawn" ? `<button class="inline-btn" data-status-id="${d.id}" data-status="committed">Recommit</button>` : `<button class="inline-btn danger" data-status-id="${d.id}" data-status="withdrawn">Withdraw</button>`;
    return `<tr><td><b>${escapeHtml(d.retailer_name)}</b></td><td>${escapeHtml(d.area)}</td><td>${d.quantity_kg} kg</td><td>${d.required_date}</td><td><span class="status ${d.status==='committed'?'success':d.status==='withdrawn'?'danger':'warning'}">${escapeHtml(d.status)}</span></td><td>${money(baseline)}</td><td>${money(d.baseline_logistics_cost)}</td><td>${d.baseline_trips} / ${d.baseline_distance_km} km</td><td>${action}</td></tr>`;
  }).join("");
  document.getElementById("quoteRows").innerHTML = state.quotes.map(q => `<tr><td><b>${escapeHtml(q.supplier_name)}</b>${q.verified?'<span class="cell-detail">Verified</span>':''}</td><td>${q.capacity_kg} kg</td><td>${q.lead_time_days} days</td><td>${q.service_areas.map(escapeHtml).join(", ")}</td><td>${money(q.fixed_fulfilment_cost)} + ${money(q.variable_fulfilment_per_kg)}/kg</td><td>${q.price_tiers.map(t=>`${t.minimum_kg}kg: ${money(t.price_per_kg)}`).join("<br>")}</td><td>${pct(q.expected_fill_rate)} fill<br>${pct(q.expected_on_time_rate)} on-time</td></tr>`).join("");
  bindStatusButtons(); setFormDefaults();
}

function setFormDefaults() {
  if (!state.scenario) return;
  const required = new Date(`${state.scenario.window_close}T00:00:00Z`); required.setUTCDate(required.getUTCDate()+5);
  const demandForm=document.getElementById("demandForm"); demandForm.querySelector('[name="required_date"]').value=required.toISOString().slice(0,10);
  const performanceForm=document.getElementById("performanceForm"); performanceForm.querySelector('[name="due_date"]').value=required.toISOString().slice(0,10); performanceForm.querySelector('[name="delivered_date"]').value=required.toISOString().slice(0,10);
}

function bindStatusButtons() {
  document.querySelectorAll("[data-status-id]").forEach(button => button.addEventListener("click", async () => {
    try { await api(`/api/demands/${button.dataset.statusId}/status`, { method:"PATCH", body:JSON.stringify({status:button.dataset.status}) }); showToast(`Demand ${button.dataset.status}.`); await loadScenario(true); }
    catch(error){ showToast(error.message,true); }
  }));
}

async function loadPerformance() {
  try {
    const p=await api(`/api/scenarios/${state.scenario.id}/performance`); const el=document.getElementById("performanceSummary");
    if(!p.record_count){el.className="performance-summary empty-state";el.textContent="No completed-order data recorded for this scenario.";return;}
    el.className="performance-summary";el.innerHTML=[["Actual cost / kg",p.actual_cost_per_kg==null?"—":money(p.actual_cost_per_kg)],["Actual logistics / kg",p.actual_logistics_cost_per_kg==null?"—":money(p.actual_logistics_cost_per_kg)],["Actual fill rate",p.fill_rate==null?"—":pct(p.fill_rate)],["Actual on-time",p.on_time_rate==null?"—":pct(p.on_time_rate)],["Trips / distance",`${p.trips} / ${p.route_distance_km} km`]].map(([l,v])=>`<div><span>${l}</span><strong>${v}</strong></div>`).join("");
  } catch(error){showToast(error.message,true);}
}

document.querySelectorAll("[data-toggle]").forEach(button=>button.addEventListener("click",()=>document.getElementById(button.dataset.toggle).classList.toggle("hidden")));
document.getElementById("scenarioSelect").addEventListener("change",()=>loadScenario(true));
document.getElementById("runEvaluation").addEventListener("click",runEvaluation);
document.getElementById("demandForm").addEventListener("submit",async event=>{event.preventDefault();const f=formObject(event.currentTarget);const body={...f,scenario_id:state.scenario.id,product:state.scenario.product,status:"committed",baseline_fill_rate:Number(f.baseline_fill_rate_pct)/100,baseline_on_time_rate:Number(f.baseline_on_time_rate_pct)/100};delete body.baseline_fill_rate_pct;delete body.baseline_on_time_rate_pct;try{await api("/api/demands",{method:"POST",body:JSON.stringify(body)});event.currentTarget.reset();event.currentTarget.classList.add("hidden");showToast("Committed demand saved.");await loadScenario(true);}catch(error){showToast(error.message,true);}});
document.getElementById("quoteForm").addEventListener("submit",async event=>{event.preventDefault();const f=formObject(event.currentTarget);const body={...f,scenario_id:state.scenario.id,product:state.scenario.product,verified:true,expected_fill_rate:Number(f.expected_fill_rate_pct)/100,expected_on_time_rate:Number(f.expected_on_time_rate_pct)/100};delete body.expected_fill_rate_pct;delete body.expected_on_time_rate_pct;try{await api("/api/quotes",{method:"POST",body:JSON.stringify(body)});event.currentTarget.reset();event.currentTarget.classList.add("hidden");showToast("Supplier quotation saved.");await loadScenario(true);}catch(error){showToast(error.message,true);}});
document.getElementById("performanceForm").addEventListener("submit",async event=>{event.preventDefault();const body={...formObject(event.currentTarget),scenario_id:state.scenario.id};try{const result=await api("/api/performance",{method:"POST",body:JSON.stringify(body)});showToast(`Actual performance saved: ${pct(result.fill_rate)} fill rate.`);event.currentTarget.reset();setFormDefaults();await loadPerformance();}catch(error){showToast(error.message,true);}});

loadScenario(true);

