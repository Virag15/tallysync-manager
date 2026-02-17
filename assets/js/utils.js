/**
 * TallySync Manager — Shared Utilities
 * Version: 1.0.0 | Build: 20260217.001
 */

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

// ── Company Selector ───────────────────────────────────────────────────────────

async function initCompanySelector() {
  const select = document.getElementById('company-select');
  if (!select) return;
  try {
    const companies = await Companies.list();
    select.innerHTML = companies.length
      ? companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('')
      : '<option value="">No companies — go to Settings</option>';

    const saved = CompanyStore.get();
    if (saved && companies.find(c => c.id === saved)) {
      select.value = String(saved);
    } else if (companies.length) {
      CompanyStore.set(companies[0].id);
      select.value = String(companies[0].id);
    }
  } catch (_) {
    select.innerHTML = '<option value="">Server offline</option>';
    toast('Cannot reach TallySync server', 'error');
  }
  select.addEventListener('change', () => {
    CompanyStore.set(select.value ? parseInt(select.value, 10) : null);
  });
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
  const csv = [headers.join(','), ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? '')).join(','))].join('\n');
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })),
    download: filename,
  });
  a.click();
}
