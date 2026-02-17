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
    }
  } catch (_) {
    _setLabel('Server offline');
    dropdown.innerHTML = '<div class="cs-empty">Cannot reach server</div>';
    toast('Cannot reach TallySync server', 'error');
  }
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
