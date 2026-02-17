/**
 * TallySync Manager — Settings Page
 * Version: 1.0.0 | Build: 20260217.001
 */

async function initSettings() {
  await loadAppInfo();
  await loadCompanies();
  setupSettingsEvents();
}

async function loadAppInfo() {
  // Populate backend URL field from localStorage
  document.getElementById('backend-url').value = localStorage.getItem('tallysync_api') || window.TALLYSYNC_API || 'http://localhost:8001';

  // Populate API key from localStorage (already set) or from server
  const storedKey = localStorage.getItem('tallysync_api_key') || '';
  if (storedKey) document.getElementById('api-key').value = storedKey;

  try {
    const info = await Info.get();
    document.getElementById('info-name').textContent    = info.name;
    document.getElementById('info-version').textContent = info.version;
    document.getElementById('info-build').textContent   = info.build;
    document.getElementById('info-db').textContent      = info.db_path;
    // Auto-save key on first run so users don't need to manually click Save
    if (!storedKey && info.api_key) {
      document.getElementById('api-key').value = info.api_key;
      localStorage.setItem('tallysync_api_key', info.api_key);
      // Also ensure window.TALLYSYNC_API reflects the current URL
      const currentUrl = document.getElementById('backend-url').value.trim().replace(/\/$/, '');
      if (currentUrl) localStorage.setItem('tallysync_api', currentUrl);
      toast('Connected! API key saved automatically.', 'success');
    }
  } catch (_) { toast('Cannot reach server — check Backend URL in Settings', 'warning'); }
}

function saveConnection() {
  const url = document.getElementById('backend-url').value.trim().replace(/\/$/, '');
  const key = document.getElementById('api-key').value.trim();
  if (!url) { toast('Enter a valid backend URL', 'warning'); return; }
  if (!key) { toast('Enter the API key', 'warning'); return; }
  localStorage.setItem('tallysync_api', url);
  localStorage.setItem('tallysync_api_key', key);
  window.TALLYSYNC_API = url;
  toast('Connection settings saved — reloading…', 'success');
  setTimeout(() => location.reload(), 900);
}

async function loadCompanies() {
  const tbody = document.getElementById('companies-table');
  tbody.innerHTML = renderLoadingRow();
  try {
    const list = await Companies.list();
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="8">
        <div class="empty-state">
          <div class="empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </div>
          <div class="fw-500">No companies yet</div>
          <div class="text-muted text-sm">Add your first Tally company to get started</div>
          <button class="btn btn-primary" onclick="openCompanyModal()" style="margin-top:0.5rem;">Add Company</button>
        </div>
      </td></tr>`;
      return;
    }
    tbody.innerHTML = list.map(c => `<tr>
      <td class="fw-600">${esc(c.name)}</td>
      <td class="text-muted">${esc(c.tally_company_name)}</td>
      <td class="mono text-sm">${esc(c.host)}</td>
      <td class="mono text-sm">${c.port}</td>
      <td class="text-muted text-sm">${c.sync_interval_minutes} min</td>
      <td class="text-muted text-sm">${fmt.relativeTime(c.last_synced_at)}</td>
      <td>${c.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-neutral">Inactive</span>'}</td>
      <td>
        <div class="flex gap-2">
          <button class="btn btn-outline btn-sm" onclick="editCompany(${c.id})">Edit</button>
          <button class="btn btn-secondary btn-sm" onclick="triggerSync(${c.id}, this)">Sync</button>
          <button class="btn btn-ghost btn-sm" onclick="viewSyncLogs(${c.id})">Logs</button>
          <button class="btn btn-ghost btn-sm text-destructive" onclick="deleteCompany(${c.id})">Delete</button>
        </div>
      </td>
    </tr>`).join('');
  } catch (err) { tbody.innerHTML = renderEmptyState('Failed: ' + err.message); }
}

function setupSettingsEvents() {
  document.getElementById('btn-add-company')?.addEventListener('click', () => openCompanyModal());
  document.getElementById('btn-save-company')?.addEventListener('click', saveCompany);
  document.getElementById('btn-test-conn')?.addEventListener('click', testConnection);
  document.getElementById('btn-test-entry')?.addEventListener('click', sendTestEntry);
  document.getElementById('btn-guide')?.addEventListener('click', openGuide);
  document.getElementById('btn-probe')?.addEventListener('click', probeConnection);
  document.getElementById('btn-save-connection')?.addEventListener('click', saveConnection);
  document.getElementById('btn-toggle-key')?.addEventListener('click', () => {
    const inp = document.getElementById('api-key');
    inp.type = inp.type === 'password' ? 'text' : 'password';
  });
  document.getElementById('btn-copy-key')?.addEventListener('click', () => {
    const key = document.getElementById('api-key').value;
    if (!key) { toast('No key to copy', 'warning'); return; }
    navigator.clipboard.writeText(key).then(() => toast('API key copied', 'success'));
  });
}

// ── Modal ──────────────────────────────────────────────────────────────────────

function openCompanyModal(c = null) {
  document.getElementById('company-modal-title').textContent = c ? 'Edit Company' : 'Add Company';
  document.getElementById('edit-company-id').value    = c?.id || '';
  document.getElementById('company-name').value       = c?.name || '';
  document.getElementById('company-tally-name').value = c?.tally_company_name || '';
  document.getElementById('company-host').value       = c?.host || 'localhost';
  document.getElementById('company-port').value       = c?.port || 9000;
  document.getElementById('company-interval').value   = c?.sync_interval_minutes || 5;
  document.getElementById('test-result').style.display = 'none';
  document.getElementById('btn-test-entry').style.display = 'none';
  openModal('company-modal');
}

async function editCompany(id) {
  try { openCompanyModal(await Companies.get(id)); }
  catch (err) { toast('Load failed: ' + err.message, 'error'); }
}

async function saveCompany() {
  const id       = document.getElementById('edit-company-id').value;
  const name     = document.getElementById('company-name').value.trim();
  const tName    = document.getElementById('company-tally-name').value.trim();
  const host     = document.getElementById('company-host').value.trim();
  const port     = parseInt(document.getElementById('company-port').value);
  const interval = parseInt(document.getElementById('company-interval').value) || 5;

  if (!name || !tName || !host || !port) { toast('Fill in all required fields', 'warning'); return; }

  try {
    const payload = { name, tally_company_name: tName, host, port, sync_interval_minutes: interval };
    if (id) { await Companies.update(id, payload); toast('Company updated', 'success'); }
    else    { await Companies.create(payload);      toast('Company added', 'success'); }
    closeModal('company-modal');
    loadCompanies();
    initCompanySelector();
  } catch (err) { toast('Save failed: ' + err.message, 'error'); }
}

async function testConnection() {
  const id   = document.getElementById('edit-company-id').value;
  const host = document.getElementById('company-host').value.trim() || 'localhost';
  const port = parseInt(document.getElementById('company-port').value) || 9000;
  const btn  = document.getElementById('btn-test-conn');
  const el   = document.getElementById('test-result');
  btn.disabled = true;
  btn.textContent = 'Testing…';
  el.style.display = 'none';
  try {
    // If company is already saved use the DB-aware endpoint; otherwise probe directly
    const r = id
      ? await Companies.testConnection(id)
      : await Companies.probe(host, port);

    el.style.display = 'block';
    if (r.success) {
      el.style.background    = 'var(--success-bg)';
      el.style.color         = 'var(--success-fg)';
      el.style.borderColor   = 'oklch(0.527 0.154 150 / 30%)';
      el.innerHTML = `✓ ${r.message}<br><small style="opacity:.7;">Open in Tally: ${r.open_companies.join(', ') || 'none detected'}</small>`;
      // Show Test Entry button only for saved companies with a successful connection
      if (id) document.getElementById('btn-test-entry').style.display = '';
    } else {
      el.style.background    = 'oklch(0.97 0.02 27)';
      el.style.color         = 'var(--destructive)';
      el.style.borderColor   = 'oklch(0.577 0.245 27 / 30%)';
      el.textContent = '✕ ' + r.message;
      document.getElementById('btn-test-entry').style.display = 'none';
    }
  } catch (err) { toast('Test error: ' + err.message, 'error'); }
  finally {
    btn.disabled = false;
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/></svg> Test Connection`;
  }
}

async function sendTestEntry() {
  const id = document.getElementById('edit-company-id').value;
  if (!id) { toast('Save the company first', 'warning'); return; }
  const btn = document.getElementById('btn-test-entry');
  btn.disabled = true;
  btn.textContent = 'Sending…';
  const el = document.getElementById('test-result');
  try {
    const r = await Companies.testEntry(id);
    el.style.display = 'block';
    if (r.success) {
      el.style.background  = 'var(--success-bg)';
      el.style.color       = 'var(--success-fg)';
      el.style.borderColor = 'oklch(0.527 0.154 150 / 30%)';
      el.innerHTML = `✓ Test entry created in Tally${r.tally_voucher_number ? ` — Voucher: <strong>${r.tally_voucher_number}</strong>` : ''}<br><small style="opacity:.7;">You can delete it from Tally after verification.</small>`;
    } else {
      el.style.background  = 'oklch(0.97 0.02 27)';
      el.style.color       = 'var(--destructive)';
      el.style.borderColor = 'oklch(0.577 0.245 27 / 30%)';
      el.textContent = '✕ ' + r.message;
    }
  } catch (err) { toast('Test entry failed: ' + err.message, 'error'); }
  finally {
    btn.disabled = false;
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 12l2 2 4-4"/><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/></svg> Send Test Entry`;
  }
}

function openGuide() {
  document.getElementById('probe-result').style.display = 'none';
  openModal('guide-modal');
}

async function probeConnection() {
  const host = document.getElementById('probe-host').value.trim() || 'localhost';
  const port = parseInt(document.getElementById('probe-port').value) || 9000;
  const btn  = document.getElementById('btn-probe');
  const el   = document.getElementById('probe-result');
  btn.disabled = true;
  btn.textContent = 'Testing…';
  el.style.display = 'none';
  try {
    const r = await Companies.probe(host, port);
    el.style.display = 'block';
    if (r.success) {
      el.style.background  = 'var(--success-bg)';
      el.style.color       = 'var(--success-fg)';
      el.style.borderColor = 'oklch(0.527 0.154 150 / 30%)';
      el.innerHTML = `✓ ${r.message}<br><small style="opacity:.7;">Open companies: ${r.open_companies.join(', ') || 'none detected'}</small>`;
    } else {
      el.style.background  = 'oklch(0.97 0.02 27)';
      el.style.color       = 'var(--destructive)';
      el.style.borderColor = 'oklch(0.577 0.245 27 / 30%)';
      el.textContent = '✕ ' + r.message;
    }
  } catch (err) { toast('Probe failed: ' + err.message, 'error'); }
  finally { btn.disabled = false; btn.textContent = 'Test Now'; }
}

async function deleteCompany(id) {
  if (!confirm('Delete this company and all its cached data? This cannot be undone.')) return;
  try { await Companies.delete(id); toast('Company deleted', 'info'); loadCompanies(); initCompanySelector(); }
  catch (err) { toast('Delete failed: ' + err.message, 'error'); }
}

async function triggerSync(id, btn) {
  btn.disabled = true; btn.textContent = '…';
  try { await Companies.sync(id); toast('Sync triggered', 'info'); }
  catch (err) { toast('Failed: ' + err.message, 'error'); }
  finally { setTimeout(() => { btn.disabled = false; btn.textContent = 'Sync'; }, 3000); }
}

async function viewSyncLogs(id) {
  document.getElementById('sync-logs-table').innerHTML = renderLoadingRow();
  openModal('sync-logs-modal');
  try {
    const logs = await Companies.syncLogs(id, 30);
    document.getElementById('sync-logs-table').innerHTML = logs.length
      ? logs.map(l => `<tr>
          <td>${l.sync_type}</td>
          <td>${statusBadge(l.status)}</td>
          <td class="text-right">${l.records_synced}</td>
          <td class="text-right text-muted text-xs">${l.duration_seconds != null ? l.duration_seconds.toFixed(1)+'s' : '—'}</td>
          <td class="text-muted text-xs">${fmt.datetime(l.started_at)}</td>
          <td class="text-xs text-destructive">${l.error_message || ''}</td>
        </tr>`).join('')
      : renderEmptyState('No sync logs yet');
  } catch (err) { document.getElementById('sync-logs-table').innerHTML = renderEmptyState('Failed: ' + err.message); }
}
