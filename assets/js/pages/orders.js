/**
 * TallySync Manager — Orders Page
 * Version: 1.0.0 | Build: 20260217.001
 */

let _ordersData = [];

async function initOrders() {
  const companyId = CompanyStore.get();
  if (!companyId) return;
  await loadOrders();
  await populateDataLists(companyId);
  setupOrderEvents();
}

async function loadOrders() {
  const companyId = CompanyStore.get();
  if (!companyId) return;
  document.getElementById('orders-table-body').innerHTML = renderLoadingRow();

  try {
    _ordersData = await Orders.list({
      company_id:  companyId,
      order_type:  document.getElementById('order-type-filter')?.value || undefined,
      status:      document.getElementById('order-status-filter')?.value || undefined,
      from_date:   document.getElementById('order-from')?.value || undefined,
      to_date:     document.getElementById('order-to')?.value || undefined,
      party_name:  document.getElementById('order-search')?.value || undefined,
    });
    renderOrdersTable(_ordersData);
  } catch (err) {
    document.getElementById('orders-table-body').innerHTML = renderEmptyState('Failed: ' + err.message);
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById('orders-table-body');
  if (!orders.length) { tbody.innerHTML = renderEmptyState('No orders found'); return; }

  tbody.innerHTML = orders.map(o => `<tr>
    <td class="mono fw-600">${o.order_number}</td>
    <td><span class="badge ${o.order_type === 'SALES' ? 'badge-secondary' : 'badge-outline'}">${o.order_type}</span></td>
    <td class="text-muted">${fmt.date(o.order_date)}</td>
    <td class="fw-500">${o.party_name}</td>
    <td class="text-right amount">${fmt.currency(o.total_amount)}</td>
    <td>${statusBadge(o.status)}</td>
    <td class="mono text-muted text-xs">${o.tally_voucher_number || '—'}</td>
    <td>
      <div class="flex gap-2">
        ${o.status !== 'PUSHED' && o.status !== 'CANCELLED'
          ? `<button class="btn btn-outline btn-sm" onclick="editOrder(${o.id})">Edit</button>` : ''}
        ${o.status === 'CONFIRMED'
          ? `<button class="btn btn-primary btn-sm" onclick="pushOrder(${o.id}, this)">Push</button>` : ''}
        ${o.status === 'DRAFT'
          ? `<button class="btn btn-ghost btn-sm text-destructive" onclick="deleteOrder(${o.id})">Delete</button>` : ''}
      </div>
    </td>
  </tr>`).join('');
}

async function populateDataLists(companyId) {
  try {
    const [ledgers, stock] = await Promise.all([
      Ledgers.list({ company_id: companyId, limit: 500 }),
      Inventory.list({ company_id: companyId, limit: 1000 }),
    ]);
    const pd = document.getElementById('party-datalist');
    if (pd) pd.innerHTML = ledgers.map(l => `<option value="${l.tally_name}">`).join('');
    const sd = document.getElementById('stock-datalist');
    if (sd) sd.innerHTML = stock.map(s => `<option value="${s.tally_name}" data-uom="${s.uom||'Nos'}" data-rate="${s.rate}">`).join('');
  } catch (_) {}
}

function setupOrderEvents() {
  ['order-type-filter','order-status-filter','order-from','order-to'].forEach(id => {
    const el = document.getElementById(id);
    if (el && !el._bound) { el._bound = true; el.addEventListener('change', loadOrders); }
  });
  const s = document.getElementById('order-search');
  if (s && !s._bound) { s._bound = true; s.addEventListener('input', debounce(loadOrders, 400)); }

  document.getElementById('btn-new-order')?.addEventListener('click', openNewOrderModal);
  document.getElementById('btn-add-item')?.addEventListener('click', () => addItemRow());
  document.getElementById('btn-save-draft')?.addEventListener('click', () => saveOrder('DRAFT'));
  document.getElementById('btn-save-confirm')?.addEventListener('click', () => saveOrder('CONFIRMED'));
  document.getElementById('btn-export-orders')?.addEventListener('click', () =>
    exportCSV(_ordersData.map(o => ({ No: o.order_number, Type: o.order_type, Date: o.order_date, Party: o.party_name, Amount: o.total_amount, Status: o.status, TallyVoucher: o.tally_voucher_number })), 'orders.csv'));
}

// ── Modal ──────────────────────────────────────────────────────────────────────

function openNewOrderModal() {
  document.getElementById('order-modal-title').textContent = 'New Order';
  document.getElementById('edit-order-id').value = '';
  document.getElementById('order-type').value = 'SALES';
  document.getElementById('order-date').value = today();
  document.getElementById('order-party').value = '';
  document.getElementById('order-narration').value = '';
  document.getElementById('order-items-body').innerHTML = '';
  document.getElementById('order-total').textContent = '₹0.00';
  addItemRow();
  openModal('order-modal');
}

async function editOrder(id) {
  try {
    const o = await Orders.get(id);
    document.getElementById('order-modal-title').textContent = `Edit — ${o.order_number}`;
    document.getElementById('edit-order-id').value = id;
    document.getElementById('order-type').value = o.order_type;
    document.getElementById('order-date').value = o.order_date;
    document.getElementById('order-party').value = o.party_name;
    document.getElementById('order-narration').value = o.narration || '';
    document.getElementById('order-items-body').innerHTML = '';
    o.items.forEach(item => addItemRow(item));
    recalcTotal();
    openModal('order-modal');
  } catch (err) { toast('Failed to load order: ' + err.message, 'error'); }
}

function addItemRow(item = null) {
  const tpl   = document.getElementById('order-item-row-tpl');
  const clone = tpl.content.cloneNode(true);
  const tbody = document.getElementById('order-items-body');

  if (item) {
    clone.querySelector('.item-name').value = item.stock_item_name;
    clone.querySelector('.item-uom').value  = item.uom || '';
    clone.querySelector('.item-qty').value  = item.quantity;
    clone.querySelector('.item-rate').value = item.rate;
    clone.querySelector('.item-amount').textContent = fmt.number(item.amount);
  }

  const row = clone.querySelector('.order-item-row');

  clone.querySelector('.item-name').addEventListener('change', function () {
    const opt = document.querySelector(`#stock-datalist option[value="${this.value}"]`);
    if (opt) {
      const r = this.closest('tr');
      r.querySelector('.item-uom').value  = opt.dataset.uom || 'Nos';
      r.querySelector('.item-rate').value = opt.dataset.rate || '';
      recalcRow(r);
    }
  });
  ['item-qty','item-rate'].forEach(cls =>
    clone.querySelector('.' + cls).addEventListener('input', function () { recalcRow(this.closest('tr')); }));
  clone.querySelector('.btn-remove-item').addEventListener('click', function () {
    this.closest('tr').remove(); recalcTotal();
  });

  tbody.appendChild(clone);
}

function recalcRow(row) {
  const qty  = parseFloat(row.querySelector('.item-qty').value)  || 0;
  const rate = parseFloat(row.querySelector('.item-rate').value) || 0;
  row.querySelector('.item-amount').textContent = fmt.number(qty * rate);
  recalcTotal();
}

function recalcTotal() {
  let total = 0;
  document.querySelectorAll('.item-amount').forEach(el => { total += parseFloat(el.textContent.replace(/,/g,'')) || 0; });
  document.getElementById('order-total').textContent = fmt.currency(total);
}

function collectItems() {
  return [...document.querySelectorAll('.order-item-row')].map(row => ({
    stock_item_name: row.querySelector('.item-name').value.trim(),
    quantity:        parseFloat(row.querySelector('.item-qty').value),
    rate:            parseFloat(row.querySelector('.item-rate').value),
    uom:             row.querySelector('.item-uom').value.trim() || 'Nos',
  })).filter(i => i.stock_item_name && !isNaN(i.quantity) && !isNaN(i.rate) && i.quantity > 0 && i.rate > 0);
}

async function saveOrder(status) {
  const companyId = CompanyStore.get();
  const editId    = document.getElementById('edit-order-id').value;
  const party     = document.getElementById('order-party').value.trim();
  const items     = collectItems();

  if (!party)        { toast('Party name is required', 'warning'); return; }
  if (!items.length) { toast('Add at least one line item', 'warning'); return; }

  const payload = {
    company_id: companyId,
    order_type: document.getElementById('order-type').value,
    order_date: document.getElementById('order-date').value,
    party_name: party,
    narration:  document.getElementById('order-narration').value.trim(),
    items,
    status,
  };

  try {
    if (editId) { await Orders.update(editId, { ...payload, company_id: undefined }); toast('Order updated', 'success'); }
    else        { await Orders.create(payload); toast('Order created', 'success'); }
    closeModal('order-modal');
    loadOrders();
  } catch (err) { toast('Save failed: ' + err.message, 'error'); }
}

async function pushOrder(id, btn) {
  btn.disabled = true; btn.textContent = '…';
  try {
    const r = await Orders.push(id);
    toast(r.success ? `Pushed! Voucher: ${r.tally_voucher_number || 'N/A'}` : 'Push failed: ' + r.message, r.success ? 'success' : 'error', 5000);
    loadOrders();
  } catch (err) {
    toast('Error: ' + err.message, 'error');
    btn.disabled = false; btn.textContent = 'Push';
  }
}

async function deleteOrder(id) {
  if (!confirm('Delete this draft order?')) return;
  try { await Orders.delete(id); toast('Deleted', 'info'); loadOrders(); }
  catch (err) { toast('Failed: ' + err.message, 'error'); }
}
