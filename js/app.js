/* =============================================================
   NS 2026 Election Intelligence Dashboard — client script
   Loads /data/model_output.json and /data/intel.json and renders
   all 14 sections. Auto-refreshes every 5 minutes to pick up
   updates written by the daily cron job.
   ============================================================= */

const REFRESH_MS = 5 * 60 * 1000; // 5-minute client polling
const PARTY_LABELS = {
  PH: "Pakatan Harapan",
  BN: "Barisan Nasional",
  PN: "Perikatan Nasional (PAS/Wawasan)",
  BERSATU: "Bersatu (solo)",
  "BN+PN": "BN + PN pact",
  OTHER: "Others / IND"
};
const PARTY_ORDER = ["BN+PN", "PH", "BN", "PN", "BERSATU", "OTHER"];

// ---------- Theme toggle ----------
(function () {
  const t = document.querySelector('[data-theme-toggle]');
  const r = document.documentElement;
  let d = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'dark'; // default dark
  r.setAttribute('data-theme', d);
  t && t.addEventListener('click', () => {
    d = d === 'dark' ? 'light' : 'dark';
    r.setAttribute('data-theme', d);
    t.innerHTML = d === 'dark'
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
  });
})();

// ---------- Utilities ----------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const el = (tag, cls, txt) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
};
const fmtPct = (x, digits = 1) => (x * 100).toFixed(digits) + '%';
const fmtDate = iso => {
  try { return new Date(iso).toLocaleString('en-GB',
    { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'Asia/Kuala_Lumpur' }); }
  catch { return iso; }
};
const partyBadge = (p) => {
  const b = el('span', 'party-badge party-' + p);
  b.textContent = p;
  return b;
};
function ratingClass(r) {
  return { "Very Positive":"vp", "Positive":"p", "Neutral":"n", "Negative":"neg", "Very Negative":"vn" }[r] || "n";
}
function sentimentClass(s) {
  if (!s) return "sent-neu";
  if (s.startsWith("Very Pos") || s.startsWith("Positive")) return "sent-pos";
  if (s.startsWith("Very Neg") || s.startsWith("Negative")) return "sent-neg";
  return "sent-neu";
}

// ---------- Data load ----------
async function loadData() {
  const cacheBust = '?v=' + Date.now();
  const [m, i] = await Promise.all([
    fetch('data/model_output.json' + cacheBust).then(r => r.json()),
    fetch('data/intel.json' + cacheBust).then(r => r.json()),
  ]);
  return { model: m, intel: i };
}

// ---------- Renderers ----------
function renderMeta(model, intel) {
  const gen = intel.meta.generated_at || model.meta.generated_at;
  $('#last-updated').textContent = fmtDate(gen);
  const polling = new Date('2026-08-01T08:00:00+08:00');
  const now = new Date();
  const daysLeft = Math.max(0, Math.ceil((polling - now) / (1000 * 60 * 60 * 24)));
  $('#days-to-polling').textContent = daysLeft === 0 ? "Polling day" : daysLeft + ' day' + (daysLeft === 1 ? '' : 's') + ' to go';
  // Next update — assume 07:30 and 19:00 MYT
  const nextHours = [7.5, 19];
  const nowHrs = now.getHours() + now.getMinutes()/60;
  let nextH = nextHours.find(h => h > nowHrs);
  const nextDate = new Date(now);
  if (nextH == null) { nextH = nextHours[0]; nextDate.setDate(nextDate.getDate()+1); }
  nextDate.setHours(Math.floor(nextH), (nextH % 1) * 60, 0, 0);
  $('#next-update').textContent = fmtDate(nextDate);
  $('#n-sims').textContent = (model.meta.n_simulations || 10000).toLocaleString();
}

function renderExec(intel) {
  const e = intel.executive;
  const winner = e.predicted_winner_short || e.predicted_winner;
  const headlineHtml = e.headline
    ? `<span class="muted small" style="display:inline-block;margin-left:6px;">${e.headline}</span>`
    : '';
  $('#exec-headline').innerHTML =
    `Predicted winner: <span class="predicted-winner">${winner}</span> · ${e.probability_pct}%` +
    (headlineHtml ? ' ' + headlineHtml : '');
  $('#exec-subhead').textContent = e.subhead;
  $('#confidence-value').textContent = intel.meta.confidence_level || '—';
}

function renderGovProb(model, intel) {
  const gp = model.government_probability;
  const wrap = $('#gov-prob'); wrap.innerHTML = '';
  const items = Object.entries(gp)
    .map(([k,v]) => ({k, v}))
    .sort((a,b) => b.v - a.v);
  const partyClassMap = { 'PH':'PH', 'BN+PN':'BNPN', 'Hung/Other':'Hung' };
  for (const {k, v} of items) {
    const row = el('div', 'gov-prob-row');
    row.appendChild(el('div', '', k));
    const track = el('div', 'track');
    const fill = el('div', 'fill ' + (partyClassMap[k] || 'Hung'));
    fill.style.width = (v * 100) + '%';
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(el('div', 'num', fmtPct(v, 1)));
    wrap.appendChild(row);
  }
}

function renderSeatTable(model) {
  const tbody = $('#seat-table tbody'); tbody.innerHTML = '';
  const s = model.coalition_seat_stats;
  const order = ['BN+PN','PH','BN','PN','BERSATU'];
  const total = model.meta.n_simulations || 10000;
  for (const k of order) {
    if (!s[k]) continue;
    const row = el('tr');
    const nameTd = el('td');
    nameTd.appendChild(partyBadge(k));
    nameTd.appendChild(document.createTextNode(' ' + PARTY_LABELS[k]));
    row.appendChild(nameTd);
    row.appendChild(el('td', 'num', s[k].mean.toFixed(1)));
    row.appendChild(el('td', 'num', s[k].p10 + '–' + s[k].p90));
    row.appendChild(el('td', 'num', fmtPct(s[k].p_majority, 1)));
    // Distribution — mini bar showing p10-p90 range on 0-36 axis
    const distTd = el('td');
    const distWrap = el('div');
    distWrap.style.position = 'relative';
    distWrap.style.height = '10px';
    distWrap.style.background = 'var(--color-surface-offset)';
    distWrap.style.borderRadius = '999px';
    distWrap.style.overflow = 'hidden';
    const range = el('div');
    range.style.position = 'absolute';
    range.style.left = (s[k].p10 / 36 * 100) + '%';
    range.style.width = ((s[k].p90 - s[k].p10) / 36 * 100) + '%';
    range.style.height = '100%';
    range.style.background = 'var(--color-primary)';
    range.style.opacity = '0.4';
    const marker = el('div');
    marker.style.position = 'absolute';
    marker.style.left = (s[k].mean / 36 * 100) + '%';
    marker.style.top = '0'; marker.style.width = '2px'; marker.style.height = '100%';
    marker.style.background = 'var(--color-primary)';
    // Threshold marker at 19/36
    const thresh = el('div');
    thresh.style.position = 'absolute';
    thresh.style.left = (19/36*100) + '%';
    thresh.style.top = '-2px'; thresh.style.width = '1px'; thresh.style.height = 'calc(100% + 4px)';
    thresh.style.background = 'var(--color-red)';
    thresh.title = 'Majority threshold (19)';
    distWrap.append(range, marker, thresh);
    distTd.appendChild(distWrap);
    row.appendChild(distTd);
    tbody.appendChild(row);
  }
}

function renderHeatMap(model) {
  const wrap = $('#heat-grid'); wrap.innerHTML = '';
  const seats = model.seats.slice().sort((a,b) => a.code.localeCompare(b.code));
  for (const s of seats) {
    const cell = el('a', 'heat-cell leader-' + s.leader);
    cell.href = '#c-' + s.code;
    cell.appendChild(el('div', 'code', s.code + ' · ' + s.parl));
    cell.appendChild(el('div', 'name', s.name));
    const p = el('div', 'prob');
    p.innerHTML = `<span class="party-badge party-${s.leader}">${s.leader}</span> · ${fmtPct(s.leader_prob, 0)}`;
    cell.appendChild(p);
    const b = el('span', 'class-badge class-' + s.classification.replace(/ /g,'\\ '), s.classification);
    b.className = 'class-badge';
    b.style.cssText = ''; // rely on class list
    // Have to apply class manually because CSS class name can't have spaces
    b.classList.add('class-' + s.classification.replace(/ /g,'-'));
    cell.appendChild(b);
    wrap.appendChild(cell);
  }
}

function renderMomentum(intel) {
  const wrap = $('#momentum-grid'); wrap.innerHTML = '';
  for (const m of intel.momentum) {
    const c = el('div', 'momentum-card');
    const partyKey = m.party.split(' ')[0]; // "PN (PAS)" → PN
    c.appendChild((()=> { const p = el('div','party'); p.appendChild(partyBadge(partyKey)); const s = document.createElement('span'); s.textContent=' '+m.party; s.className='small muted'; p.appendChild(s); return p;})());
    const r = el('div', 'rating rating-' + ratingClass(m.rating), m.rating);
    c.appendChild(r);
    c.appendChild(el('div', 'small muted', m.drivers));
    wrap.appendChild(c);
  }
}

function renderSentiment(intel) {
  const wrap = $('#sentiment-grid'); wrap.innerHTML = '';
  for (const s of intel.sentiment) {
    const c = el('div', 'sentiment-cell');
    c.appendChild(el('div', 'sentiment-platform', s.platform));
    for (const p of ['PH','BN','PN','BERSATU']) {
      const r = el('div', 'sentiment-row');
      const l = el('span'); l.appendChild(partyBadge(p));
      const v = el('span', sentimentClass(s[p]), s[p] || '—');
      r.append(l, v);
      c.appendChild(r);
    }
    const note = el('div', 'xs muted', s.notes);
    note.style.marginTop = '8px';
    c.appendChild(note);
    wrap.appendChild(c);
  }
  // Coordinated flags in callout
  const flagsHtml = (intel.coordinated_flags || []).map(f => '• ' + f).join('<br>');
  if (flagsHtml) {
    const flagBox = el('div', 'callout');
    flagBox.style.marginTop = '16px';
    flagBox.innerHTML = '<strong>Coordinated activity flags:</strong><br>' + flagsHtml;
    wrap.parentElement.appendChild(flagBox);
  }
}

function renderDemographics(intel) {
  const wrap = $('#demo-list'); wrap.innerHTML = '';
  for (const d of intel.demographics) {
    const row = el('div', 'demo-row');
    row.appendChild(el('div', 'label', d.segment));
    // Bar
    const bar = el('div');
    bar.style.height = '10px';
    bar.style.borderRadius = '999px';
    bar.style.background = 'var(--color-surface-offset)';
    bar.style.overflow = 'hidden';
    bar.style.position = 'relative';
    const fill = el('div');
    fill.style.height = '100%';
    fill.style.width = d.lean_pct + '%';
    fill.style.background = d.lean.startsWith('BN') || d.lean.startsWith('PN') || d.lean.startsWith('BN/PN')
        ? 'var(--color-bn)' : (d.lean.startsWith('PH') ? 'var(--color-ph)' : 'var(--color-amber)');
    bar.appendChild(fill);
    row.appendChild(bar);
    // Right cell — lean label + driver
    const rt = el('div');
    rt.style.textAlign = 'right';
    rt.style.minWidth = '220px';
    rt.innerHTML = `<div style="font-weight:600;">${d.lean} · <span class="mono">${d.lean_pct}%</span></div>
      <div class="drivers">${d.drivers}</div>`;
    row.appendChild(rt);
    wrap.appendChild(row);
  }
}

function renderConstituencies(model) {
  const tbody = $('#constituency-table tbody'); tbody.innerHTML = '';
  const seats = model.seats.slice();
  for (const s of seats) {
    const row = el('tr');
    row.id = 'c-' + s.code;
    // Seat cell
    const seatTd = el('td');
    seatTd.innerHTML = `<strong>${s.code}</strong> · ${s.name}<div class="xs muted">${s.parl}</div>`;
    row.appendChild(seatTd);
    // 2023 winner
    const y23 = el('td');
    y23.appendChild(partyBadge(s.y2023_winner));
    row.appendChild(y23);
    // Leader now
    const leadTd = el('td');
    leadTd.appendChild(partyBadge(s.leader));
    row.appendChild(leadTd);
    row.appendChild(el('td', 'num', fmtPct(s.leader_prob, 0)));
    // Class
    const cls = el('td');
    const cb = el('span', 'class-badge class-' + s.classification.replace(/ /g,'-'), s.classification);
    cls.appendChild(cb);
    row.appendChild(cls);
    row.appendChild(el('td', 'small', s.contest));
    // Candidate
    const cand = el('td', 'small');
    const leaderCand = s.candidates.find(c => c.party === s.leader);
    cand.innerHTML = leaderCand
      ? `${leaderCand.name}${leaderCand.incumbent ? ' <span class="chip flat">incumbent</span>' : ''}${leaderCand.star ? ' <span class="chip up">star</span>' : ''}`
      : '—';
    row.appendChild(cand);
    tbody.appendChild(row);
  }
}

function renderNarrative(intel) {
  const up = $('#narrative-up'); up.innerHTML = '';
  for (const n of intel.narratives_up) {
    const i = el('div', 'narrative-item trending-up');
    i.innerHTML = `<div><strong>${n.title}</strong> · <span class="chip up">impact: ${n.impact}</span></div><div class="small muted" style="margin-top:4px;">${n.note}</div>`;
    up.appendChild(i);
  }
  const dn = $('#narrative-down'); dn.innerHTML = '';
  for (const n of intel.narratives_down) {
    const i = el('div', 'narrative-item trending-down');
    i.innerHTML = `<div><strong>${n.title}</strong> · <span class="chip down">impact: ${n.impact}</span></div><div class="small muted" style="margin-top:4px;">${n.note}</div>`;
    dn.appendChild(i);
  }
}

function renderCandidates(intel) {
  const wrap = $('#candidate-list'); wrap.innerHTML = '';
  for (const c of intel.candidates) {
    const item = el('div', 'candidate-item');
    item.innerHTML = `<div><strong>${c.name}</strong> · ${(function(){const s=document.createElement('span'); s.className='party-badge party-' + c.party.split('-')[0]; s.textContent = c.party.split('-')[0]; return s.outerHTML;})()} · <span class="mono small">${c.seat}</span></div><div class="small muted" style="margin-top:6px;">${c.note}</div>`;
    wrap.appendChild(item);
  }
}

function renderRisks(intel) {
  const wrap = $('#risk-list'); wrap.innerHTML = '';
  for (const r of intel.risks) {
    const item = el('div', 'risk-item ' + r.level);
    item.innerHTML = `<div><strong>${r.title}</strong> · <span class="chip flat">Impact: ${r.impact_seats} seats</span> · <span class="chip ${r.level === 'high' ? 'down' : (r.level === 'med' ? 'flat' : 'up')}">${r.level.toUpperCase()}</span></div><div class="small muted" style="margin-top:4px;">${r.note}</div>`;
    wrap.appendChild(item);
  }
}

function renderPolls(intel) {
  const tbody = $('#poll-table tbody'); tbody.innerHTML = '';
  for (const p of intel.polls) {
    const row = el('tr');
    row.appendChild(el('td', '', p.source));
    row.appendChild(el('td', 'small mono', p.date));
    row.appendChild(el('td', 'small', p.method));
    row.appendChild(el('td', 'num small', p.reliability));
    row.appendChild(el('td', 'small', p.signal));
    tbody.appendChild(row);
  }
}

function renderMarkets(intel) {
  const tbody = $('#market-table tbody'); tbody.innerHTML = '';
  for (const m of intel.markets) {
    const row = el('tr');
    row.appendChild(el('td', '', m.source));
    row.appendChild(el('td', 'small', m.type));
    row.appendChild(el('td', 'num', m.ph_gov != null ? m.ph_gov + '%' : '—'));
    row.appendChild(el('td', 'num', m.bnpn_gov != null ? m.bnpn_gov + '%' : '—'));
    row.appendChild(el('td', 'small muted', m.note));
    tbody.appendChild(row);
  }
}

function renderChangelog(intel) {
  const wrap = $('#changelog-list'); wrap.innerHTML = '';
  for (const c of intel.changelog) {
    const e = el('div', 'log-entry');
    e.appendChild(el('div', 'timestamp', c.timestamp));
    const s = el('div', 'summary');
    // Simple markdown bold conversion
    s.innerHTML = c.summary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    e.appendChild(s);
    wrap.appendChild(e);
  }
}

function renderExecutiveDetails(intel) {
  const cur = $('#exec-current'); cur.innerHTML = '';
  const ul = el('ul');
  ul.style.paddingLeft = 'var(--space-6)';
  ul.style.display = 'flex';
  ul.style.flexDirection = 'column';
  ul.style.gap = 'var(--space-2)';
  ul.style.fontSize = 'var(--text-sm)';
  for (const line of intel.executive.current_call) {
    const li = el('li');
    li.innerHTML = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    ul.appendChild(li);
  }
  cur.appendChild(ul);
  $('#exec-surprise').innerHTML = intel.executive.surprise_scenario
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  const wl = $('#exec-watchlist'); wl.innerHTML = '';
  for (const w of intel.executive.watchlist) {
    const li = el('li', 'small');
    li.textContent = w;
    wl.appendChild(li);
  }
  $('#projected-seats').textContent = intel.executive.probability_pct + '% · ' + intel.executive.predicted_winner_short;
}

// ---------- Master render ----------
async function render() {
  try {
    const { model, intel } = await loadData();
    renderMeta(model, intel);
    renderExec(intel);
    renderGovProb(model, intel);
    renderSeatTable(model);
    renderHeatMap(model);
    renderMomentum(intel);
    renderSentiment(intel);
    renderDemographics(intel);
    renderConstituencies(model);
    renderNarrative(intel);
    renderCandidates(intel);
    renderRisks(intel);
    renderPolls(intel);
    renderMarkets(intel);
    renderChangelog(intel);
    renderExecutiveDetails(intel);
  } catch (err) {
    console.error(err);
    $('#exec-headline').innerHTML = `<span style="color:var(--color-red);">Failed to load latest data — ${err.message}</span>`;
  }
}

render();
setInterval(render, REFRESH_MS);
