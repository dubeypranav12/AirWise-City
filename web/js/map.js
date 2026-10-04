/* map.js - Leaflet map with coloured zone markers.
   If Leaflet or the map tiles cannot load (offline), a simple SVG zone plot is drawn instead. */

let lmap = null, markerLayer = null;

function initMap(el) {
  if (typeof L === 'undefined') return;                       // Leaflet failed to load -> fallback plot
  lmap = L.map(el).setView([28.69, 77.4], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 18,
  }).addTo(lmap);
  markerLayer = L.layerGroup().addTo(lmap);
}

// points: [{name, lat, lon, value, current, pred6, category, dominant, trend}]
function updateMap(el, points, selected, onSelect) {
  if (!lmap) return renderFallbackMap(el, points, selected, onSelect);
  markerLayer.clearLayers();
  for (const p of points) {
    const m = L.circleMarker([p.lat, p.lon], {
      radius: 17, color: p.name === selected ? '#ffffff' : 'rgba(255,255,255,.55)', weight: p.name === selected ? 4 : 1.5,
      fillColor: colour(p.value), fillOpacity: 0.88,
    }).addTo(markerLayer);
    m.bindTooltip(String(p.value), { permanent: true, direction: 'center', className: 'aq-num' });
    m.bindPopup(`<b>${p.name}</b><br>Current AQI: ${p.current}<br>6-h forecast: ${p.pred6} (${category(p.pred6)})<br>` +
                `Dominant: ${p.dominant}<br>Trend: ${p.trend}`);
    m.on('click', () => onSelect(p.name));
  }
  setTimeout(() => lmap.invalidateSize(), 50);
}

function renderFallbackMap(el, points, selected, onSelect) {
  const lats = points.map((p) => p.lat), lons = points.map((p) => p.lon);
  const [la0, la1, lo0, lo1] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const X = (lo) => 60 + ((lo - lo0) / (lo1 - lo0 || 1)) * 480, Y = (la) => 300 - ((la - la0) / (la1 - la0 || 1)) * 260;
  el.innerHTML = `<svg viewBox="0 0 600 340" class="fallback-map">
    <text x="300" y="332" text-anchor="middle" class="fm-note">Offline: simple zone plot (the street map needs internet)</text>
    ${points.map((p) => `<g class="fm-zone" data-name="${p.name}">
      <circle cx="${X(p.lon)}" cy="${Y(p.lat)}" r="${p.name === selected ? 24 : 20}" fill="${colour(p.value)}" stroke="#fff" stroke-width="${p.name === selected ? 4 : 1.5}"/>
      <text x="${X(p.lon)}" y="${Y(p.lat) + 5}" text-anchor="middle" class="fm-num">${p.value}</text>
      <text x="${X(p.lon)}" y="${Y(p.lat) + 40}" text-anchor="middle" class="fm-name">${p.name}</text></g>`).join('')}
  </svg>`;
  el.querySelectorAll('.fm-zone').forEach((g) => g.addEventListener('click', () => onSelect(g.dataset.name)));
}
