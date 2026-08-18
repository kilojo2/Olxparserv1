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
    document.getElementById('tg-api-id').value = cfg.api_id || '';
    document.getElementById('tg-api-hash').value = cfg.api_hash || '';
    document.getElementById('tg-channels').value = cfg.channels || '';
    document.getElementById('tg-enabled').checked = !!cfg.enabled;
    const statusEl = document.getElementById('tg-status');
    const ok = !!cfg.session_set;
    statusEl.textContent = ok ? '✅ Подключено' : '❌ Не подключено';
    statusEl.className = 'tg-status ' + (ok ? 'ok' : 'off');
  } catch (e) {
    console.error(e);
  }
}

if (document.getElementById('tg-api-id')) {
  document.getElementById('save-app').addEventListener('click', async () => {
    try {
      await postJson('/api/telegram/config', {
        api_id: document.getElementById('tg-api-id').value,
        api_hash: document.getElementById('tg-api-hash').value,
      });
      setMsg('API сохранено');
    } catch (e) { setMsg(e.message, true); }
  });

  async function sendCode(forceSms) {
    try {
      const res = await postJson('/api/telegram/send-code', {
        phone: document.getElementById('tg-phone').value,
        force_sms: forceSms,
      });
      setMsg('Код отправлен: ' + (res.method || 'проверьте Telegram'));
    } catch (e) { setMsg(e.message, true); }
  }

  document.getElementById('send-code').addEventListener('click', () => sendCode(false));
  document.getElementById('send-sms').addEventListener('click', () => sendCode(true));

  document.getElementById('verify-code').addEventListener('click', async () => {
    try {
      const res = await postJson('/api/telegram/verify-code', {
        code: document.getElementById('tg-code').value,
      });
      if (res.twofa) {
        setMsg('Введите пароль 2FA');
      } else {
        setMsg('✅ Подключено');
        loadConfig();
      }
    } catch (e) { setMsg(e.message, true); }
  });

  document.getElementById('verify-password').addEventListener('click', async () => {
    try {
      await postJson('/api/telegram/verify-password', {
        password: document.getElementById('tg-2fa').value,
      });
      setMsg('✅ Подключено');
      loadConfig();
    } catch (e) { setMsg(e.message, true); }
  });

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
