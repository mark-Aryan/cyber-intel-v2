/**
 * CyberIntel Hub — script.js
 * ==========================================
 * Pure vanilla ES2022. No framework, no build step.
 * Polls /api/data every 60 seconds, renders cards,
 * manages the detail modal, drives the live ticker.
 */

'use strict';

// ── Config ────────────────────────────────────────────────
const API      = '/api/data';
const INTERVAL = 60;    // seconds between auto-polls
const STAGGER  = 55;    // ms animation delay per card

// ── Category metadata ─────────────────────────────────────
const META = {
  news:          { label: 'NEWS',    badge: 'b-news',  icon: '📡' },
  vulnerability: { label: 'CVE',     badge: 'b-vuln',  icon: '⚠️' },
  fraud:         { label: 'FRAUD',   badge: 'b-fraud', icon: '🎣' },
  bug:           { label: 'BUG',     badge: 'b-bug',   icon: '🐛' },
};

// ── State ─────────────────────────────────────────────────
let data      = {};
let activeTab = 'all';
let countdown = INTERVAL;
let timer     = null;
let knownIds  = new Set();

// ── DOM ───────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const stLoading = $('state-loading');
const stError   = $('state-error');
const stEmpty   = $('state-empty');
const grid      = $('grid');
const errMsg    = $('err-msg');
const cd        = $('countdown');
const statusPill   = $('status-pill');
const statusLabel  = $('status-label');
const statusDot    = $('status-dot');
const refreshBtn   = $('refresh-btn');
const modalBg      = $('modal-bg');
const modalBody    = $('modal-body');
const modalX       = $('modal-x');
const ticker       = $('ticker');
const tickerScroll = $('ticker-scroll');

// ══════════════════════════════════════════════════════════
// BOOTSTRAP
// ══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  bindTabs();
  bindStats();
  bindModal();
  bindRefreshBtn();
  startCountdown();
  load();
});

// ══════════════════════════════════════════════════════════
// DATA LOADING
// ══════════════════════════════════════════════════════════
async function load() {
  setStatus('FETCHING', false);
  try {
    const res = await fetch(API, { headers: { 'Cache-Control': 'no-cache' } });
    if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`);
    const fresh = await res.json();

    const newIds = diff(fresh);   // Items not previously seen
    data     = fresh;
    knownIds = allIds(fresh);

    updateStats(fresh);
    render(filtered(fresh, activeTab), newIds);
    updateTicker(fresh);
    setStatus('LIVE', false);
    resetCountdown();
  } catch (err) {
    console.error('[CyberIntel]', err);
    setStatus('OFFLINE', true);
    showError(err.message);
  }
}

function diff(fresh) {
  if (!knownIds.size) return new Set();
  const n = new Set();
  for (const items of Object.values(fresh))
    if (Array.isArray(items))
      for (const item of items)
        if (!knownIds.has(item.id)) n.add(item.id);
  return n;
}

function allIds(d) {
  const s = new Set();
  for (const items of Object.values(d))
    if (Array.isArray(items)) for (const i of items) s.add(i.id);
  return s;
}

// ══════════════════════════════════════════════════════════
// RENDERING
// ══════════════════════════════════════════════════════════
function filtered(d, tab) {
  if (tab === 'all') {
    return Object.values(d).filter(Array.isArray).flat()
      .sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));
  }
  return (d[tab] || []).sort((a, b) =>
    (b.timestamp || '').localeCompare(a.timestamp || ''));
}

function render(items, newIds = new Set()) {
  hide();
  if (!items?.length) { stEmpty.style.display = 'flex'; return; }
  grid.style.display = 'grid';
  grid.innerHTML = '';
  items.forEach((item, i) => grid.appendChild(buildCard(item, i, newIds.has(item.id))));
}

function buildCard(item, i, isNew) {
  const m   = META[item.category] || META.news;
  const det = item['In-Depth Detail'] || {};
  const sev = (det.severity_rating || item.severity || '').toUpperCase();

  const el = document.createElement('div');
  el.className = 'card';
  el.style.animationDelay = `${i * STAGGER}ms`;

  const imgHtml = (item.image_path && !item.image_path.startsWith('/placeholders'))
    ? `<img class="card-img" src="${esc(item.image_path)}" alt="" loading="lazy"
           onerror="this.outerHTML='<div class=\\'card-img-ph\\'>${m.icon}</div>'">`
    : `<div class="card-img-ph">${m.icon}</div>`;

  const sevClass = sev ? `sev-${sev.toLowerCase()}` : '';

  el.innerHTML = `
    <div class="card-img-wrap">
      ${imgHtml}
      <span class="badge badge-cat ${m.badge}">${m.label}</span>
      ${sev ? `<span class="badge badge-sev ${sevClass}">${sev}</span>` : ''}
    </div>
    <div class="card-body">
      <div class="card-src">${esc(item.source || 'UNKNOWN SOURCE')}</div>
      <h3 class="card-ttl">${esc(item.original_title || 'UNTITLED')}</h3>
      <p class="card-sum">${esc(det.executive_summary || 'Analysis loading...')}</p>
      <div class="card-foot">
        <span class="card-time">${reltime(item.timestamp)}</span>
        <button class="card-more">ANALYSE ▶</button>
      </div>
    </div>`;

  el.addEventListener('click', () => openModal(item));
  return el;
}

// ══════════════════════════════════════════════════════════
// MODAL
// ══════════════════════════════════════════════════════════
function openModal(item) {
  const m   = META[item.category] || META.news;
  const det = item['In-Depth Detail'] || {};
  const sev = (det.severity_rating || item.severity || 'UNKNOWN').toUpperCase();

  const hero = (item.image_path && !item.image_path.startsWith('/placeholders'))
    ? `<img class="m-hero" src="${esc(item.image_path)}" alt="" />`
    : '';

  const techTags = (det.affected_technologies || [])
    .map(t => `<span class="m-tag tech">${esc(t)}</span>`).join('');
  const iocTags  = (det.ioc_keywords || [])
    .map(t => `<span class="m-tag ioc">${esc(t)}</span>`).join('');

  modalBody.innerHTML = `
    ${hero}
    <div class="m-meta">
      <span class="badge ${m.badge}" style="position:static">${m.label}</span>
      <span class="badge ${sev ? `sev-${sev.toLowerCase()}` : ''}" style="position:static">${sev}</span>
      <span class="card-time">${reltime(item.timestamp)}</span>
      <span class="card-src" style="margin-left:auto">${esc(item.source||'')}</span>
    </div>
    <h2 class="m-title">${esc(item.original_title||'Untitled')}</h2>
    ${mSection('EXECUTIVE SUMMARY',   det.executive_summary)}
    ${mSection('TECHNICAL ANALYSIS',  det.technical_analysis)}
    ${mSection('IMPACT ASSESSMENT',   det.impact)}
    ${mSection('ROOT CAUSE',          det.root_cause)}
    ${mSection('MITIGATION STEPS',    det.mitigation)}
    ${techTags ? `<div class="m-section"><div class="m-section-lbl">AFFECTED TECHNOLOGIES</div><div class="m-tags">${techTags}</div></div>` : ''}
    ${iocTags  ? `<div class="m-section"><div class="m-section-lbl">IOC KEYWORDS</div><div class="m-tags">${iocTags}</div></div>` : ''}
    <a class="m-src" href="${esc(item.source_url||'#')}" target="_blank" rel="noopener">
      ↗ VIEW SOURCE
    </a>`;

  modalBg.classList.add('open');
  modalBg.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function mSection(label, content) {
  if (!content) return '';
  return `<div class="m-section">
    <div class="m-section-lbl">${label}</div>
    <div class="m-section-body">${esc(content)}</div>
  </div>`;
}

function closeModal() {
  modalBg.classList.remove('open');
  modalBg.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

function bindModal() {
  modalX.onclick  = closeModal;
  modalBg.onclick = e => { if (e.target === modalBg) closeModal(); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

// ══════════════════════════════════════════════════════════
// TICKER
// ══════════════════════════════════════════════════════════
function updateTicker(d) {
  const items = Object.values(d).filter(Array.isArray).flat()
    .sort((a,b) => (b.timestamp||'').localeCompare(a.timestamp||'')).slice(0,12);
  if (!items.length) return;
  ticker.style.display = 'flex';
  const html = [...items, ...items]
    .map(i => `<span class="t-item">${esc(i.original_title||'')}</span>`).join('  ');
  tickerScroll.innerHTML = html;
}

// ══════════════════════════════════════════════════════════
// STATS
// ══════════════════════════════════════════════════════════
function updateStats(d) {
  let total = 0;
  for (const [cat, items] of Object.entries(d)) {
    if (!Array.isArray(items)) continue;
    const el = $('cnt-' + cat);
    if (el) el.textContent = items.length;
    total += items.length;
  }
  $('cnt-total').textContent = total;
}

// ══════════════════════════════════════════════════════════
// TABS & STATS CLICK
// ══════════════════════════════════════════════════════════
function bindTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      activeTab = btn.dataset.tab;
      render(filtered(data, activeTab));
    };
  });
}

function bindStats() {
  document.querySelectorAll('.stat[data-filter]').forEach(el => {
    el.onclick = () => {
      const f = el.dataset.filter;
      document.querySelectorAll('.tab').forEach(t =>
        t.classList.toggle('active', t.dataset.tab === f));
      activeTab = f;
      render(filtered(data, f));
    };
  });
}

// ══════════════════════════════════════════════════════════
// COUNTDOWN & REFRESH
// ══════════════════════════════════════════════════════════
function startCountdown() {
  clearInterval(timer);
  timer = setInterval(() => {
    countdown--;
    cd.textContent = countdown;
    if (countdown <= 0) { load(); resetCountdown(); }
  }, 1000);
}
function resetCountdown() { countdown = INTERVAL; cd.textContent = INTERVAL; }

function bindRefreshBtn() {
  refreshBtn.onclick = () => {
    if (refreshBtn.classList.contains('spin')) return;
    refreshBtn.classList.add('spin');
    load().finally(() => refreshBtn.classList.remove('spin'));
  };
  $('err-retry').onclick = () => { show(stLoading); load(); };
}

// ══════════════════════════════════════════════════════════
// UI HELPERS
// ══════════════════════════════════════════════════════════
function hide() {
  [stLoading, stError, stEmpty, grid].forEach(el => {
    if (el) { el.style.display = 'none'; }
  });
}
function show(el) { hide(); el.style.display = 'flex'; }
function showError(msg) {
  hide();
  stError.style.display = 'flex';
  errMsg.textContent = msg || 'Unknown error.';
}

function setStatus(label, offline) {
  statusLabel.textContent = label;
  statusPill.classList.toggle('offline', offline);
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

function reltime(iso) {
  if (!iso) return '—';
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 60)  return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24)  return `${h}h ago`;
    const d = Math.floor(h / 24);
    if (d < 7)   return `${d}d ago`;
    return new Date(iso).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
  } catch { return iso.slice(0, 10); }
}
