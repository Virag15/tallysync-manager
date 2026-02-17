/**
 * TallySync Manager — Shared Layout
 * Version: 1.0.0 | Build: 20260217.001
 * Sidebar uses shadcn/ui dark sidebar variant
 */

const APP_VERSION = '1.0.0';
const APP_BUILD   = '20260217.001';

/* ── Lucide-style inline SVG icons ──────────────────────────────────────────── */
const ICONS = {
  dashboard: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`,
  package:   `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`,
  orders:    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 2h6a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="m9 14 2 2 4-4"/></svg>`,
  reports:   `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>`,
  settings:  `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
  tally:     `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20"/></svg>`,
};

function injectLayout(pageTitle = 'Dashboard') {
  const existingContent = document.getElementById('page-content');

  const shell = document.createElement('div');
  shell.className = 'app-shell';
  shell.innerHTML = `
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">${ICONS.tally}</div>
        <div>
          <div class="logo-text">TallySync</div>
          <div class="logo-sub">v${APP_VERSION}</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="sidebar-section">
          <div class="sidebar-section-label">Menu</div>
          <a href="dashboard.html" class="nav-link">
            <span class="nav-icon">${ICONS.dashboard}</span>
            <span class="nav-label">Dashboard</span>
          </a>
          <a href="inventory.html" class="nav-link">
            <span class="nav-icon">${ICONS.package}</span>
            <span class="nav-label">Inventory</span>
          </a>
          <a href="orders.html" class="nav-link">
            <span class="nav-icon">${ICONS.orders}</span>
            <span class="nav-label">Orders</span>
          </a>
          <a href="reports.html" class="nav-link">
            <span class="nav-icon">${ICONS.reports}</span>
            <span class="nav-label">Reports</span>
          </a>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">System</div>
          <a href="settings.html" class="nav-link">
            <span class="nav-icon">${ICONS.settings}</span>
            <span class="nav-label">Settings</span>
          </a>
        </div>
      </nav>

      <div class="sidebar-footer">
        Build ${APP_BUILD}<br>
        &copy; 2026 TallySync
      </div>
    </aside>

    <div class="main-content">
      <header class="topbar">
        <span class="topbar-title">${pageTitle}</span>

        <div class="company-select-wrap">
          <label for="company-select">Company</label>
          <select id="company-select"><option>Loading…</option></select>
        </div>

        <div class="sync-badge">
          <div class="sync-dot syncing" id="sync-dot"></div>
          <span id="sync-text">Connecting…</span>
        </div>
      </header>

      <main class="page-content" id="page-content-inner"></main>
    </div>
  `;

  document.body.appendChild(shell);

  const inner = document.getElementById('page-content-inner');
  if (existingContent && inner) inner.appendChild(existingContent);

  const toastEl = document.createElement('div');
  toastEl.id = 'toast-container';
  document.body.appendChild(toastEl);

  setActiveNav();
  initCompanySelector();
}
