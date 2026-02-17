/**
 * TallySync Manager — Dashboard Page
 * Version: 1.0.0 | Build: 20260217.001
 */

let _salesChart, _purchaseChart, _stockChart, _movementChart;

const CHART_BASE = {
  chart:      { fontFamily: "'Inter', ui-sans-serif, sans-serif", toolbar: { show: false }, height: 220, background: 'transparent', sparkline: { enabled: false } },
  grid:       { borderColor: '#f0f0f0', strokeDashArray: 3, padding: { left: 4, right: 4 } },
  dataLabels: { enabled: false },
  xaxis:      {
    labels: { style: { fontSize: '11px', colors: '#a1a1aa' } },
    axisBorder: { show: false }, axisTicks: { show: false },
  },
  yaxis:      {
    labels: { style: { fontSize: '11px', colors: '#a1a1aa' }, formatter: v => '₹' + (v >= 1e5 ? (v/1e5).toFixed(1)+'L' : Number(v).toFixed(0)) },
  },
  tooltip:    { theme: 'light', y: { formatter: v => fmt.currency(v) } },
  markers:    { size: 0, hover: { size: 4 } },
};

async function initDashboard() {
  const companyId = CompanyStore.get();
  if (!companyId) return;

  try {
    const [kpi, sales, purchases, stockGroups, movement] = await Promise.all([
      Reports.dashboard(companyId),
      Reports.sales(companyId, { from_date: daysAgo(29), to_date: today() }),
      Reports.purchases(companyId, { from_date: daysAgo(29), to_date: today() }),
      Reports.stockSummary(companyId),
      Reports.itemMovement(companyId, { days: 30, limit: 10 }),
    ]);

    document.getElementById('kpi-orders').textContent   = kpi.total_orders_today;
    document.getElementById('kpi-sales').textContent    = fmt.currency(kpi.total_sales_today);
    document.getElementById('kpi-purchase').textContent = fmt.currency(kpi.total_purchase_today);
    document.getElementById('kpi-pending').textContent  = kpi.pending_orders;
    document.getElementById('kpi-lowstock').textContent = kpi.low_stock_items;
    document.getElementById('kpi-invvalue').textContent = fmt.currency(kpi.total_inventory_value);
    document.getElementById('kpi-synced').textContent   = fmt.relativeTime(kpi.recent_synced_at);

    renderSalesChart(sales);
    renderPurchaseChart(purchases);
    renderStockChart(stockGroups);
    renderMovementChart(movement);

    const lowStock = await Reports.lowStock(companyId);
    renderLowStockTable(lowStock);
  } catch (err) {
    toast('Failed to load dashboard: ' + err.message, 'error');
  }
}

function renderSalesChart(data) {
  if (_salesChart) _salesChart.destroy();
  const el = document.getElementById('chart-sales');
  if (!el) return;
  _salesChart = new ApexCharts(el, {
    ...CHART_BASE,
    chart: { ...CHART_BASE.chart, type: 'area' },
    series: [{ name: 'Sales (₹)', data: data.map(d => parseFloat(d.total_amount)) }],
    xaxis: { ...CHART_BASE.xaxis, categories: data.map(d => d.date.slice(5)) },
    colors: ['#18181b'],
    fill:   { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.18, opacityTo: 0.0, stops: [0, 95] } },
    stroke: { curve: 'smooth', width: 2 },
  });
  _salesChart.render();
}

function renderPurchaseChart(data) {
  if (_purchaseChart) _purchaseChart.destroy();
  const el = document.getElementById('chart-purchases');
  if (!el) return;
  _purchaseChart = new ApexCharts(el, {
    ...CHART_BASE,
    chart: { ...CHART_BASE.chart, type: 'area' },
    series: [{ name: 'Purchases (₹)', data: data.map(d => parseFloat(d.total_amount)) }],
    xaxis: { ...CHART_BASE.xaxis, categories: data.map(d => d.date.slice(5)) },
    colors: ['#16a34a'],
    fill:   { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.18, opacityTo: 0.0, stops: [0, 95] } },
    stroke: { curve: 'smooth', width: 2 },
  });
  _purchaseChart.render();
}

function renderStockChart(data) {
  if (_stockChart) _stockChart.destroy();
  const el = document.getElementById('chart-stock');
  if (!el || !data.length) return;
  const top = data.slice(0, 8);
  _stockChart = new ApexCharts(el, {
    chart: { type: 'donut', height: 220, fontFamily: "'Inter', sans-serif" },
    series: top.map(d => d.total_value),
    labels: top.map(d => d.group),
    legend: { position: 'bottom', fontSize: '11px', fontFamily: "'Inter', sans-serif", labels: { colors: '#71717a' } },
    dataLabels: { enabled: false },
    tooltip:    { y: { formatter: v => fmt.currency(v) } },
    plotOptions: { pie: { donut: { size: '62%', labels: { show: false } } } },
    colors: ['#18181b','#3f3f46','#52525b','#71717a','#a1a1aa','#d4d4d8','#e4e4e7','#f4f4f5'],
    stroke: { width: 0 },
  });
  _stockChart.render();
}

function renderMovementChart(data) {
  if (_movementChart) _movementChart.destroy();
  const el = document.getElementById('chart-movement');
  if (!el || !data.length) return;
  _movementChart = new ApexCharts(el, {
    ...CHART_BASE,
    chart: { ...CHART_BASE.chart, type: 'bar' },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '55%' } },
    series: [{ name: 'Amount', data: data.map(d => d.total_amount) }],
    xaxis: { ...CHART_BASE.xaxis, categories: data.map(d => d.name.length > 22 ? d.name.slice(0,20)+'…' : d.name) },
    colors: ['#18181b'],
  });
  _movementChart.render();
}

function renderLowStockTable(items) {
  const tbody = document.getElementById('low-stock-table');
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="padding:2rem;text-align:center;color:var(--muted-foreground);">
      No low stock items — inventory levels are healthy</td></tr>`;
    return;
  }
  tbody.innerHTML = items.slice(0, 8).map(i => `
    <tr>
      <td class="fw-600">${i.name}</td>
      <td class="text-muted">${i.group || '—'}</td>
      <td>${i.uom || '—'}</td>
      <td class="text-right amount text-destructive">${fmt.number(i.closing_qty, 4)}</td>
      <td class="text-right amount">${fmt.number(i.reorder_level, 4)}</td>
      <td class="text-right amount text-destructive">${fmt.number(i.deficit, 4)}</td>
    </tr>`).join('');
}
