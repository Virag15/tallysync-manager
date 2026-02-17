/**
 * TallySync Manager — SSE Sync Client
 * Version: 1.0.0 | Build: 20260217.001
 *
 * Opens a Server-Sent Events connection to /api/events.
 * Handles reconnects and fires custom DOM events on sync completion.
 */

const SSE_URL = `${API_BASE}/api/events`;
const RETRY_DELAY_MS = 5000;

let _sse = null;
let _retryTimer = null;

function getSyncDot()  { return document.getElementById('sync-dot'); }
function getSyncText() { return document.getElementById('sync-text'); }

function setSyncStatus(state, text) {
  const dot  = getSyncDot();
  const label = getSyncText();
  if (dot)   { dot.className = `sync-dot${state ? ' ' + state : ''}`; }
  if (label) { label.textContent = text; }
}

function connectSSE() {
  if (_sse) { _sse.close(); _sse = null; }

  const companyId = CompanyStore.get();
  const url = companyId ? `${SSE_URL}?company_id=${companyId}` : SSE_URL;

  setSyncStatus('syncing', 'Connecting...');

  _sse = new EventSource(url);

  _sse.addEventListener('connected', () => {
    setSyncStatus('', 'Live');
    clearTimeout(_retryTimer);
  });

  _sse.addEventListener('sync_complete', (e) => {
    const data = JSON.parse(e.data);
    setSyncStatus('', `Synced ${fmt.relativeTime(data.synced_at)}`);

    toast(`Synced ${data.records} records for ${data.company_name}`, 'success', 3000);

    // Notify the current page to refresh its data
    window.dispatchEvent(new CustomEvent('sync:complete', { detail: data }));
  });

  _sse.addEventListener('sync_error', (e) => {
    const data = JSON.parse(e.data);
    setSyncStatus('error', 'Sync error');
    toast(`Sync failed: ${data.error}`, 'error', 5000);
    window.dispatchEvent(new CustomEvent('sync:error', { detail: data }));
  });

  _sse.addEventListener('heartbeat', () => {
    // silent keep-alive
  });

  _sse.onerror = () => {
    setSyncStatus('error', 'Disconnected');
    _sse.close();
    _sse = null;
    // Auto-reconnect
    _retryTimer = setTimeout(connectSSE, RETRY_DELAY_MS);
  };
}

// Reconnect when company changes
window.addEventListener('company:changed', () => {
  connectSSE();
});

// Start SSE on load
document.addEventListener('DOMContentLoaded', () => {
  connectSSE();
});
