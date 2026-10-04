/* app.js - connects everything: loads data, computes forecasts, fills the page, handles clicks. */

const $ = (id) => document.getElementById(id);
const cfg = window.AW_CONFIG;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const shortT = (t) => `${t.slice(8, 10)} ${MONTHS[+t.slice(5, 7) - 1]} ${t.slice(11, 16)}`;

const state = { mode: 'Demo', scenario: 'moderate_to_poor', zone: 'Indirapuram', metric: 'current',
                profile: 'Asthma patient', rows: {}, fc: {}, py: null, info: null };

/* ---------- small helpers ---------- */
function toast(msg) {
  const el = $('toast'); el.textContent = msg; el.classList.add('show');
  clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove('show'), 3500);
}
const pill = (aqi) => `<span class="pill" style="background:${colour(aqi)}">${category(aqi)}</span>`;
const last = (zone) => state.rows[zone][state.rows[zone].length - 1];
const zoneNames = () => Object.keys(cfg.zones);

/* ---------- load data + forecasts ---------- */
async function load() {
  $('statusLine').innerHTML = 'Loading data...';
  const d = await getData(state.mode, state.scenario);
  state.info = d; state.py = d.py;
  state.rows = {}; state.fc = {};
  for (const name of zoneNames()) {
    if (!d.rows[name] || !d.rows[name].length) continue;
    state.rows[name] = enrich(d.rows[name]);
    state.fc[name] = forecastZone(state.rows[name], cfg.model);
  }
  if (!state.rows[state.zone]) state.zone = Object.keys(state.rows)[0];
  renderAll();
}

/* ---------- renderers ---------- */
function renderStatus() {
  const i = state.info;
  $('statusLine').innerHTML = `Active mode: <b>${i.modeUsed}</b> &middot; ${i.message}` +
    (i.sample ? '<span class="tag warn">sample data - not real measurements</span>' : '');
  document.querySelectorAll('#modeBtns button').forEach((b) => b.classList.toggle('active', b.dataset.mode === i.modeUsed));
  $('scenario').style.display = i.modeUsed === 'Demo' ? '' : 'none';
}

function renderOverview() {
  const z = state.zone, now = last(z), fc = state.fc[z], col = colour(now.aqi);
  document.documentElement.style.setProperty('--accent', col);        // whole page takes the AQI colour
  $('gaugeNum').textContent = now.aqi;
  $('gaugeArc').style.strokeDashoffset = 527.8 * (1 - Math.min(now.aqi, 500) / 500);
  $('ovZone').textContent = z + ' - Ghaziabad / Delhi NCR';
  $('gaugeCat').textContent = category(now.aqi); $('gaugeCat').style.background = col;
  $('ovDominant').textContent = LABELS[now.dominant] || 'n/a';
  $('ovUpdated').textContent = shortT(now.t);
  const p6 = fc.horizons[6], delta = p6.aqi - now.aqi;
  $('ovForecast').textContent = `${p6.aqi} (${p6.category}) ${delta >= 0 ? '+' : ''}${delta}`;

  const ban = $('ovBanner');
  const bad = ['Poor', 'Very Poor', 'Severe'].includes(p6.category);
  ban.classList.toggle('hidden', !bad && !fc.warning);
  ban.classList.toggle('amber', !bad);
  ban.innerHTML = bad ? `<b>Heads up:</b> air is predicted to reach <b>${p6.category}</b> within 6 hours. Open the Health advisor for precautions.` : fc.warning;

  $('pollGrid').innerHTML = POLLUTANTS.map((p) => {
    const v = now[p], s = subIndex(p, v);
    return `<div class="tile"><span>${LABELS[p]}</span><b>${isNum(v) ? v.toFixed(p === 'co' ? 2 : 1) : 'n/a'}</b> <small>${UNITS[p]}</small>
      <div class="bar"><i style="width:${Math.min(100, (s || 0) / 5)}%;background:${colour(s)}"></i></div></div>`;
  }).join('');
  $('wxGrid').innerHTML = [['Temperature', now.temp, '°C'], ['Humidity', now.humidity, '%'], ['Wind speed', now.wind, 'km/h']]
    .map(([n, v, u]) => `<div class="tile"><span>${n}</span><b>${isNum(v) ? v.toFixed(1) : 'n/a'}</b> <small>${u}</small></div>`).join('');
}

function renderForecast() {
  const z = state.zone, now = last(z), fc = state.fc[z];
  $('fcZone').textContent = '- ' + z;
  const cards = [`<div class="fc-card" style="--c:${colour(now.aqi)}"><div class="h">Now</div><div class="v">${now.aqi}</div>${pill(now.aqi)}</div>`];
  for (const h of HORIZONS) {
    const r = fc.horizons[h];
    cards.push(`<div class="fc-card" style="--c:${colour(r.aqi)}"><div class="h">In ${h} hours <span class="muted">(${shortT(r.time)})</span></div>
      <div class="v">${r.aqi}</div>${pill(r.aqi)}
      <div class="r">Likely range ${r.low}-${r.high}</div>
      <div class="r">Chance of Poor or worse: <b>${Math.round(r.pPoor * 100)}%</b></div><div class="prob"><i style="width:${Math.round(r.pPoor * 100)}%"></i></div></div>`);
  }
  $('fcCards').innerHTML = cards.join('');
  drawForecastChart($('fcChart'), state.rows[z], fc, $('chartTip'));
  $('fcReasons').innerHTML = fc.reasons.map((r) => `<li>${r}</li>`).join('');

  const m6 = cfg.model.metrics[6], pyF = state.py && state.py[z];
  $('fcModelNote').innerHTML =
    `Model: <b>Linear Regression</b> trained in Python, running in your browser. On held-out test data its 6-hour error was ` +
    `<b>${m6.linear_test.MAE.toFixed(1)} AQI points</b> versus ${m6.persistence_test.MAE.toFixed(1)} for the "same as now" baseline` +
    (cfg.dataSource === 'synthetic' ? ' <span class="tag warn">measured on SAMPLE data - retrain on real data before quoting</span>' : '') +
    `.<br><br>The range is the forecast &plusmn; 1.28 &times; validation RMSE (about 80%); the Poor+ chance assumes roughly normal errors.` +
    (pyF ? `<br><br>Python ${pyF.model} forecast for comparison: 6 h <b>${pyF['6']}</b>, 12 h <b>${pyF['12']}</b>, 24 h <b>${pyF['24']}</b>.` : '');
}

function mapPoints() {
  return zoneNames().filter((n) => state.rows[n]).map((n) => {
    const now = last(n), p6 = state.fc[n].horizons[6].aqi, diff = p6 - now.aqi;
    return { name: n, lat: cfg.zones[n].lat, lon: cfg.zones[n].lon, current: now.aqi, pred6: p6,
             value: state.metric === 'current' ? now.aqi : p6, dominant: LABELS[now.dominant] || 'n/a', dom: now.dominant,
             trend: diff > 15 ? 'Rising' : diff < -15 ? 'Falling' : 'Steady' };
  });
}

function renderMap() {
  const pts = mapPoints();
  updateMap($('map'), pts, state.zone, selectZone);
  const rows = [...pts].sort((a, b) => b.pred6 - a.pred6);
  document.querySelector('#zoneTable tbody').innerHTML = rows.map((p) =>
    `<tr class="click ${p.name === state.zone ? 'sel' : ''}" data-zone="${p.name}"><td><i class="dot" style="background:${colour(p.value)}"></i>${p.name}</td>
     <td>${p.current}</td><td>${p.pred6}</td><td>${p.trend === 'Rising' ? '&#9650;' : p.trend === 'Falling' ? '&#9660;' : '&#9644;'} ${p.trend}</td></tr>`).join('');
  document.querySelectorAll('#zoneTable tr.click').forEach((tr) => tr.addEventListener('click', () => selectZone(tr.dataset.zone)));
  const s = pts.find((p) => p.name === state.zone);
  $('mapDetail').innerHTML = `<b>${s.name}</b> - now ${s.current}, 6-h forecast ${s.pred6} ${pill(s.pred6)}<br>Dominant: ${s.dominant} &middot; Trend: ${s.trend}` +
    `<br><span class="muted">Suggested action:</span> ${authorityActions(s.pred6, s.dom).slice(0, 2).join('; ')}`;
}

function advisorAqi() {
  const h = +$('whenSel').value, fc = state.fc[state.zone];
  return h === 0 ? fc.current : fc.horizons[h].aqi;
}
function renderAdvisor() {
  $('profileChips').innerHTML = PROFILES.map((p) => `<button class="chip ${p === state.profile ? 'active' : ''}" data-p="${p}">${p}</button>`).join('');
  document.querySelectorAll('#profileChips .chip').forEach((b) => b.addEventListener('click', () => { state.profile = b.dataset.p; renderAdvisor(); }));
  const aqi = advisorAqi();
  $('advAqi').textContent = aqi; $('advAqi').style.color = colour(aqi);
  $('advCat').textContent = category(aqi); $('advCat').style.background = colour(aqi);
  $('advList').innerHTML = healthAdvice(state.profile, aqi).map((t) => `<li>${t}</li>`).join('');
  $('advDisclaimer').textContent = DISCLAIMER + ` (Advice for: ${state.profile}, ${state.zone})`;
}

function riskRows() {
  return zoneNames().filter((n) => state.rows[n]).map((n) => {
    const now = last(n), fc = state.fc[n], p6 = fc.horizons[6];
    const peakH = HORIZONS.reduce((a, h) => (fc.horizons[h].aqi > fc.horizons[a].aqi ? h : a), 6);
    return { zone: n, now: now.aqi, p6: p6.aqi, cat: p6.category, dom: now.dominant, change: p6.aqi - now.aqi,
             peak: shortT(fc.horizons[peakH].time), pPoor: Math.round(p6.pPoor * 100),
             affected: p6.aqi > 200 ? cfg.zones[n].pop : 0 };
  }).sort((a, b) => b.p6 - a.p6);
}

function renderAuthority() {
  const rows = riskRows();
  $('riskBody').innerHTML = rows.map((r) => `<tr><td><i class="dot" style="background:${colour(r.p6)}"></i>${r.zone}</td><td>${r.now}</td><td>${r.p6}</td>
    <td>${r.cat}</td><td>${LABELS[r.dom] || 'n/a'}</td><td>${r.change >= 0 ? '+' : ''}${r.change}</td><td>${r.peak}</td><td>${r.pPoor}%</td>
    <td>${r.affected ? r.affected.toLocaleString('en-IN') : '-'}</td></tr>`).join('');
  const worse = rows.filter((r) => r.change > 30);
  $('worseBanner').classList.toggle('hidden', !worse.length);
  $('worseBanner').innerHTML = '<b>Rapidly worsening:</b> ' + worse.map((r) => r.zone).join(', ');
  $('actionCards').innerHTML = rows.slice(0, 3).map((r) => `<div class="card act-card"><h4>${r.zone} - predicted ${r.p6} ${pill(r.p6)}</h4>
    <ul class="list">${authorityActions(r.p6, r.dom).map((a) => `<li>${a}</li>`).join('')}</ul></div>`).join('');
  renderAlertBox(); renderSim();
}

function alertText() {
  const z = $('alertZone').value, fc = state.fc[z], p6 = fc.horizons[6];
  return `AirWise City alert - ${z}\nCurrent AQI ${fc.current}. Predicted AQI in 6h: ${p6.aqi} (${p6.category}).\n` +
         `Main reason: ${fc.reasons[0]}\nGeneral guidance only - open the app for personalised advice.`;
}
function renderAlertBox() {
  const z = $('alertZone').value, thr = +$('alertThr').value, p6 = state.fc[z].horizons[6].aqi;
  $('alertThrVal').textContent = thr;
  $('alertMsg').textContent = alertText() + `\n\n${p6 >= thr ? 'THRESHOLD CROSSED' : 'Threshold not crossed'} (${p6} vs ${thr})`;
  let hist = []; try { hist = JSON.parse(localStorage.getItem('aw_alerts')) || []; } catch (e) { /* ignore */ }
  $('alertHist').innerHTML = hist.slice(0, 6).map((a) => `<li>${a.at} - ${a.zone}: predicted ${a.aqi}</li>`).join('') || '<li>No alerts sent yet.</li>';
}
function sendAlert() {
  const z = $('alertZone').value, text = alertText(), aqi = state.fc[z].horizons[6].aqi;
  let hist = []; try { hist = JSON.parse(localStorage.getItem('aw_alerts')) || []; } catch (e) { /* ignore */ }
  hist.unshift({ at: new Date().toLocaleString('en-IN'), zone: z, aqi });
  try { localStorage.setItem('aw_alerts', JSON.stringify(hist.slice(0, 20))); } catch (e) { /* ignore */ }
  if ('Notification' in window && Notification.permission === 'granted') new Notification('AirWise City alert - ' + z, { body: text });
  toast(`Alert sent for ${z}: predicted AQI ${aqi}`); renderAlertBox();
}

function renderSim() {
  const z = $('simZone').value, t = +$('simT').value / 100, d = +$('simD').value / 100, b = +$('simB').value / 100;
  $('simTv').textContent = Math.round(t * 100) + '%'; $('simDv').textContent = Math.round(d * 100) + '%'; $('simBv').textContent = Math.round(b * 100) + '%';
  const r = simulateScenario(last(z), t, d, b);
  $('simBase').textContent = r.baseline; $('simScen').textContent = r.scenario; $('simGain').textContent = r.improvementPct.toFixed(0) + '%';
}

function downloadCsv() {
  const head = ['Zone', 'Current AQI', 'Predicted AQI (6h)', 'Category (6h)', 'Dominant', 'Change (6h)', 'Expected peak', 'P(Poor+) %', 'Citizens potentially affected'];
  const lines = riskRows().map((r) => [r.zone, r.now, r.p6, r.cat, LABELS[r.dom], r.change, r.peak, r.pPoor, r.affected].join(','));
  const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'airwise_daily_report.csv'; a.click();
}

/* ---------- interactions ---------- */
function selectZone(name) { state.zone = name; $('zoneSelect').value = name; renderAll(); }

function renderAll() {
  renderStatus(); renderOverview(); renderForecast(); renderMap(); renderAdvisor(); renderAuthority();
}

function fillSelect(el, names, value) {
  el.innerHTML = names.map((n) => `<option>${n}</option>`).join(''); el.value = value;
}

function init() {
  const names = zoneNames();
  fillSelect($('zoneSelect'), names, state.zone);
  fillSelect($('alertZone'), names, state.zone); fillSelect($('simZone'), names, state.zone);
  $('catLegend').innerHTML = CATEGORIES.map((c) => `<span><i style="background:${c.colour}"></i>${c.name}</span>`).join('');
  initMap($('map'));

  document.querySelectorAll('#modeBtns button').forEach((b) => b.addEventListener('click', () => { state.mode = b.dataset.mode; load(); }));
  $('scenario').addEventListener('change', (e) => { state.scenario = e.target.value; load(); });
  $('refreshBtn').addEventListener('click', load);
  $('zoneSelect').addEventListener('change', (e) => selectZone(e.target.value));
  document.querySelectorAll('#metricBtns button').forEach((b) => b.addEventListener('click', () => {
    state.metric = b.dataset.metric;
    document.querySelectorAll('#metricBtns button').forEach((x) => x.classList.toggle('active', x === b)); renderMap();
  }));
  $('whenSel').addEventListener('change', renderAdvisor);
  ['alertThr', 'alertZone'].forEach((id) => $(id).addEventListener('input', renderAlertBox));
  $('alertBtn').addEventListener('click', sendAlert);
  $('notifyBtn').addEventListener('click', async () => {
    if (!('Notification' in window)) return toast('This browser does not support notifications.');
    const p = await Notification.requestPermission(); toast('Notifications: ' + p);
  });
  ['simZone', 'simT', 'simD', 'simB'].forEach((id) => $(id).addEventListener('input', renderSim));
  $('csvBtn').addEventListener('click', downloadCsv);
  window.addEventListener('resize', () => { if (state.rows[state.zone]) drawForecastChart($('fcChart'), state.rows[state.zone], state.fc[state.zone], $('chartTip')); });
  load();
}
document.addEventListener('DOMContentLoaded', init);
