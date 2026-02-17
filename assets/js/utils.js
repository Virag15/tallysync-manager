/**
 * TallySync Manager — Shared Utilities
 * Version: 1.0.0 | Build: 20260217.001
 */

// ── HTML Escape ────────────────────────────────────────────────────────────────

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── Company State ──────────────────────────────────────────────────────────────

const CompanyStore = {
  _key: 'tallysync_company_id',
  get()    { const v = localStorage.getItem(this._key); return v ? parseInt(v, 10) : null; },
  set(id)  {
    if (id) localStorage.setItem(this._key, String(id));
    else    localStorage.removeItem(this._key);
    window.dispatchEvent(new CustomEvent('company:changed', { detail: { id } }));
  },
};

// ── Formatters ─────────────────────────────────────────────────────────────────

const fmt = {
  currency(v, sym = '₹') {
    if (v == null) return '—';
    return sym + Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },
  number(v, dec = 2) {
    if (v == null) return '—';
    return Number(v).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  },
  date(v) {
    if (!v) return '—';
    return new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  },
  datetime(v) {
    if (!v) return '—';
    return new Date(v).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  },
  relativeTime(v) {
    if (!v) return 'Never';
    const s = Math.floor((Date.now() - new Date(v).getTime()) / 1000);
    if (s < 60)    return `${s}s ago`;
    if (s < 3600)  return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return fmt.date(v);
  },
};

// ── Status Badge ───────────────────────────────────────────────────────────────

function statusBadge(status) {
  const map = {
    DRAFT:     ['badge-neutral',  'Draft'],
    CONFIRMED: ['badge-info',     'Confirmed'],
    PUSHED:    ['badge-success',  'Pushed'],
    CANCELLED: ['badge-danger',   'Cancelled'],
    SUCCESS:   ['badge-success',  'Success'],
    FAILED:    ['badge-danger',   'Failed'],
    PARTIAL:   ['badge-warning',  'Partial'],
  };
  const [cls, label] = map[status] || ['badge-neutral', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

// ── Toast (shadcn Sonner-style) ────────────────────────────────────────────────

const TOAST_ICONS = {
  success: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  error:   `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>`,
  warning: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
  info:    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
};

function toast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <span class="toast-icon">${TOAST_ICONS[type] || TOAST_ICONS.info}</span>
    <div class="toast-body"><div class="toast-title">${message}</div></div>
  `;
  container.appendChild(el);

  setTimeout(() => {
    el.style.transition = 'opacity 250ms, transform 250ms';
    el.style.opacity = '0';
    el.style.transform = 'translateX(1rem)';
    setTimeout(() => el.remove(), 260);
  }, duration);
}

// ── Modal Helpers ──────────────────────────────────────────────────────────────

function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Table Helpers ──────────────────────────────────────────────────────────────

function renderEmptyState(msg = 'No results found') {
  return `<tr><td colspan="99">
    <div class="empty-state">
      <div class="empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <div class="fw-500">${msg}</div>
    </div>
  </td></tr>`;
}

function renderLoadingRow() {
  return `<tr><td colspan="99" style="padding:2.5rem;text-align:center;">
    <span class="spinner"></span>
  </td></tr>`;
}

// ── Company Selector (custom dropdown) ────────────────────────────────────────

async function initCompanySelector() {
  const trigger  = document.getElementById('cs-trigger');
  const dropdown = document.getElementById('cs-dropdown');
  const label    = document.getElementById('cs-label');
  if (!trigger || !dropdown) return;

  let _companies = [];
  let _open = false;

  function _setLabel(name) {
    label.textContent = name || 'Select company';
  }

  function _openDropdown() {
    if (_open) return;
    _open = true;
    trigger.setAttribute('aria-expanded', 'true');
    dropdown.classList.add('cs-open');
    // Position check: flip up if too close to bottom
    const rect = trigger.getBoundingClientRect();
    if (rect.bottom + 260 > window.innerHeight) {
      dropdown.style.top = 'auto';
      dropdown.style.bottom = '100%';
      dropdown.style.marginTop = '0';
      dropdown.style.marginBottom = '0.25rem';
    } else {
      dropdown.style.bottom = 'auto';
      dropdown.style.top = '100%';
      dropdown.style.marginBottom = '0';
      dropdown.style.marginTop = '0.25rem';
    }
    dropdown.querySelector('[aria-selected="true"]')?.focus();
  }

  function _closeDropdown() {
    if (!_open) return;
    _open = false;
    trigger.setAttribute('aria-expanded', 'false');
    dropdown.classList.remove('cs-open');
    trigger.focus();
  }

  function _renderOptions(companies) {
    const saved = CompanyStore.get();
    dropdown.innerHTML = companies.length
      ? companies.map(c => `
          <div class="cs-option${c.id === saved ? ' cs-selected' : ''}"
               role="option" tabindex="0"
               aria-selected="${c.id === saved}"
               data-id="${esc(String(c.id))}">
            <svg class="cs-check" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            ${esc(c.name)}
          </div>`).join('')
      : `<div class="cs-empty">No companies — <a href="settings.html">add one</a></div>`;

    dropdown.querySelectorAll('.cs-option').forEach(opt => {
      opt.addEventListener('click', () => {
        const id = parseInt(opt.dataset.id, 10);
        CompanyStore.set(id);
        dropdown.querySelectorAll('.cs-option').forEach(o => {
          o.classList.toggle('cs-selected', parseInt(o.dataset.id, 10) === id);
          o.setAttribute('aria-selected', parseInt(o.dataset.id, 10) === id);
        });
        const c = _companies.find(c => c.id === id);
        if (c) _setLabel(c.name);
        _closeDropdown();
      });
      opt.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); opt.click(); }
        if (e.key === 'Escape') _closeDropdown();
        if (e.key === 'ArrowDown') { e.preventDefault(); (opt.nextElementSibling || opt).focus(); }
        if (e.key === 'ArrowUp')   { e.preventDefault(); (opt.previousElementSibling || opt).focus(); }
      });
    });
  }

  // Trigger click
  trigger.addEventListener('click', e => {
    e.stopPropagation();
    _open ? _closeDropdown() : _openDropdown();
  });
  trigger.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault(); _openDropdown();
    }
    if (e.key === 'Escape') _closeDropdown();
  });

  // Close on outside click
  document.addEventListener('click', e => {
    const root = document.getElementById('cs-root');
    if (root && !root.contains(e.target)) _closeDropdown();
  });

  // Load companies
  try {
    _companies = await Companies.list();
    _renderOptions(_companies);
    const saved = CompanyStore.get();
    const active = saved && _companies.find(c => c.id === saved);
    if (active) {
      _setLabel(active.name);
    } else if (_companies.length) {
      CompanyStore.set(_companies[0].id);
      _setLabel(_companies[0].name);
      _renderOptions(_companies);
    } else {
      _setLabel('No companies');
      _showOnboarding();
    }
  } catch (_) {
    _setLabel('Server offline');
    dropdown.innerHTML = '<div class="cs-empty">Cannot reach server</div>';
    toast('Cannot reach TallySync server', 'error');
  }
}

// ── First-Run Onboarding Wizard ─────────────────────────────────────────────────

function _showOnboarding() {
  if (document.getElementById('ob-overlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'ob-overlay';
  overlay.innerHTML = `
    <div class="ob-card">
      <div class="ob-brand">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        TallySync Manager
      </div>

      <!-- Step 1: Welcome -->
      <div id="ob-step1">
        <p class="ob-title">Welcome! Let's get started.</p>
        <p class="ob-desc">Connect TallySync to your Tally Prime to sync companies, orders, and inventory automatically.</p>
        <div class="ob-actions">
          <button class="btn btn-primary" onclick="_obConnect()">Connect to Tally Prime</button>
          <button class="btn btn-outline" onclick="_obDemo()">Try with demo data</button>
        </div>
        <p class="ob-hint">Already have Tally running? Click "Connect" above.</p>
      </div>

      <!-- Step 2: Connection form -->
      <div id="ob-step2" class="ob-hidden">
        <p class="ob-step-num">Step 2 of 2</p>
        <p class="ob-title">Connect to Tally Prime</p>
        <p class="ob-desc">Enter your Tally company details. You can change these later in Settings.</p>
        <div class="ob-form">
          <div class="ob-field">
            <label for="ob-name">Company name (as it appears in Tally)</label>
            <input id="ob-name" class="form-control" type="text" placeholder="e.g. Acme Industries" autocomplete="off">
          </div>
          <div class="ob-row">
            <div class="ob-field" style="flex:1">
              <label for="ob-host">Tally server address</label>
              <input id="ob-host" class="form-control" type="text" value="localhost" placeholder="localhost">
            </div>
            <div class="ob-field" style="width:90px">
              <label for="ob-port">Port</label>
              <input id="ob-port" class="form-control" type="number" value="9000" min="1" max="65535">
            </div>
          </div>
        </div>
        <div class="ob-actions">
          <button class="btn btn-primary" id="ob-connect-btn" onclick="_obTryConnect()">Connect &amp; Sync</button>
          <button class="btn btn-ghost" onclick="_obGo(1)">← Back</button>
        </div>
        <p class="ob-hint">Tally must be open and HTTP server enabled on port 9000.<br>
          <span class="ob-hint-inline">F12 → Advanced Configuration → Enable HTTP Server</span>
        </p>
      </div>

      <!-- Step 3: Result -->
      <div id="ob-step3" class="ob-hidden">
        <div id="ob-result"></div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

function _obGo(step) {
  [1, 2, 3].forEach(n => {
    const el = document.getElementById('ob-step' + n);
    if (el) el.classList.toggle('ob-hidden', n !== step);
  });
}

async function _obDemo() {
  _obGo(3);
  document.getElementById('ob-result').innerHTML = `
    <p class="ob-title">Setting up demo…</p>
    <p class="ob-desc">Creating a demo company with sample data.</p>
    <div style="text-align:center;padding:1rem 0">
      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none"
           stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
           style="animation:spin 1s linear infinite">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
      </svg>
    </div>`;

  try {
    const res = await apiFetch('/api/companies', {
      method: 'POST',
      body: JSON.stringify({ name: 'Demo Company', tally_host: 'localhost', tally_port: 9000 }),
    });
    if (!res.ok) throw new Error('create failed');
    const company = await res.json();
    await apiFetch(`/api/companies/${company.id}/sync`, { method: 'POST' });
    _obSuccess('Demo company created! Explore the dashboard to see how TallySync works.', true);
  } catch (_) {
    _obSuccess('Demo mode ready. You can add a real Tally connection later in Settings.', true);
  }
}

async function _obTryConnect() {
  const name = document.getElementById('ob-name').value.trim();
  const host = document.getElementById('ob-host').value.trim() || 'localhost';
  const port = parseInt(document.getElementById('ob-port').value, 10) || 9000;

  if (!name) {
    toast('Please enter the company name', 'warning');
    document.getElementById('ob-name').focus();
    return;
  }

  const btn = document.getElementById('ob-connect-btn');
  btn.disabled = true;
  btn.textContent = 'Connecting…';

  let companyId = null;
  try {
    const res = await apiFetch('/api/companies', {
      method: 'POST',
      body: JSON.stringify({ name, tally_host: host, tally_port: port }),
    });
    if (!res.ok) throw new Error('create failed');
    const company = await res.json();
    companyId = company.id;

    const syncRes = await apiFetch(`/api/companies/${companyId}/sync`, { method: 'POST' });
    if (!syncRes.ok) throw new Error('sync failed');

    _obGo(3);
    _obSuccess(`Connected to <strong>${esc(name)}</strong>! Syncing data now — your dashboard will update shortly.`, true);
  } catch (_) {
    btn.disabled = false;
    btn.textContent = 'Connect & Sync';
    if (companyId) {
      try { await apiFetch(`/api/companies/${companyId}`, { method: 'DELETE' }); } catch (_) {}
    }
    _obFail(`Could not connect to Tally at <strong>${esc(host)}:${port}</strong>.<br>
      Make sure Tally is open and HTTP server is enabled.`, true);
  }
}

function _obSuccess(msg, showDashboard = false) {
  _obGo(3);
  document.getElementById('ob-result').innerHTML = `
    <div style="text-align:center;padding:0.5rem 0 1rem">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="oklch(0.65 0.22 142)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
      </svg>
    </div>
    <p class="ob-title" style="text-align:center">All set!</p>
    <p class="ob-desc" style="text-align:center">${msg}</p>
    ${showDashboard ? `<div class="ob-actions">
      <button class="btn btn-primary" onclick="document.getElementById('ob-overlay').remove();location.reload()">
        Go to Dashboard →
      </button>
    </div>` : ''}`;
}

function _obFail(msg, allowRetry = true) {
  _obGo(3);
  document.getElementById('ob-result').innerHTML = `
    <div style="text-align:center;padding:0.5rem 0 1rem">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="oklch(0.55 0.22 27)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
      </svg>
    </div>
    <p class="ob-title" style="text-align:center">Connection failed</p>
    <p class="ob-desc" style="text-align:center">${msg}</p>
    ${allowRetry ? `<div class="ob-actions">
      <button class="btn btn-primary" onclick="_obGo(2)">← Try again</button>
      <button class="btn btn-outline" onclick="_obDemo()">Use demo data instead</button>
    </div>` : ''}`;
}

// ── Active Nav ─────────────────────────────────────────────────────────────────

function setActiveNav() {
  const current = window.location.pathname.split('/').pop() || 'dashboard.html';
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', (link.getAttribute('href') || '').includes(current));
  });
}

// ── Date Utils ─────────────────────────────────────────────────────────────────

function today()    { return new Date().toISOString().split('T')[0]; }
function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().split('T')[0]; }

// ── Debounce ───────────────────────────────────────────────────────────────────

function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── CSV Export ─────────────────────────────────────────────────────────────────

function exportCSV(rows, filename = 'export.csv') {
  if (!rows.length) { toast('Nothing to export', 'warning'); return; }
  const headers = Object.keys(rows[0]);
  const cell = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const csv = [headers.map(cell).join(','), ...rows.map(r => headers.map(h => cell(r[h])).join(','))].join('\r\n');
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })),
    download: filename,
  });
  a.click();
}
