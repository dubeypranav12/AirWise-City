/* aqi.js - Indian AQI (CPCB) calculation.
   Units: PM2.5, PM10, NO2, SO2, O3 in ug/m3; CO in mg/m3.
   NOTE: this is an HOURLY ESTIMATE. Official CPCB AQI uses 24-hour (and 8-hour) averages. */

// Top concentration of each of the 6 AQI bands, per pollutant.
const BAND_TOPS = {
  pm25: [30, 60, 90, 120, 250, 380],
  pm10: [50, 100, 250, 350, 430, 600],
  no2:  [40, 80, 180, 280, 400, 560],
  so2:  [40, 80, 380, 800, 1600, 2400],
  co:   [1.0, 2.0, 10, 17, 34, 50],
  o3:   [50, 100, 168, 208, 748, 1000],
};
const INDEX_TOPS = [50, 100, 200, 300, 400, 500];
const POLLUTANTS = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3'];
const LABELS = { pm25: 'PM2.5', pm10: 'PM10', no2: 'NO₂', so2: 'SO₂', co: 'CO', o3: 'Ozone' };
const UNITS  = { pm25: 'µg/m³', pm10: 'µg/m³', no2: 'µg/m³', so2: 'µg/m³', co: 'mg/m³', o3: 'µg/m³' };

const CATEGORIES = [
  { max: 50,    name: 'Good',         colour: '#2ecc71' },
  { max: 100,   name: 'Satisfactory', colour: '#e8d82a' },
  { max: 200,   name: 'Moderate',     colour: '#ff9f1c' },
  { max: 300,   name: 'Poor',         colour: '#ff4d4d' },
  { max: 400,   name: 'Very Poor',    colour: '#b45cff' },
  { max: 99999, name: 'Severe',       colour: '#c0182d' },
];

const isNum = (v) => typeof v === 'number' && !Number.isNaN(v);

// Linear interpolation: same job as numpy.interp in the Python version.
function interp(x, xs, ys) {
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) {
    if (x <= xs[i]) return ys[i - 1] + ((x - xs[i - 1]) * (ys[i] - ys[i - 1])) / (xs[i] - xs[i - 1]);
  }
  return ys[ys.length - 1];
}

function subIndex(pollutant, conc) {
  if (!isNum(conc) || conc < 0) return null;
  return interp(conc, [0, ...BAND_TOPS[pollutant]], [0, ...INDEX_TOPS]);
}

// Returns { aqi, dominant } using whichever pollutants are available.
function computeAqi(values) {
  let best = null, dom = null;
  for (const p of POLLUTANTS) {
    const s = subIndex(p, values[p]);
    if (s !== null && (best === null || s > best)) { best = s; dom = p; }
  }
  if (best === null) return { aqi: null, dominant: null };
  return { aqi: Math.min(Math.round(best), 500), dominant: dom };
}

function category(aqi) {
  if (!isNum(aqi)) return 'Unknown';
  return CATEGORIES.find((c) => aqi <= c.max).name;
}
function colour(aqi) {
  if (!isNum(aqi)) return '#888888';
  return CATEGORIES.find((c) => aqi <= c.max).colour;
}
