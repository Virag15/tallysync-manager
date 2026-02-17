/**
 * TallySync Manager — Custom Date Picker
 * Replaces <input type="date"> with a calendar that includes year navigation.
 *
 * Usage:
 *   DatePicker.init('input-id')           // wraps an existing input
 *   DatePicker.init('input-id', {         // with options
 *     placeholder: 'From date',
 *   })
 *
 * The original <input type="date"> is hidden and kept in sync.
 * A native `change` event is dispatched on it so existing listeners work.
 */
const DatePicker = (() => {
  const MONTHS = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
  ];
  const DAYS_SHORT = ['Su','Mo','Tu','We','Th','Fr','Sa'];

  let _active = null; // currently open { panel, input, trigger }

  /* ── Helpers ────────────────────────────────────────────────────────── */

  function _pad(n) { return String(n).padStart(2, '0'); }

  function _iso(y, m1, d) {
    // m1 is 1-based month
    return `${y}-${_pad(m1)}-${_pad(d)}`;
  }

  function _parseIso(s) {
    if (!s) return null;
    const parts = s.split('-').map(Number);
    return { y: parts[0], m: parts[1] - 1, d: parts[2] }; // m is 0-based
  }

  function _todayIso() {
    const d = new Date();
    return _iso(d.getFullYear(), d.getMonth() + 1, d.getDate());
  }

  /* ── Close ──────────────────────────────────────────────────────────── */

  function _close() {
    if (_active) {
      _active.panel.remove();
      document.removeEventListener('keydown', _onKey);
      _active = null;
    }
  }

  function _onKey(e) {
    if (e.key === 'Escape') _close();
  }

  /* ── Update trigger label ────────────────────────────────────────────── */

  function _updateTrigger(input) {
    const trigger = input._dpTrigger;
    if (!trigger) return;
    const textEl = trigger.querySelector('.dp-trigger-text');
    const clearEl = trigger.querySelector('.dp-clear');
    if (input.value) {
      const p = _parseIso(input.value);
      textEl.textContent = `${_pad(p.d)} ${MONTHS[p.m].slice(0, 3)} ${p.y}`;
      trigger.classList.add('dp-has-value');
      if (clearEl) clearEl.style.display = '';
    } else {
      textEl.textContent = trigger._dpPlaceholder || 'Select date';
      trigger.classList.remove('dp-has-value');
      if (clearEl) clearEl.style.display = 'none';
    }
  }

  /* ── Render: day grid ────────────────────────────────────────────────── */

  function _renderDays(panel, input, state) {
    panel.innerHTML = '';
    panel.className = 'dp-panel';

    const selected = input.value;
    const todayStr = _todayIso();

    /* Header ── ‹ Month Year › */
    const hdr = document.createElement('div');
    hdr.className = 'dp-header';

    const btnPrevM = document.createElement('button');
    btnPrevM.type = 'button';
    btnPrevM.className = 'dp-nav dp-nav-sm';
    btnPrevM.title = 'Previous month';
    btnPrevM.innerHTML = '&#8249;';
    btnPrevM.addEventListener('click', () => {
      state.month--;
      if (state.month < 0) { state.month = 11; state.year--; }
      _renderDays(panel, input, state);
    });

    const btnNextM = document.createElement('button');
    btnNextM.type = 'button';
    btnNextM.className = 'dp-nav dp-nav-sm';
    btnNextM.title = 'Next month';
    btnNextM.innerHTML = '&#8250;';
    btnNextM.addEventListener('click', () => {
      state.month++;
      if (state.month > 11) { state.month = 0; state.year++; }
      _renderDays(panel, input, state);
    });

    const hdrCenter = document.createElement('div');
    hdrCenter.className = 'dp-header-center';

    const monthLabel = document.createElement('span');
    monthLabel.className = 'dp-month-label';
    monthLabel.textContent = MONTHS[state.month];

    const yearBtn = document.createElement('button');
    yearBtn.type = 'button';
    yearBtn.className = 'dp-year-chip';
    yearBtn.title = 'Pick a year';
    yearBtn.textContent = state.year;
    yearBtn.addEventListener('click', () => _renderYears(panel, input, state));

    hdrCenter.appendChild(monthLabel);
    hdrCenter.appendChild(yearBtn);
    hdr.appendChild(btnPrevM);
    hdr.appendChild(hdrCenter);
    hdr.appendChild(btnNextM);
    panel.appendChild(hdr);

    /* Year quick-nav row */
    const yRow = document.createElement('div');
    yRow.className = 'dp-year-row';

    const btnPrevY = document.createElement('button');
    btnPrevY.type = 'button';
    btnPrevY.className = 'dp-year-step';
    btnPrevY.title = 'Previous year';
    btnPrevY.innerHTML = '&#171; ' + (state.year - 1);
    btnPrevY.addEventListener('click', () => {
      state.year--;
      _renderDays(panel, input, state);
    });

    const btnNextY = document.createElement('button');
    btnNextY.type = 'button';
    btnNextY.className = 'dp-year-step';
    btnNextY.title = 'Next year';
    btnNextY.innerHTML = (state.year + 1) + ' &#187;';
    btnNextY.addEventListener('click', () => {
      state.year++;
      _renderDays(panel, input, state);
    });

    yRow.appendChild(btnPrevY);
    yRow.appendChild(btnNextY);
    panel.appendChild(yRow);

    /* Weekday headers */
    const wkRow = document.createElement('div');
    wkRow.className = 'dp-weekdays';
    DAYS_SHORT.forEach(d => {
      const s = document.createElement('span');
      s.textContent = d;
      wkRow.appendChild(s);
    });
    panel.appendChild(wkRow);

    /* Days */
    const grid = document.createElement('div');
    grid.className = 'dp-days';

    const firstDayOfWeek = new Date(state.year, state.month, 1).getDay();
    const daysInMonth    = new Date(state.year, state.month + 1, 0).getDate();
    const prevMonthDays  = new Date(state.year, state.month, 0).getDate();

    // Filler for days from previous month
    for (let i = 0; i < firstDayOfWeek; i++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'dp-day dp-other';
      btn.textContent = prevMonthDays - firstDayOfWeek + 1 + i;
      btn.disabled = true;
      grid.appendChild(btn);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const iso = _iso(state.year, state.month + 1, d);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'dp-day';
      if (iso === todayStr)  btn.classList.add('dp-today');
      if (iso === selected)  btn.classList.add('dp-selected');
      btn.textContent = d;
      btn.addEventListener('click', () => {
        input.value = iso;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        _updateTrigger(input);
        _close();
      });
      grid.appendChild(btn);
    }

    panel.appendChild(grid);

    /* Footer: Today / Clear */
    const footer = document.createElement('div');
    footer.className = 'dp-footer';

    const btnToday = document.createElement('button');
    btnToday.type = 'button';
    btnToday.className = 'dp-footer-btn';
    btnToday.textContent = 'Today';
    btnToday.addEventListener('click', () => {
      input.value = todayStr;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      _updateTrigger(input);
      _close();
    });

    const btnClear = document.createElement('button');
    btnClear.type = 'button';
    btnClear.className = 'dp-footer-btn dp-footer-clear';
    btnClear.textContent = 'Clear';
    btnClear.addEventListener('click', () => {
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
      _updateTrigger(input);
      _close();
    });

    footer.appendChild(btnToday);
    footer.appendChild(btnClear);
    panel.appendChild(footer);
  }

  /* ── Render: year picker ─────────────────────────────────────────────── */

  function _renderYears(panel, input, state) {
    panel.innerHTML = '';
    panel.className = 'dp-panel dp-panel-years';

    // Anchor to a decade-ish block of 12 years
    const startYear = Math.floor(state.year / 12) * 12;

    const hdr = document.createElement('div');
    hdr.className = 'dp-header';

    const btnPrev = document.createElement('button');
    btnPrev.type = 'button';
    btnPrev.className = 'dp-nav dp-nav-sm';
    btnPrev.innerHTML = '&#8249;';
    btnPrev.title = 'Previous 12 years';
    btnPrev.addEventListener('click', () => {
      state.year = startYear - 12 + 6; // centre of previous block
      _renderYears(panel, input, state);
    });

    const btnNext = document.createElement('button');
    btnNext.type = 'button';
    btnNext.className = 'dp-nav dp-nav-sm';
    btnNext.innerHTML = '&#8250;';
    btnNext.title = 'Next 12 years';
    btnNext.addEventListener('click', () => {
      state.year = startYear + 12 + 6;
      _renderYears(panel, input, state);
    });

    const title = document.createElement('span');
    title.className = 'dp-title';
    title.textContent = `${startYear} – ${startYear + 11}`;

    const backBtn = document.createElement('button');
    backBtn.type = 'button';
    backBtn.className = 'dp-back-link';
    backBtn.title = 'Back to calendar';
    backBtn.innerHTML = '&#8592; Back';
    backBtn.addEventListener('click', () => _renderDays(panel, input, state));

    hdr.appendChild(btnPrev);
    hdr.appendChild(title);
    hdr.appendChild(btnNext);
    panel.appendChild(hdr);
    panel.appendChild(backBtn);

    const grid = document.createElement('div');
    grid.className = 'dp-year-grid';

    for (let y = startYear; y < startYear + 12; y++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'dp-year-btn' + (y === state.year ? ' dp-selected' : '');
      btn.textContent = y;
      btn.addEventListener('click', () => {
        state.year = y;
        state.view = 'days';
        _renderDays(panel, input, state);
      });
      grid.appendChild(btn);
    }
    panel.appendChild(grid);
  }

  /* ── Open panel ─────────────────────────────────────────────────────── */

  function _open(input, trigger) {
    if (_active) _close();

    const parsed = _parseIso(input.value);
    const now    = new Date();
    const state  = {
      year:  parsed ? parsed.y : now.getFullYear(),
      month: parsed ? parsed.m : now.getMonth(),
    };

    const panel = document.createElement('div');
    panel.className = 'dp-panel';
    _renderDays(panel, input, state);

    // Position below trigger
    const rect = trigger.getBoundingClientRect();
    panel.style.position = 'fixed';
    panel.style.zIndex   = '9999';
    panel.style.top      = (rect.bottom + 6) + 'px';
    panel.style.left     = rect.left + 'px';

    document.body.appendChild(panel);

    // Adjust if off screen
    const pr = panel.getBoundingClientRect();
    if (pr.right > window.innerWidth - 8) {
      panel.style.left = Math.max(8, window.innerWidth - pr.width - 8) + 'px';
    }
    if (pr.bottom > window.innerHeight - 8) {
      panel.style.top = (rect.top - pr.height - 6) + 'px';
    }

    _active = { panel, input, trigger };
    document.addEventListener('keydown', _onKey);
  }

  /* ── Public: init ───────────────────────────────────────────────────── */

  function init(inputId, opts) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const options = opts || {};

    // Hide the native input but keep it in the DOM (value + events still work)
    input.style.display = 'none';

    // Build trigger button
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'dp-trigger form-control';
    trigger._dpPlaceholder = options.placeholder || 'Select date';

    trigger.innerHTML = `
      <svg class="dp-cal-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14"
           viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
        <line x1="16" x2="16" y1="2" y2="6"/>
        <line x1="8" x2="8" y1="2" y2="6"/>
        <line x1="3" x2="21" y1="10" y2="10"/>
      </svg>
      <span class="dp-trigger-text"></span>
      <span class="dp-clear" title="Clear date" style="display:none;">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
        </svg>
      </span>`;

    input._dpTrigger = trigger;
    _updateTrigger(input);

    // Clear button stops propagation so it doesn't open the picker
    trigger.querySelector('.dp-clear').addEventListener('click', e => {
      e.stopPropagation();
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
      _updateTrigger(input);
    });

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      if (_active && _active.input === input) {
        _close();
      } else {
        _open(input, trigger);
      }
    });

    // Insert immediately after the hidden input
    input.insertAdjacentElement('afterend', trigger);
  }

  /* ── Global close handlers ──────────────────────────────────────────── */

  document.addEventListener('click', e => {
    if (!_active) return;
    if (_active.panel.contains(e.target)) return;
    if (e.target === _active.trigger) return;
    _close();
  });

  window.addEventListener('scroll', _close, true);
  window.addEventListener('resize', _close);

  return { init };
})();
