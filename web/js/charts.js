/* charts.js - a hand-made line chart on <canvas> (no library needed, good JavaScript practice). */

const hexA = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
};

function drawForecastChart(canvas, rows, fc, tipEl) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const c = canvas.getContext('2d');
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, W, H);

  const hist = rows.slice(-48);
  const t0 = toMs(hist[0].t), tNow = toMs(hist[hist.length - 1].t), t1 = tNow + 24 * 3600e3;
  const peak = Math.max(...hist.map((r) => r.aqi), ...HORIZONS.map((h) => fc.horizons[h].high));
  const yMax = Math.min(500, Math.max(250, Math.ceil(peak / 50) * 50));
  const pad = { l: 42, r: 12, t: 12, b: 28 };
  const X = (t) => pad.l + ((t - t0) / (t1 - t0)) * (W - pad.l - pad.r);
  const Y = (v) => pad.t + (1 - v / yMax) * (H - pad.t - pad.b);
  const accent = colour(fc.current);

  // coloured AQI category bands in the background
  let lo = 0;
  for (const cat of CATEGORIES) {
    if (lo >= yMax) break;
    const hi = Math.min(cat.max, yMax);
    c.fillStyle = hexA(cat.colour, 0.08);
    c.fillRect(pad.l, Y(hi), W - pad.l - pad.r, Y(lo) - Y(hi));
    lo = cat.max;
  }
  // grid + y labels
  c.font = '11px system-ui, sans-serif'; c.textBaseline = 'middle'; c.textAlign = 'right';
  for (let v = 0; v <= yMax; v += 100) {
    c.strokeStyle = 'rgba(255,255,255,.08)'; c.beginPath(); c.moveTo(pad.l, Y(v)); c.lineTo(W - pad.r, Y(v)); c.stroke();
    c.fillStyle = 'rgba(255,255,255,.55)'; c.fillText(v, pad.l - 6, Y(v));
  }
  // x labels every 12 hours
  c.textAlign = 'center'; c.textBaseline = 'top';
  for (let t = Math.ceil(t0 / 43200e3) * 43200e3; t <= t1; t += 43200e3) {
    if (t < t0) continue;
    const iso = fmtT(t);
    c.fillStyle = 'rgba(255,255,255,.55)';
    c.fillText(iso.slice(11, 16) === '00:00' ? iso.slice(5, 10) : iso.slice(11, 16), X(t), H - pad.b + 8);
  }

  // observed line + soft area
  const pts = hist.map((r) => ({ x: X(toMs(r.t)), y: Y(r.aqi), text: `${r.t.replace('T', ' ')} - AQI ${r.aqi} (${category(r.aqi)})` }));
  const grad = c.createLinearGradient(0, pad.t, 0, H - pad.b);
  grad.addColorStop(0, hexA(accent, 0.35)); grad.addColorStop(1, hexA(accent, 0));
  c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)));
  c.lineTo(pts[pts.length - 1].x, Y(0)); c.lineTo(pts[0].x, Y(0)); c.closePath(); c.fillStyle = grad; c.fill();
  c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)));
  c.strokeStyle = accent; c.lineWidth = 2.5; c.lineJoin = 'round'; c.stroke();

  // "now" marker
  c.setLineDash([4, 4]); c.strokeStyle = 'rgba(255,255,255,.45)';
  c.beginPath(); c.moveTo(X(tNow), pad.t); c.lineTo(X(tNow), H - pad.b); c.stroke(); c.setLineDash([]);
  c.fillStyle = 'rgba(255,255,255,.7)'; c.textAlign = 'right'; c.textBaseline = 'top'; c.fillText('now ', X(tNow) - 2, pad.t + 2);

  // forecast: shaded range, dashed line, dots
  const fpts = [{ t: tNow, v: fc.current, lo: fc.current, hi: fc.current, cat: fc.category }]
    .concat(HORIZONS.map((h) => ({ t: tNow + h * 3600e3, v: fc.horizons[h].aqi, lo: fc.horizons[h].low, hi: fc.horizons[h].high, cat: fc.horizons[h].category, h })));
  c.beginPath();
  fpts.forEach((p, i) => (i ? c.lineTo(X(p.t), Y(p.hi)) : c.moveTo(X(p.t), Y(p.hi))));
  [...fpts].reverse().forEach((p) => c.lineTo(X(p.t), Y(p.lo)));
  c.closePath(); c.fillStyle = 'rgba(255,255,255,.12)'; c.fill();
  c.beginPath(); fpts.forEach((p, i) => (i ? c.lineTo(X(p.t), Y(p.v)) : c.moveTo(X(p.t), Y(p.v))));
  c.setLineDash([7, 5]); c.strokeStyle = '#ffffff'; c.lineWidth = 2.5; c.stroke(); c.setLineDash([]);
  for (const p of fpts.slice(1)) {
    c.beginPath(); c.arc(X(p.t), Y(p.v), 6, 0, 7); c.fillStyle = colour(p.v); c.fill(); c.strokeStyle = '#fff'; c.lineWidth = 2; c.stroke();
    pts.push({ x: X(p.t), y: Y(p.v), text: `+${p.h} h forecast - AQI ${p.v} (${p.cat}), range ${p.lo}-${p.hi}` });
  }

  // hover tooltip (listener added once; it reads the latest points)
  canvas._pts = pts;
  if (!canvas._bound) {
    canvas._bound = true;
    canvas.addEventListener('mousemove', (e) => {
      const r = canvas.getBoundingClientRect(), mx = e.clientX - r.left;
      let best = null;
      for (const p of canvas._pts) if (!best || Math.abs(p.x - mx) < Math.abs(best.x - mx)) best = p;
      if (best && Math.abs(best.x - mx) < 14) {
        tipEl.textContent = best.text; tipEl.style.display = 'block';
        tipEl.style.left = Math.min(best.x, canvas.clientWidth - 200) + 'px'; tipEl.style.top = Math.max(best.y - 44, 0) + 'px';
      } else tipEl.style.display = 'none';
    });
    canvas.addEventListener('mouseleave', () => { tipEl.style.display = 'none'; });
  }
}
