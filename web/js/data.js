/* data.js - three data modes with automatic fallback:  Live (Open-Meteo)  ->  Cached  ->  Demo
   Every mode returns hourly rows per zone:
   { t:"2026-10-02T14:00", pm25, pm10, no2, so2, co(mg/m3), o3, temp, humidity, wind(km/h), wind_dir } */

const AQ_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality';
const WX_URL = 'https://api.open-meteo.com/v1/forecast';
const AQ_VARS = 'pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone';
const WX_VARS = 'temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m';
const CACHE_KEY = 'aw_live_cache';

// Current India time as "YYYY-MM-DDTHH:MM" (IST = UTC + 5:30).
const nowIST = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 16);

async function fetchJson(url, ms = 10000) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);          // give up after 10 seconds
  try {
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } finally { clearTimeout(timer); }
}

// Live data for ALL zones with just two requests (Open-Meteo accepts comma-separated coordinates).
async function fetchLive(zones) {
  const names = Object.keys(zones);
  const lat = names.map((n) => zones[n].lat).join(',');
  const lon = names.map((n) => zones[n].lon).join(',');
  const common = `latitude=${lat}&longitude=${lon}&timezone=Asia%2FKolkata&past_days=3&forecast_days=1`;
  const [aq, wx] = await Promise.all([
    fetchJson(`${AQ_URL}?${common}&hourly=${AQ_VARS}`),
    fetchJson(`${WX_URL}?${common}&hourly=${WX_VARS}`),
  ]);
  const aqs = Array.isArray(aq) ? aq : [aq];
  const wxs = Array.isArray(wx) ? wx : [wx];
  const cutoff = nowIST();
  const out = {};
  names.forEach((name, i) => {
    const a = aqs[i].hourly, w = wxs[i].hourly;
    const wIndex = new Map(w.time.map((t, j) => [t, j]));
    const rows = [];
    a.time.forEach((t, j) => {
      if (t > cutoff || !wIndex.has(t)) return;               // only hours that have already happened
      const k = wIndex.get(t);
      rows.push({
        t, pm25: a.pm2_5[j], pm10: a.pm10[j], no2: a.nitrogen_dioxide[j], so2: a.sulphur_dioxide[j],
        co: a.carbon_monoxide[j] == null ? null : a.carbon_monoxide[j] / 1000,   // ug/m3 -> mg/m3
        o3: a.ozone[j], temp: w.temperature_2m[k], humidity: w.relative_humidity_2m[k],
        wind: w.wind_speed_10m[k], wind_dir: w.wind_direction_10m[k],
      });
    });
    while (rows.length && rows[rows.length - 1].pm25 == null) rows.pop();      // drop hours not analysed yet
    out[name] = rows.slice(-72);
  });
  return out;
}

function readBrowserCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY)); } catch (e) { return null; }
}

// Returns { rows:{zone:[...]}, py:{zone:{...}}|null, modeUsed, message, updated, sample }
async function getData(mode, scenario) {
  const cfg = window.AW_CONFIG;
  let msg = '';
  if (mode === 'Live') {
    try {
      const rows = await fetchLive(cfg.zones);
      try { localStorage.setItem(CACHE_KEY, JSON.stringify({ savedAt: nowIST(), rows })); } catch (e) { /* storage full/blocked */ }
      return { rows, py: null, modeUsed: 'Live', message: 'Live data from Open-Meteo.', sample: false };
    } catch (err) {
      msg = 'Live API unavailable (' + (err.name === 'AbortError' ? 'timeout' : err.message) + '). ';
      mode = 'Cached';
    }
  }
  if (mode === 'Cached') {
    const saved = readBrowserCache();
    if (saved && saved.rows) {
      return { rows: saved.rows, py: null, modeUsed: 'Cached', message: msg + 'Showing your last live download (' + saved.savedAt + ').', sample: false };
    }
    if (window.AW_CACHED) {
      return { rows: window.AW_CACHED.history, py: window.AW_CACHED.pyForecast, modeUsed: 'Cached',
               message: msg + 'Showing data saved in data/cached.js.', sample: cfg.dataSource === 'synthetic' };
    }
    msg += 'No cache found. ';
  }
  const sc = window.AW_DEMO[scenario] || window.AW_DEMO.moderate_to_poor;
  return { rows: sc.history, py: sc.pyForecast, modeUsed: 'Demo', message: msg + `Replaying demo scenario "${scenario}".`, sample: true };
}
