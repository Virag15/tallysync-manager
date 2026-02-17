/**
 * TallySync Manager — Runtime Configuration
 *
 * Change TALLYSYNC_API to point to your backend server.
 * Default: http://localhost:8001 (same machine as Tally)
 *
 * LAN example: 'http://192.168.1.10:8001'
 */
window.TALLYSYNC_API = localStorage.getItem('tallysync_api') || window.TALLYSYNC_API || 'http://localhost:8001';

// Sync API key from server on every load.
// Handles: first run (no key), server reinstall (stale key), key rotation.
// /api/info is public so this works even with a wrong/missing key.
(async () => {
  try {
    const res = await fetch(window.TALLYSYNC_API + '/api/info', { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const info = await res.json();
      if (info.api_key && info.api_key !== localStorage.getItem('tallysync_api_key')) {
        localStorage.setItem('tallysync_api_key', info.api_key);
        location.reload();
      }
    }
  } catch (_) {}
})();
