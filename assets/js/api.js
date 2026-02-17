/**
 * TallySync Manager — API Client
 * Version: 1.0.0 | Build: 20260217.001
 *
 * All fetch calls to the FastAPI backend go through here.
 * Reads the selected company from localStorage automatically.
 */

const API_BASE = window.TALLYSYNC_API || 'http://localhost:8001';

// ── Core Fetch ────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}, _retry = true) {
  const url = `${API_BASE}${path}`;
  const apiKey = localStorage.getItem('tallysync_api_key') || '';
  const defaults = {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey, ...(options.headers || {}) },
  };
  const response = await fetch(url, { ...defaults, ...options });

  // Auto-heal stale API key: refresh from /api/info and retry once
  if (response.status === 401 && _retry) {
    try {
      const infoRes = await fetch(`${API_BASE}/api/info`, { signal: AbortSignal.timeout(3000) });
      if (infoRes.ok) {
        const info = await infoRes.json();
        if (info.api_key) {
          localStorage.setItem('tallysync_api_key', info.api_key);
          return apiFetch(path, options, false); // retry once with new key
        }
      }
    } catch (_) {}
  }

  if (!response.ok) {
    let errorMsg = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      errorMsg = body.detail || body.message || errorMsg;
    } catch (_) {}
    throw new Error(errorMsg);
  }

  // 204 No Content
  if (response.status === 204) return null;
  return response.json();
}

const api = {
  get:    (path)         => apiFetch(path),
  post:   (path, body)   => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) }),
  put:    (path, body)   => apiFetch(path, { method: 'PUT',    body: JSON.stringify(body) }),
  patch:  (path, body)   => apiFetch(path, { method: 'PATCH',  body: JSON.stringify(body) }),
  delete: (path)         => apiFetch(path, { method: 'DELETE' }),
};

// Like apiFetch but also returns the X-Total-Count header value as `total`.
// Used by paginated endpoints so callers get { data: [...], total: N }.
async function apiFetchWithCount(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const apiKey = localStorage.getItem('tallysync_api_key') || '';
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey, ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let errorMsg = `HTTP ${response.status}`;
    try { const body = await response.json(); errorMsg = body.detail || body.message || errorMsg; } catch (_) {}
    throw new Error(errorMsg);
  }
  const data   = response.status === 204 ? null : await response.json();
  const total  = parseInt(response.headers.get('X-Total-Count') || '0', 10);
  return { data, total };
}

// ── Helper: build query string ────────────────────────────────────────────────

function buildQuery(params = {}) {
  const q = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  return q ? `?${q}` : '';
}

// ── App Info ──────────────────────────────────────────────────────────────────

const Info = {
  get: () => api.get('/api/info'),
};

// ── Companies ─────────────────────────────────────────────────────────────────

const Companies = {
  list:           ()        => api.get('/api/companies'),
  get:            (id)      => api.get(`/api/companies/${id}`),
  create:         (data)    => api.post('/api/companies', data),
  update:         (id, data)=> api.put(`/api/companies/${id}`, data),
  delete:         (id)      => api.delete(`/api/companies/${id}`),
  testConnection: (id)      => api.post(`/api/companies/${id}/test-connection`),
  probe:          (host, port) => api.post('/api/probe', { host, port }),
  testEntry:      (id)      => api.post(`/api/companies/${id}/test-entry`),
  sync:           (id)      => api.post(`/api/companies/${id}/sync`),
  syncLogs:       (id, limit=20) => api.get(`/api/companies/${id}/sync-logs?limit=${limit}`),
};

// ── Inventory ─────────────────────────────────────────────────────────────────

const Inventory = {
  list:   (params) => api.get(`/api/inventory${buildQuery(params)}`),
  get:    (id)     => api.get(`/api/inventory/${id}`),
  groups: (companyId) => api.get(`/api/inventory/meta/groups?company_id=${companyId}`),
  stats:  (companyId) => api.get(`/api/inventory/meta/stats?company_id=${companyId}`),
  setReorderLevel: (id, level) => api.patch(`/api/inventory/${id}/reorder-level?reorder_level=${level}`),
  search: (companyId, q, limit = 30) => api.get(`/api/inventory/search?company_id=${encodeURIComponent(companyId)}&q=${encodeURIComponent(q)}&limit=${limit}`),
};

// ── Ledgers ───────────────────────────────────────────────────────────────────

const Ledgers = {
  list: (params) => api.get(`/api/ledgers${buildQuery(params)}`),
  get:  (id)     => api.get(`/api/ledgers/${id}`),
};

// ── Orders ────────────────────────────────────────────────────────────────────

const Orders = {
  list:   (params) => apiFetchWithCount(`/api/orders${buildQuery(params)}`),
  get:    (id)     => api.get(`/api/orders/${id}`),
  create: (data)   => api.post('/api/orders', data),
  update: (id, data) => api.put(`/api/orders/${id}`, data),
  delete: (id)     => api.delete(`/api/orders/${id}`),
  push:   (id)     => api.post(`/api/orders/${id}/push`),
};

// ── Vouchers ──────────────────────────────────────────────────────────────────

const Vouchers = {
  list:  (params) => api.get(`/api/vouchers${buildQuery(params)}`),
  get:   (id)     => api.get(`/api/vouchers/${id}`),
  types: (companyId) => api.get(`/api/vouchers/meta/types?company_id=${companyId}`),
};

// ── Reports ───────────────────────────────────────────────────────────────────

const Reports = {
  dashboard:       (companyId)         => api.get(`/api/reports/dashboard?company_id=${companyId}`),
  sales:           (companyId, params) => api.get(`/api/reports/sales${buildQuery({ company_id: companyId, ...params })}`),
  purchases:       (companyId, params) => api.get(`/api/reports/purchases${buildQuery({ company_id: companyId, ...params })}`),
  stockSummary:    (companyId)         => api.get(`/api/reports/stock-summary?company_id=${companyId}`),
  lowStock:        (companyId)         => api.get(`/api/reports/low-stock?company_id=${companyId}`),
  partyOutstanding:(companyId, type)   => api.get(`/api/reports/party-outstanding${buildQuery({ company_id: companyId, ledger_type: type })}`),
  itemMovement:    (companyId, params) => api.get(`/api/reports/item-movement${buildQuery({ company_id: companyId, ...params })}`),
  partySales:      (companyId, params) => api.get(`/api/reports/party-sales${buildQuery({ company_id: companyId, ...params })}`),
  creditorsAging:  (companyId)         => api.get(`/api/reports/creditors-aging?company_id=${companyId}`),
};
