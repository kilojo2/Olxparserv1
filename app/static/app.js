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

async function loadListings() {
  try {
    const res = await fetch('/api/listings');
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
      tr.innerHTML =
        '<td><a href="' + escapeHtml(l.url) + '" target="_blank" rel="noopener noreferrer">' +
        escapeHtml(title) + '</a></td>' +
        '<td>' + escapeHtml(l.price) + '</td>' +
        '<td>' + escapeHtml(l.area) + '</td>' +
        '<td>' + escapeHtml(l.location) + '</td>' +
        '<td>' + escapeHtml(formatDate(l.published_at)) + '</td>';
      tbody.appendChild(tr);
    }
  } catch (e) {
    console.error(e);
  }
}

async function runNow() {
  const btn = document.getElementById('run-now');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.textContent = '⏳ Парсинг...';
  try {
    await fetch('/api/run', { method: 'POST' });
    status.textContent = '✅ Запущено';
  } catch (e) {
    status.textContent = '❌ Помилка';
  }
  btn.disabled = false;
  setTimeout(loadListings, 8000);
}

document.getElementById('run-now').addEventListener('click', runNow);

loadListings();
setInterval(loadListings, 60000);
