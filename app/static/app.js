let nextRunAt = null;

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDate(iso) {
  if (!iso) return '';
  return String(iso).replace('T', ' ').slice(0, 16);
}

function safeUrl(value) {
  try {
    const url = new URL(value, window.location.origin);
    return (url.protocol === 'http:' || url.protocol === 'https:') ? url.href : '#';
  } catch (e) {
    return '#';
  }
}

const FILTER_IDS = [
  'f-currency', 'f-min-price', 'f-max-price', 'f-rooms', 'f-district',
  'f-date-from', 'f-date-to', 'f-q'
];

function buildQuery() {
  const p = new URLSearchParams();
  const currency = document.getElementById('f-currency').value;
  const min = document.getElementById('f-min-price').value;
  const max = document.getElementById('f-max-price').value;
  const rooms = document.getElementById('f-rooms').value;
  const district = document.getElementById('f-district').value;
  const from = document.getElementById('f-date-from').value;
  const to = document.getElementById('f-date-to').value;
  const q = document.getElementById('f-q').value.trim();
  if (min) p.set('min_price', min);
  if (max) p.set('max_price', max);
  if (currency) p.set('currency', currency);
  if (rooms) p.set('rooms', rooms);
  if (district) p.set('district', district);
  if (from) p.set('date_from', from);
  if (to) p.set('date_to', to);
  if (q) p.set('q', q);
  const s = p.toString();
  return s ? '?' + s : '';
}

async function loadListings() {
  try {
    const res = await fetch('/api/listings' + buildQuery());
    if (res.status === 401) { window.location.href = '/settings'; return; }
    const data = await res.json();
    document.getElementById('count').textContent = data.count;
    const tbody = document.querySelector('#listings tbody');
    tbody.innerHTML = '';
    const empty = document.getElementById('empty');

    if (!data.listings.length) {
      empty.style.display = 'block';
      return;
    }
    empty.style.display = 'none';

    for (const l of data.listings) {
      const tr = document.createElement('tr');
      const title = l.title || l.url;
      const rooms = (l.rooms === null || l.rooms === undefined) ? '' : l.rooms;
      const sourceLabels = { telegram: 'TG', olx: 'OLX', domria: 'RIA', rieltor: 'RIEL' };
      const src = l.source || 'olx';
      const label = sourceLabels[src] || src.toUpperCase().slice(0, 5);
      const safeClass = src.replace(/[^a-z0-9_-]/gi, '');
      const sourceBadge = '<span class="badge badge-' + safeClass + '">' + escapeHtml(label) + '</span>';
      const price = l.price ||
        ((l.price_value !== null && l.price_value !== undefined)
          ? String(l.price_value) + ' ' + (l.currency || '')
          : '');
      tr.innerHTML =
        '<td>' + sourceBadge + '</td>' +
        '<td><a href="' + escapeHtml(safeUrl(l.url)) + '" target="_blank" rel="noopener noreferrer">' +
        escapeHtml(title) + '</a></td>' +
        '<td>' + escapeHtml(price) + '</td>' +
        '<td>' + escapeHtml(rooms) + '</td>' +
        '<td>' + escapeHtml(l.area) + '</td>' +
        '<td>' + escapeHtml(l.district || l.location) + '</td>' +
        '<td>' + escapeHtml(formatDate(l.published_at)) + '</td>';
      tbody.appendChild(tr);
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadFilters() {
  try {
    const res = await fetch('/api/filters');
    const data = await res.json();
    const roomsSel = document.getElementById('f-rooms');
    const districtSel = document.getElementById('f-district');
    const currencySel = document.getElementById('f-currency');
    for (const c of (data.currencies || [])) {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      currencySel.appendChild(opt);
    }
    for (const r of (data.rooms || [])) {
      const opt = document.createElement('option');
      opt.value = r;
      opt.textContent = r + ' кімн.';
      roomsSel.appendChild(opt);
    }
    for (const d of (data.districts || [])) {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      districtSel.appendChild(opt);
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    nextRunAt = data.next_run_at ? new Date(data.next_run_at) : null;
    updateCountdown();
  } catch (e) {
    console.error(e);
  }
}

function updateCountdown() {
  const el = document.getElementById('countdown');
  if (!el) return;
  if (!nextRunAt) {
    el.textContent = 'До оновлення: —';
    return;
  }
  const diff = nextRunAt.getTime() - Date.now();
  if (diff <= 0) {
    el.textContent = 'Оновлення зараз…';
    loadListings();
    loadStatus();
    return;
  }
  const total = Math.floor(diff / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  el.textContent = 'До оновлення: ' +
    String(h).padStart(2, '0') + ':' +
    String(m).padStart(2, '0') + ':' +
    String(s).padStart(2, '0');
}

async function runNow() {
  const btn = document.getElementById('run-now');
  const status = document.getElementById('status');
  if (!btn || !status) return;
  btn.disabled = true;
  status.textContent = '⏳ Парсинг…';
  try {
    const res = await fetch('/api/run', { method: 'POST' });
    if (res.status === 401) { window.location.href = '/settings'; return; }
    if (!res.ok) throw new Error('run failed');
    status.textContent = '✅ Запущено';
  } catch (e) {
    status.textContent = '❌ Помилка';
  }
  btn.disabled = false;
  setTimeout(loadListings, 8000);
  setTimeout(loadStatus, 8000);
}

function resetFilters() {
  FILTER_IDS.forEach(function (id) {
    document.getElementById(id).value = '';
  });
  loadListings();
}

let debounceTimer = null;
function scheduleReload() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadListings, 350);
}

document.getElementById('run-now').addEventListener('click', runNow);
document.getElementById('f-reset').addEventListener('click', resetFilters);
FILTER_IDS.forEach(function (id) {
  const el = document.getElementById(id);
  el.addEventListener('input', scheduleReload);
  el.addEventListener('change', scheduleReload);
});

loadFilters();
loadListings();
loadStatus();
setInterval(updateCountdown, 1000);
setInterval(loadListings, 60000);
