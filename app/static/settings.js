function setMsg(text, isError) {
  const el = document.getElementById('settings-msg');
  if (el) {
    el.textContent = text;
    el.style.color = isError ? '#c0392b' : '#27ae60';
  }
}

async function api(url, options) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    window.location.href = '/settings';
    throw new Error('unauthorized');
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* пустой ответ */ }
  if (!res.ok) throw new Error(data.detail || 'Ошибка');
  return data;
}

function postJson(url, body) {
  return api(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// --- Страница входа ---
const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = document.getElementById('admin-password').value;
    const errEl = document.getElementById('login-error');
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        window.location.href = '/settings';
      } else {
        errEl.textContent = 'Неверный пароль';
      }
    } catch (err) {
      errEl.textContent = 'Ошибка';
    }
  });
}

// --- Страница настроек ---
async function loadConfig() {
  try {
    const cfg = await api('/api/telegram/config');
    document.getElementById('tg-channels').value = cfg.channels || '';
    document.getElementById('tg-enabled').checked = !!cfg.enabled;
  } catch (e) {
    console.error(e);
  }
}

if (document.getElementById('tg-channels')) {
  document.getElementById('save-channels').addEventListener('click', async () => {
    try {
      await postJson('/api/telegram/config', {
        channels: document.getElementById('tg-channels').value,
        enabled: document.getElementById('tg-enabled').checked,
      });
      setMsg('Каналы сохранены');
    } catch (e) { setMsg(e.message, true); }
  });

  loadConfig();
}
