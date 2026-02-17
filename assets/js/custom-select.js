/**
 * TallySync Manager — Custom Select
 * Wraps any <select> element with the same shadcn-style dropdown as the
 * company selector (cs-root / cs-trigger / cs-dropdown / cs-option).
 *
 * Usage:
 *   CustomSelect.init('my-select-id')
 *   CustomSelect.init('my-select-id', { minWidth: '14rem', placeholder: 'Pick one' })
 *   CustomSelect.refresh('my-select-id')   // call after changing <select> options dynamically
 */
const CustomSelect = (() => {
  const _instances = {};

  function init(selectId, opts) {
    const select = document.getElementById(selectId);
    if (!select || select._csInitialized) return;

    const options = opts || {};
    select.style.display = 'none';
    select._csInitialized = true;

    /* ── Build DOM ─────────────────────────────────────────────────────── */
    const root = document.createElement('div');
    root.className = 'cs-root';

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'cs-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    if (options.minWidth) trigger.style.minWidth = options.minWidth;

    const label = document.createElement('span');
    label.className = 'cs-label-text';

    const chevron = document.createElement('span');
    chevron.className = 'cs-chevron';
    chevron.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`;

    trigger.appendChild(label);
    trigger.appendChild(chevron);

    const dropdown = document.createElement('div');
    dropdown.className = 'cs-dropdown';
    dropdown.setAttribute('role', 'listbox');

    root.appendChild(trigger);
    root.appendChild(dropdown);
    select.insertAdjacentElement('afterend', root);

    /* ── State ─────────────────────────────────────────────────────────── */
    let _open = false;

    function _getLabel() {
      const opt = select.options[select.selectedIndex];
      return opt ? opt.text : (options.placeholder || 'Select…');
    }

    function _renderOptions() {
      const currentVal = select.value;
      dropdown.innerHTML = '';
      Array.from(select.options).forEach(opt => {
        const item = document.createElement('div');
        item.className = 'cs-option' + (opt.value === currentVal ? ' cs-selected' : '');
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', opt.value === currentVal);
        item.setAttribute('tabindex', '0');
        item.dataset.value = opt.value;
        item.innerHTML = `<svg class="cs-check" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>${esc(opt.text)}`;

        item.addEventListener('click', () => {
          _selectValue(opt.value);
          _close();
        });
        item.addEventListener('keydown', e => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); item.click(); }
          if (e.key === 'Escape') { _close(); trigger.focus(); }
          if (e.key === 'ArrowDown') { e.preventDefault(); (item.nextElementSibling || item).focus(); }
          if (e.key === 'ArrowUp')   { e.preventDefault(); (item.previousElementSibling || item).focus(); }
        });
        dropdown.appendChild(item);
      });
      label.textContent = _getLabel();
    }

    function _selectValue(value) {
      select.value = value;
      label.textContent = _getLabel();
      dropdown.querySelectorAll('.cs-option').forEach(o => {
        const sel = o.dataset.value === value;
        o.classList.toggle('cs-selected', sel);
        o.setAttribute('aria-selected', sel);
      });
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function _openDropdown() {
      if (_open) return;
      _open = true;
      trigger.setAttribute('aria-expanded', 'true');
      _renderOptions();
      dropdown.classList.add('cs-open');
      const rect = trigger.getBoundingClientRect();
      if (rect.bottom + 260 > window.innerHeight) {
        dropdown.style.top    = 'auto';
        dropdown.style.bottom = '100%';
        dropdown.style.marginTop    = '0';
        dropdown.style.marginBottom = '0.25rem';
      } else {
        dropdown.style.bottom = 'auto';
        dropdown.style.top    = '100%';
        dropdown.style.marginBottom = '0';
        dropdown.style.marginTop    = '0.25rem';
      }
      dropdown.querySelector('.cs-selected')?.focus();
    }

    function _close() {
      if (!_open) return;
      _open = false;
      trigger.setAttribute('aria-expanded', 'false');
      dropdown.classList.remove('cs-open');
    }

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      _open ? _close() : _openDropdown();
    });
    trigger.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault(); _openDropdown();
      }
      if (e.key === 'Escape') _close();
    });
    document.addEventListener('click', e => {
      if (_open && !root.contains(e.target)) _close();
    });

    _renderOptions();
    _instances[selectId] = { root, trigger, dropdown, select, label, _renderOptions };
  }

  /** Re-read native select options after dynamic update (e.g. API-loaded groups). */
  function refresh(selectId) {
    const inst = _instances[selectId];
    if (inst) inst._renderOptions();
  }

  return { init, refresh };
})();
