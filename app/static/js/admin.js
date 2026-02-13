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
        if (!(/[zZ]$/.test(s) || /[\+\-]\d{2}:?\d{2}$/.test(s))) {
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
                    // try a looser parse from displayed text (space-separated)
                    var alt = utc.replace(' ', 'T') + 'Z';
                    d = parseUtcStringToDate(alt);
                }
                if (!d) return;
                el.textContent = d.toLocaleString();
            } catch (e) {
                console.warn('Failed to parse last-synced time', e, utc);
            }
        });
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
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        initFileInputLabels();
        formatLastSyncedTimes();
    });

    // Also run after HTMX swaps
    document.body.addEventListener('htmx:afterSwap', onHtmxAfterSwap);

})();
