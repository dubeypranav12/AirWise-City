/* forecast.js - features + Linear Regression forecast that runs IN THE BROWSER.
   The coefficients were trained in Python (scripts/export_web_data.py) and saved in data/config.js. */

const HORIZONS = [6, 12, 24];
const POOR = 200; // AQI above this = Poor or worse

// ---- time helpers (times are strings like "2026-10-02T14:00", India time) ----
const toMs = (t) => Date.parse(t + ':00Z');
const fmtT = (ms) => new Date(ms).toISOString().slice(0, 16);
const addHours = (t, h) => fmtT(toMs(t) + h * 3600e3);

// Fill missing readings with the previous value (short gaps only matter here).
function fillGaps(rows) {
  const keys = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3', 'temp', 'humidity', 'wind', 'wind_dir'];
  const out = rows.map((r) => ({ ...r }));
  for (const k of keys) {
    let last = null;
    for (const r of out) { if (isNum(r[k])) last = r[k]; else if (last !== null) r[k] = last; }
    let next = null;                                   // fill leading gaps from the future
    for (let i = out.length - 1; i >= 0; i--) { if (isNum(out[i][k])) next = out[i][k]; else if (next !== null) out[i][k] = next; }
  }
  return out;
}

// Add aqi + dominant pollutant to every hourly row.
function enrich(rows) {
  return fillGaps(rows).map((r) => ({ ...r, ...computeAqi(r) }));
}

const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;

// Build the feature vector for the LAST row (must match feature_engineering.py exactly).
function buildFeatures(rows) {
  const i = rows.length - 1;
  if (i < 24) return null;                              // need 24 h of history
  const r = rows[i];
  const d = new Date(toMs(r.t));
  const hour = d.getUTCHours();
  const dow = (d.getUTCDay() + 6) % 7;                  // Monday = 0, like pandas
  const rad = (r.wind_dir * Math.PI) / 180;
  const aqi = rows.map((x) => x.aqi);
  const f = {
    pm25: r.pm25, pm10: r.pm10, no2: r.no2, so2: r.so2, co: r.co, o3: r.o3,
    temp: r.temp, humidity: r.humidity, wind: r.wind,
    wind_sin: Math.sin(rad), wind_cos: Math.cos(rad),
    hour_sin: Math.sin((2 * Math.PI * hour) / 24), hour_cos: Math.cos((2 * Math.PI * hour) / 24),
    dow, aqi: r.aqi,
    aqi_lag1: aqi[i - 1],
    aqi_avg3: mean(aqi.slice(i - 2, i + 1)),
    aqi_avg6: mean(aqi.slice(i - 5, i + 1)),
    aqi_roc3: aqi[i] - aqi[i - 3],
    pm25_roc3: r.pm25 - rows[i - 3].pm25,
    aqi_same_hour_yday: aqi[i - 24],
  };
  return { f, hour };
}

// Abramowitz-Stegun approximation of erf, for the probability estimate.
function erf(x) {
  const s = Math.sign(x); x = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * x);
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return s * y;
}
const normCdf = (x) => 0.5 * (1 + erf(x / Math.SQRT2));

// Plain-language "contributing factors" (statistical hints, NOT proven sources).
function explain(f, hour) {
  const r = [];
  if (f.pm25_roc3 > 8) r.push('PM2.5 increased over the previous three hours');
  if (f.aqi_roc3 > 20) r.push('AQI has been rising quickly');
  if (f.wind < 6) r.push('Wind speed is low, so pollutants are not dispersing');
  if (f.humidity > 70) r.push('High humidity is trapping fine particles');
  if (hour >= 15 && hour <= 20) r.push('Evening traffic period is approaching');
  else if (hour >= 6 && hour <= 9) r.push('Morning traffic period is under way');
  if (f.aqi > f.aqi_same_hour_yday + 25) r.push('AQI is higher than at the same hour yesterday');
  return r.length ? r : ['No strong short-term driver detected; conditions look steady'];
}

// Forecast for one zone. `rows` = hourly history WITH aqi (use enrich()).
function forecastZone(rows, model) {
  const cur = rows[rows.length - 1];
  const out = { current: cur.aqi, category: category(cur.aqi), horizons: {}, warning: '', reasons: [] };
  const built = buildFeatures(rows);
  const ok = built && model && model.features.every((k) => isNum(built.f[k]));
  if (!ok) out.warning = 'Not enough recent data for the model - showing "same as now" instead.';
  for (const h of HORIZONS) {
    let pred = cur.aqi, sd = 40;
    if (ok) {
      const m = model.horizons[h];
      pred = m.intercept;
      model.features.forEach((k, j) => { pred += m.coef[j] * built.f[k]; });
      sd = m.rmse;
    }
    pred = Math.min(500, Math.max(0, pred));
    out.horizons[h] = {
      aqi: Math.round(pred), category: category(pred),
      low: Math.round(Math.max(0, pred - 1.28 * sd)), high: Math.round(Math.min(500, pred + 1.28 * sd)),
      pPoor: 1 - normCdf((POOR - pred) / Math.max(sd, 1e-6)),
      time: addHours(cur.t, h),
    };
  }
  out.reasons = ok ? explain(built.f, built.hour) : ['Not enough history to explain the trend'];
  return out;
}
