// Admin page utilities: file input UI, timezone formatting for last-synced timestamps,
// and HTMX hooks. Loaded from /static/js/admin.js

(function () {
    'use strict';

    function parseUtcStringToDate(utc) {
        if (!utc) return null;
        var s = String(utc).trim();
        if (s.indexOf('T') === -1 && s.indexOf(' ') !== -1) {
            s = s.replace(' ', 'T');
        }
        if (!(/[zZ]$/.test(s) || /[+-]\d{2}:?\d{2}$/.test(s))) {
            s = s + 'Z';
        }
        var d = new Date(s);
        if (isNaN(d.getTime())) return null;
        return d;
    }

    function formatLastSyncedTimes() {
        var els = document.querySelectorAll('.last-synced');
        els.forEach(function (el) {
            var utc = el.getAttribute('data-utc') || el.textContent || '';
            utc = (typeof utc === 'string') ? utc.trim() : '';
            if (!utc) return;
            try {
                var d = parseUtcStringToDate(utc);
                if (!d) {
                    var alt = utc.replace(' ', 'T') + 'Z';
                    d = parseUtcStringToDate(alt);
                }
                if (!d) return;
                el.textContent = d.toLocaleString();
            } catch (e) {
                // Silently ignore parse errors
            }
        });
        // Also format next-sync times
        var nextEls = document.querySelectorAll('.next-sync');
        nextEls.forEach(function (el) {
            var utc = el.getAttribute('data-utc') || el.textContent || '';
            utc = (typeof utc === 'string') ? utc.trim() : '';
            if (!utc || utc === '—') return;
            try {
                var d = parseUtcStringToDate(utc);
                if (!d) {
                    var alt = utc.replace(' ', 'T') + 'Z';
                    d = parseUtcStringToDate(alt);
                }
                if (!d) return;
                el.textContent = d.toLocaleString();
            } catch (e) {
                // Failed to parse timestamp (silently ignore)
            }
        });
    }

    function setBrowserTimezone() {
        try {
            var el = document.getElementById('browser-tz');
            if (!el) return;
            // Check if Intl is available (not in iOS 9.3)
            /* eslint-disable-next-line compat/compat */
            var tz = (typeof Intl !== 'undefined' && Intl.DateTimeFormat) ? Intl.DateTimeFormat().resolvedOptions().timeZone : null;
            if (tz) {
                el.textContent = tz;
            } else {
                var m = (new Date()).toString().match(/\(([^)]+)\)$/);
                el.textContent = m ? m[1] : (new Date()).toLocaleString();
            }
        } catch (e) {
            // Ignore timezone detection errors
        }
    }

    function initFileInputLabels() {
        document.body.addEventListener('change', function (e) {
            if (e.target && e.target.type === 'file') {
                var wrapper = e.target.parentNode;
                if (wrapper && wrapper.classList && wrapper.classList.contains('file-input-wrapper')) {
                    var labelSpan = wrapper.querySelector('.btn-text');
                    if (labelSpan) {
                        var count = e.target.files ? e.target.files.length : 1;
                        if (count > 0) {
                            labelSpan.innerText = count + (count === 1 ? " File Selected" : " Files Selected");
                        } else {
                            labelSpan.innerText = wrapper.getAttribute('data-placeholder') || "Choose Files";
                        }
                    }
                }
            }
        });
    }

    function onHtmxAfterSwap() {
        try { formatLastSyncedTimes(); } catch (e) { /* ignore */ }
        try { setBrowserTimezone(); } catch (e) { /* ignore */ }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        initFileInputLabels();
        formatLastSyncedTimes();
        try { setBrowserTimezone(); } catch (e) { /* ignore */ }
    });

    // Also run after HTMX swaps
    document.body.addEventListener('htmx:afterSwap', onHtmxAfterSwap);

    // HTMX-driven calendar sync feedback
    function isCalendarSyncElement(elt) {
        if (!elt || !elt.getAttribute) return false;
        var url = elt.getAttribute('hx-post') || elt.getAttribute('hx-get') || elt.getAttribute('hx-delete');
        return url === '/admin/calendars/sync-now';
    }

    document.body.addEventListener('htmx:beforeRequest', function (evt) {
        try {
            var elt = evt.detail && evt.detail.elt;
            if (!isCalendarSyncElement(elt)) return;
            // show inline syncing message and disable button
            var btn = elt;
            btn.setAttribute('disabled', 'disabled');
            btn.classList.add('loading');
            var spinner = document.createElement('span');
            spinner.className = 'sync-spinner';
            spinner.style.marginLeft = '8px';
            spinner.textContent = '⏳';
            btn.appendChild(spinner);
            var msg = document.getElementById('cal-sync-msg');
            if (msg) { msg.style.display = 'inline-block'; msg.style.color = '#9ae6b4'; msg.textContent = 'Syncing…'; }
        } catch (e) { /* ignore */ }
    });

    document.body.addEventListener('htmx:afterSwap', function (evt) {
        try {
            var elt = evt.detail && evt.detail.elt;
            if (!isCalendarSyncElement(elt)) return;
            // After successful swap the partial is refreshed; but ensure message shown briefly
            var msg = document.getElementById('cal-sync-msg');
            if (msg) { msg.style.display = 'inline-block'; msg.style.color = '#9ae6b4'; msg.textContent = 'Sync complete'; }
            // cleanup button (if still present in DOM)
            var btn = document.getElementById('btn-sync-calendars');
            if (btn) {
                btn.removeAttribute('disabled');
                var spinner = btn.querySelector('.sync-spinner');
                if (spinner) spinner.remove();
            }
            // hide message after a short delay
            setTimeout(function () { if (msg) msg.style.display = 'none'; }, 2500);
        } catch (e) {
            // Ignore sync errors
        }
    });

    document.body.addEventListener('htmx:responseError', function (evt) {
        try {
            var elt = evt.detail && evt.detail.elt;
            if (!isCalendarSyncElement(elt)) return;
            var msg = document.getElementById('cal-sync-msg');
            if (msg) { msg.style.display = 'inline-block'; msg.style.color = '#f87171'; msg.textContent = 'Sync failed'; }
            var btn = document.getElementById('btn-sync-calendars');
            if (btn) { btn.removeAttribute('disabled'); var spinner = btn.querySelector('.sync-spinner'); if (spinner) spinner.remove(); }
            setTimeout(function () { if (msg) msg.style.display = 'none'; }, 4000);
        } catch (e) {
            // Ignore error handling
        }
    });

    // === Settings Page Event Handlers ===

    // Location search - Enter key triggers search button
    document.body.addEventListener('htmx:afterSwap', function () {
        var locationInput = document.getElementById('location_query');
        var searchBtn = document.getElementById('btn-search');

        if (locationInput && searchBtn) {
            locationInput.addEventListener('keydown', function (event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    searchBtn.click();
                }
            });
        }
    });

    // GPS geolocation button
    document.body.addEventListener('click', function (event) {
        if (event.target.id === 'btn-gps' || event.target.closest('#btn-gps')) {
            event.preventDefault();

            if (!navigator.geolocation) {
                alert('Geolocation is not supported by your browser');
                return;
            }

            var btn = document.getElementById('btn-gps');
            var originalText = btn.innerText;
            btn.innerText = 'Locating...';

            navigator.geolocation.getCurrentPosition(function (position) {
                document.getElementById('lat').value = position.coords.latitude.toFixed(4);
                document.getElementById('lon').value = position.coords.longitude.toFixed(4);
                btn.innerText = originalText;
            }, function (error) {
                alert('Unable to retrieve your location: ' + error.message);
                btn.innerText = originalText;
            });
        }
    });

})();
