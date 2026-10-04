/* advice.js - health advice, authority actions and the policy simulator. */

const PROFILES = ['General adult', 'Child', 'Elderly person', 'Asthma patient', 'Outdoor worker', 'Athlete'];
const DISCLAIMER = 'General informational guidance only - not medical advice or diagnosis.';

function healthAdvice(profile, aqi) {
  const sensitive = ['Child', 'Elderly person', 'Asthma patient'].includes(profile);
  const tips = [];
  if (aqi <= 50) return ['Air quality is good - normal outdoor activity is fine.'];
  if (aqi <= 100) {
    tips.push('Air is acceptable; unusually sensitive people may notice mild symptoms.');
    if (profile === 'Asthma patient') tips.push('Keep your prescribed medication within reach when outdoors.');
    return tips;
  }
  if (aqi <= 200) {
    tips.push(sensitive ? 'Limit long or intense outdoor exercise.' : 'Reduce prolonged heavy exertion outdoors.');
    if (profile === 'Asthma patient') tips.push('Keep prescribed medication available', 'Watch for breathlessness or wheezing');
    if (profile === 'Outdoor worker') tips.push('Take regular breaks in cleaner indoor air; consider an N95 mask.');
    return tips;
  }
  tips.push(`Air is ${category(aqi)}: avoid outdoor exercise during the peak period.`);
  tips.push('Close windows during the peak period; use an air purifier if available.');
  tips.push('Prefer outdoor activity between 8 AM and 10 AM, when air is usually cleaner.');
  if (profile === 'Asthma patient') tips.push('Keep prescribed medication available', "Follow your doctor's asthma action plan");
  if (profile === 'Child' || profile === 'Elderly person') tips.push('Keep outdoor time short; prefer indoor play/rest.');
  if (profile === 'Outdoor worker' || profile === 'Athlete')
    tips.push('Move training indoors or postpone it', 'Wear a well-fitted N95/FFP2 mask if you must be outside');
  if (aqi > 300) tips.push('Everyone should minimise outdoor exposure; seek medical help for severe symptoms.');
  return tips;
}

const AUTHORITY_ACTIONS = {
  pm10: ['Increase road-water sprinkling in construction-heavy areas', 'Enforce dust-control covers at construction sites'],
  pm25: ['Inspect and act on waste-burning reports', 'Deploy mobile monitoring units to confirm the hotspot'],
  no2:  ['Temporarily restrict heavy vehicles in the hotspot', 'Increase public-transport frequency'],
  co:   ['Manage traffic congestion at key junctions'],
  so2:  ['Check industrial emission compliance nearby'],
  o3:   ['Issue midday outdoor-activity advisory'],
};

// The system only RECOMMENDS. People decide and enforce.
function authorityActions(aqiPred, dominant) {
  const acts = [...(AUTHORITY_ACTIONS[dominant] || [])];
  if (aqiPred > 200) acts.push('Issue school outdoor-activity advisory');
  if (aqiPred > 300) acts.push('Consider temporary restrictions on heavy vehicles and construction activity',
                               'Activate public health alert for vulnerable groups');
  return acts.length ? acts : ['Continue routine monitoring'];
}

// ASSUMED shares of PM from each source (illustration only, not measured data).
const SOURCE_SHARES = { traffic: 0.35, construction_dust: 0.25, waste_burning: 0.15 };

function simulateScenario(row, trafficCut, dustCut, burnCut) {
  const f = 1 - (SOURCE_SHARES.traffic * trafficCut + SOURCE_SHARES.construction_dust * dustCut + SOURCE_SHARES.waste_burning * burnCut);
  const base = computeAqi(row).aqi;
  const scen = computeAqi({ ...row, pm25: row.pm25 * f, pm10: row.pm10 * f }).aqi;
  return { baseline: base, scenario: scen, improvementPct: base ? ((base - scen) / base) * 100 : 0 };
}
