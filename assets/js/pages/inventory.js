/**
 * TallySync Manager — Inventory Page
 * Version: 1.0.0 | Build: 20260217.001
 */

let _invData = [];
let _reorderItemId = null;

async function initInventory() {
  const companyId = CompanyStore.get();
  if (!companyId) return;

  try {
    const [stats, groups] = await Promise.all([
      Inventory.stats(companyId),
      Inventory.groups(companyId),
    ]);

    document.getElementById('inv-total').textContent    = stats.total_items;
    document.getElementById('inv-lowstock').textContent = stats.low_stock_count;
    document.getElementById('inv-value').textContent    = fmt.currency(stats.total_value);
    document.getElementById('inv-groups').textContent   = stats.groups.length;

    const gf = document.getElementById('inv-group-filter');
    gf.innerHTML = '<option value="">All Groups</option>' +
      groups.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
    CustomSelect.refresh('inv-group-filter');
  } catch (_) {}

  await loadInventory();
  setupInventoryEvents();
}

async function loadInventory() {
  const companyId = CompanyStore.get();
  if (!companyId) return;

  document.getElementById('inv-table-body').innerHTML = renderLoadingRow();

  try {
    _invData = await Inventory.list({
      company_id: companyId,
      search:     document.getElementById('inv-search')?.value || undefined,
      group:      document.getElementById('inv-group-filter')?.value || undefined,
      low_stock:  document.getElementById('inv-low-stock-filter')?.checked || undefined,
      limit:      500,
    });
    renderInventoryTable(_invData);
  } catch (err) {
    document.getElementById('inv-table-body').innerHTML = renderEmptyState('Failed to load: ' + err.message);
  }
}

function renderInventoryTable(items) {
  const tbody = document.getElementById('inv-table-body');
  if (!items.length) { tbody.innerHTML = renderEmptyState('No stock items found'); return; }

  tbody.innerHTML = items.map(i => `
    <tr>
      <td class="fw-600">${esc(i.tally_name)}</td>
      <td class="text-muted text-sm">${esc(i.alias) || '—'}</td>
      <td class="text-muted">${esc(i.group_name) || '—'}</td>
      <td class="text-muted">${esc(i.uom) || '—'}</td>
      <td class="text-right amount ${i.is_low_stock ? 'text-destructive' : ''}">${fmt.number(i.closing_qty, 4)}</td>
      <td class="text-right amount">${fmt.currency(i.closing_value)}</td>
      <td class="text-right amount">${fmt.currency(i.rate)}</td>
      <td class="text-right" style="white-space:nowrap;">
        <span class="amount">${fmt.number(i.reorder_level, 4)}</span>
        <button class="btn-icon sm" title="Edit reorder level"
          data-id="${esc(String(i.id))}" data-name="${esc(i.tally_name)}" data-level="${esc(String(i.reorder_level))}"
          onclick="openReorderModal(this)">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
        </button>
      </td>
      <td>${i.is_low_stock
        ? '<span class="badge badge-danger">Low</span>'
        : '<span class="badge badge-success">OK</span>'}</td>
    </tr>`).join('');
}

function setupInventoryEvents() {
  const searchEl = document.getElementById('inv-search');
  if (searchEl && !searchEl._bound) { searchEl._bound = true; searchEl.addEventListener('input', debounce(loadInventory, 400)); }

  const gf = document.getElementById('inv-group-filter');
  if (gf && !gf._bound) { gf._bound = true; gf.addEventListener('change', loadInventory); }

  const lsf = document.getElementById('inv-low-stock-filter');
  if (lsf && !lsf._bound) { lsf._bound = true; lsf.addEventListener('change', loadInventory); }

  document.getElementById('btn-refresh-inv')?.addEventListener('click', () => {
    const id = CompanyStore.get();
    if (id) Companies.sync(id).then(() => toast('Sync triggered', 'info'));
  });

  document.getElementById('btn-export-inv')?.addEventListener('click', () =>
    exportCSV(_invData.map(i => ({ Name: i.tally_name, Alias: i.alias, Group: i.group_name, UOM: i.uom, Qty: i.closing_qty, Value: i.closing_value, Rate: i.rate, ReorderLevel: i.reorder_level })), 'inventory.csv'));

  document.getElementById('btn-save-reorder')?.addEventListener('click', async () => {
    const level = parseFloat(document.getElementById('reorder-level-input').value);
    if (isNaN(level) || level < 0) { toast('Enter a valid reorder level', 'warning'); return; }
    try {
      await Inventory.setReorderLevel(_reorderItemId, level);
      closeModal('reorder-modal');
      toast('Reorder level saved', 'success');
      loadInventory();
    } catch (err) { toast('Failed: ' + err.message, 'error'); }
  });
}

function openReorderModal(btn) {
  _reorderItemId = parseInt(btn.dataset.id);
  document.getElementById('reorder-item-name').textContent = btn.dataset.name;
  document.getElementById('reorder-level-input').value = btn.dataset.level;
  openModal('reorder-modal');
}
