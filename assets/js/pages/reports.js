/**
 * TallySync Manager — Reports Page
 * Version: 1.0.0 | Build: 20260217.001
 */

let _reportChart = null;
let _reportData  = [];

function initReports() {
  // Set default date range (last 30 days)
  document.getElementById('report-from').value = daysAgo(29);
  document.getElementById('report-to').value   = today();

  document.getElementById('btn-run-report')?.addEventListener('click', runReport);
  document.getElementById('btn-export-report')?.addEventListener('click', () => {
    if (_reportData.length) exportCSV(_reportData, 'report.csv');
    else toast('Run a report first', 'warning');
  });
  document.getElementById('report-type')?.addEventListener('change', () => {
    const type = document.getElementById('report-type').value;
    const needsDates = ['sales', 'purchases', 'item-movement', 'party-sales'].includes(type);
    document.getElementById('report-from').style.display = needsDates ? '' : 'none';
    document.getElementById('report-to').style.display   = needsDates ? '' : 'none';
  });
}

async function runReport() {
  const companyId = CompanyStore.get();
  if (!companyId) { toast('Select a company first', 'warning'); return; }

  const type     = document.getElementById('report-type').value;
  const fromDate = document.getElementById('report-from').value;
  const toDate   = document.getElementById('report-to').value;

  if (fromDate && toDate && fromDate > toDate) {
    toast('"From" date must be on or before "To" date', 'warning');
    return;
  }

  const tbody = document.getElementById('report-tbody');
  tbody.innerHTML = `<tr><td colspan="10" class="text-center" style="padding:32px;"><span class="spinner"></span></td></tr>`;
  if (_reportChart) { _reportChart.destroy(); _reportChart = null; }

  try {
    switch (type) {
      case 'sales':            await renderSalesReport(companyId, fromDate, toDate);    break;
      case 'purchases':        await renderPurchasesReport(companyId, fromDate, toDate); break;
      case 'stock-summary':    await renderStockSummary(companyId);                      break;
      case 'low-stock':        await renderLowStock(companyId);                          break;
      case 'party-outstanding':await renderPartyOutstanding(companyId);                  break;
      case 'item-movement':    await renderItemMovement(companyId, fromDate, toDate);     break;
      case 'party-sales':      await renderPartySales(companyId, fromDate, toDate);       break;
    }
  } catch (err) {
    tbody.innerHTML = renderEmptyState('Error: ' + err.message);
    toast('Report failed: ' + err.message, 'error');
  }
}

// ── Report Renderers ──────────────────────────────────────────────────────────

async function renderSalesReport(companyId, from, to) {
  const data = await Reports.sales(companyId, { from_date: from, to_date: to });
  _reportData = data;

  document.getElementById('report-chart-title').textContent = 'Sales Trend';
  document.getElementById('report-table-title').textContent = 'Daily Sales';

  renderLineChart(
    data.map(d => d.date.slice(5)),
    [{ name: 'Sales (₹)', data: data.map(d => d.total_amount) }],
    '#18181b'
  );

  document.getElementById('report-thead').innerHTML = `<tr><th>Date</th><th class="text-right">Orders</th><th class="text-right">Total Amount</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr><td>${fmt.date(d.date)}</td><td class="text-right">${d.order_count}</td><td class="text-right amount">${fmt.currency(d.total_amount)}</td></tr>`).join('')
      + `<tr style="font-weight:700;background:var(--bg);">
           <td>Total</td><td class="text-right">${data.reduce((s,d)=>s+d.order_count,0)}</td>
           <td class="text-right amount">${fmt.currency(data.reduce((s,d)=>s+d.total_amount,0))}</td>
         </tr>`
    : renderEmptyState('No sales data for this period');
}

async function renderPurchasesReport(companyId, from, to) {
  const data = await Reports.purchases(companyId, { from_date: from, to_date: to });
  _reportData = data;

  document.getElementById('report-chart-title').textContent = 'Purchase Trend';
  document.getElementById('report-table-title').textContent = 'Daily Purchases';

  renderLineChart(
    data.map(d => d.date.slice(5)),
    [{ name: 'Purchases (₹)', data: data.map(d => d.total_amount) }],
    '#16a34a'
  );

  document.getElementById('report-thead').innerHTML = `<tr><th>Date</th><th class="text-right">Orders</th><th class="text-right">Total Amount</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr><td>${fmt.date(d.date)}</td><td class="text-right">${d.order_count}</td><td class="text-right amount">${fmt.currency(d.total_amount)}</td></tr>`).join('')
    : renderEmptyState('No purchase data for this period');
}

async function renderStockSummary(companyId) {
  const data = await Reports.stockSummary(companyId);
  _reportData = data;

  document.getElementById('report-chart-title').textContent = 'Stock Value by Group';
  document.getElementById('report-table-title').textContent = 'Stock Summary by Group';

  renderDonutChart(data.map(d => d.group), data.map(d => d.total_value));

  document.getElementById('report-thead').innerHTML = `<tr><th>Group</th><th class="text-right">Items</th><th class="text-right">Total Value (₹)</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr><td>${esc(d.group)}</td><td class="text-right">${d.item_count}</td><td class="text-right amount">${fmt.currency(d.total_value)}</td></tr>`).join('')
    : renderEmptyState('No stock data');
}

async function renderLowStock(companyId) {
  const data = await Reports.lowStock(companyId);
  _reportData = data;
  document.getElementById('report-chart-title').textContent = 'Low Stock Items';
  document.getElementById('report-table-title').textContent = `Low Stock Items (${data.length})`;
  document.getElementById('report-chart').innerHTML = '<div class="flex-center" style="height:120px;color:var(--text-muted);">📦 See table below for details</div>';
  document.getElementById('report-thead').innerHTML = `<tr><th>Item Name</th><th>Group</th><th>UOM</th><th class="text-right">Current Qty</th><th class="text-right">Reorder Level</th><th class="text-right">Deficit</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr>
        <td class="fw-600">${esc(d.name)}</td>
        <td>${esc(d.group) || '—'}</td><td>${esc(d.uom) || '—'}</td>
        <td class="text-right danger amount">${fmt.number(d.closing_qty, 4)}</td>
        <td class="text-right amount">${fmt.number(d.reorder_level, 4)}</td>
        <td class="text-right danger amount">${fmt.number(d.deficit, 4)}</td>
      </tr>`).join('')
    : renderEmptyState('No low stock items 👍');
}

async function renderPartyOutstanding(companyId) {
  const data = await Reports.partyOutstanding(companyId);
  _reportData = data;
  document.getElementById('report-chart-title').textContent = 'Party Outstanding';
  document.getElementById('report-table-title').textContent = 'Outstanding Balances';
  document.getElementById('report-chart').innerHTML = '<div class="flex-center" style="height:120px;color:var(--text-muted);">🏦 Ledger balances from last Tally sync</div>';
  document.getElementById('report-thead').innerHTML = `<tr><th>Party Name</th><th>Type</th><th class="text-right">Closing Balance (₹)</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr>
        <td class="fw-600">${esc(d.party_name)}</td>
        <td><span class="badge ${d.ledger_type === 'CUSTOMER' ? 'badge-info' : 'badge-warning'}">${esc(d.ledger_type)}</span></td>
        <td class="text-right amount ${d.closing_balance < 0 ? 'danger' : ''}">${fmt.currency(Math.abs(d.closing_balance))}</td>
      </tr>`).join('')
    : renderEmptyState('No outstanding data');
}

async function renderItemMovement(companyId, from, to) {
  const data = await Reports.itemMovement(companyId, { from_date: from, to_date: to, limit: 20 });
  _reportData = data;
  document.getElementById('report-chart-title').textContent = 'Top Items by Movement';
  document.getElementById('report-table-title').textContent = 'Item Movement';

  renderBarChart(data.map(d => d.name), data.map(d => d.total_amount));

  document.getElementById('report-thead').innerHTML = `<tr><th>Item Name</th><th class="text-right">Orders</th><th class="text-right">Total Qty</th><th class="text-right">Total Amount</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr>
        <td class="fw-600">${esc(d.name)}</td>
        <td class="text-right">${d.order_count}</td>
        <td class="text-right amount">${fmt.number(d.total_qty, 4)}</td>
        <td class="text-right amount">${fmt.currency(d.total_amount)}</td>
      </tr>`).join('')
    : renderEmptyState('No movement data');
}

async function renderPartySales(companyId, from, to) {
  const data = await Reports.partySales(companyId, { from_date: from, to_date: to });
  _reportData = data;
  document.getElementById('report-chart-title').textContent = 'Top Parties by Sales';
  document.getElementById('report-table-title').textContent = 'Party-wise Sales';

  renderBarChart(data.map(d => d.party), data.map(d => d.total_amount), '#2563eb');

  document.getElementById('report-thead').innerHTML = `<tr><th>Party</th><th class="text-right">Orders</th><th class="text-right">Total Amount</th></tr>`;
  document.getElementById('report-tbody').innerHTML = data.length
    ? data.map(d => `<tr>
        <td class="fw-600">${esc(d.party)}</td>
        <td class="text-right">${d.order_count}</td>
        <td class="text-right amount">${fmt.currency(d.total_amount)}</td>
      </tr>`).join('')
    : renderEmptyState('No party sales data');
}

// ── Chart Helpers ─────────────────────────────────────────────────────────────

function renderLineChart(categories, series, color) {
  if (_reportChart) { _reportChart.destroy(); }
  _reportChart = new ApexCharts(document.getElementById('report-chart'), {
    chart: { type: 'area', height: 280, fontFamily: "'Inter', sans-serif", toolbar: { show: false }, background: 'transparent' },
    series, colors: [color],
    xaxis: { categories, labels: { style: { fontSize: '11px', colors: '#a1a1aa' } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { fontSize: '11px', colors: '#a1a1aa' }, formatter: v => '₹' + (v >= 1e5 ? (v/1e5).toFixed(1)+'L' : v.toFixed(0)) } },
    fill:  { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.18, opacityTo: 0.0, stops: [0, 95] } },
    stroke: { curve: 'smooth', width: 2 },
    grid:  { borderColor: '#f0f0f0', strokeDashArray: 3, padding: { left: 4, right: 4 } },
    dataLabels: { enabled: false },
    markers: { size: 0, hover: { size: 4 } },
    tooltip: { theme: 'light', y: { formatter: v => fmt.currency(v) } },
  });
  _reportChart.render();
}

function renderDonutChart(labels, series) {
  if (_reportChart) { _reportChart.destroy(); }
  _reportChart = new ApexCharts(document.getElementById('report-chart'), {
    chart: { type: 'donut', height: 280, fontFamily: "'Inter', sans-serif", background: 'transparent' },
    series, labels,
    legend: { position: 'bottom', fontSize: '11px', labels: { colors: '#71717a' } },
    dataLabels: { enabled: false },
    plotOptions: { pie: { donut: { size: '62%' } } },
    colors: ['#18181b','#3f3f46','#52525b','#71717a','#a1a1aa','#d4d4d8','#16a34a','#2563eb'],
    stroke: { width: 0 },
    tooltip: { y: { formatter: v => fmt.currency(v) } },
  });
  _reportChart.render();
}

function renderBarChart(categories, data, color = '#18181b') {
  if (_reportChart) { _reportChart.destroy(); }
  _reportChart = new ApexCharts(document.getElementById('report-chart'), {
    chart: { type: 'bar', height: 280, fontFamily: "'Inter', sans-serif", toolbar: { show: false }, background: 'transparent' },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '55%' } },
    series: [{ name: 'Amount', data }],
    colors: [color],
    xaxis: {
      categories: categories.map(c => c.length > 22 ? c.slice(0, 20) + '…' : c),
      labels: { style: { fontSize: '11px', colors: '#a1a1aa' }, formatter: v => '₹' + (v >= 1e5 ? (v/1e5).toFixed(1)+'L' : Number(v).toFixed(0)) },
      axisBorder: { show: false }, axisTicks: { show: false },
    },
    dataLabels: { enabled: false },
    grid: { borderColor: '#f0f0f0', strokeDashArray: 3 },
    tooltip: { theme: 'light', y: { formatter: v => fmt.currency(v) } },
  });
  _reportChart.render();
}
