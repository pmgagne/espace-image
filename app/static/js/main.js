// Main frontend scripts for slideshow, alarms, and time display.
/* eslint-disable no-console */

(function () {
    'use strict';

    // Service worker registration with error logging
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/static/sw.js').catch(function (e) {
                console.warn('Service worker registration failed:', e);
            });
        });
    }

    // Wait for DOM to be ready before adding htmx listeners
    document.addEventListener('DOMContentLoaded', function () {
        // Preload image before swapping for smooth fade-in
        document.body.addEventListener('htmx:beforeSwap', function (evt) {
            if (evt.detail.target.classList && evt.detail.target.classList.contains('slideshow-container')) {
                var newHtml = evt.detail.xhr.responseText || "";
                var tempDiv = document.createElement('div');
                tempDiv.innerHTML = newHtml;
                var imgElement = tempDiv.querySelector('img');
                var imgUrl = imgElement ? imgElement.src : null;

                if (imgUrl) {
                    var preloadImg = new Image();
                    preloadImg.src = imgUrl;
                }
            }
        });

        // Smart swap for alarms to prevent flickering on dismiss
        var lastAlarmContent = "";
        var hasAnimated = false;
        // Ensure dismiss POST always forces an update: clear the cached content
        document.body.addEventListener('htmx:beforeRequest', function (evt) {
            try {
                var verb = (evt.detail && evt.detail.verb) || '';
                var path = (evt.detail && evt.detail.path) || '';
                if (verb && verb.toUpperCase() === 'POST' && /\/api\/alarms\/.+\/dismiss/.test(path)) {
                    lastAlarmContent = '';
                }
            } catch (e) {
                // Non-fatal - don't block requests
            }
        });
        document.body.addEventListener('htmx:beforeSwap', function (evt) {
            if (evt.detail.target && evt.detail.target.id === 'alarm-poller') {
                var newHtml = evt.detail.xhr.responseText || "";
                var normalize = function (html) {
                    return html.replace(/\s/g, '').toLowerCase();
                };

                var normalizedNew = normalize(newHtml);
                if (normalizedNew === lastAlarmContent) {
                    evt.detail.shouldSwap = false;
                } else {
                    lastAlarmContent = normalizedNew;
                }
            }
        });

        // Animate alarm box only on first appearance and format times after swap
        document.body.addEventListener('htmx:afterSwap', function (evt) {
            if (evt.detail.target && evt.detail.target.id === 'alarm-poller') {
                var alarmBox = document.querySelector('.alarm-box-container');
                if (alarmBox && !hasAnimated) {
                    alarmBox.classList.add('animate-in');
                    hasAnimated = true;
                }
                try {
                    formatAlarmTimes();
                } catch (e) {
                    console.error('formatAlarmTimes error', e);
                }
            }
        });

        // Start clock updates
        updateTime();
        setInterval(updateTime, 1000);
        // initial formatting of any alarm times already present
        try { formatAlarmTimes(); } catch (e) { /* ignore */ }
        // Ensure a short client-side index-refresh to pick up new alarms
        // quickly (uses HTMX to request /components/index-refresh which
        // returns out-of-band fragments). This complements the server-side
        // configured interval and helps surface new alarms faster.
        (function () {
            var INDEX_AUTO_REFRESH_MS = 30 * 1000; // 30 seconds
            if (window.htmx && typeof window.setInterval === 'function') {
                try {
                    setInterval(function () {
                        try {
                            window.htmx.ajax('GET', '/components/index-refresh');
                        } catch (e) {
                            console.error('htmx ajax error', e);
                        }
                    }, INDEX_AUTO_REFRESH_MS);
                } catch (e) {
                    console.error('Failed to start index auto-refresh', e);
                }
            }
        })();
    });

    function updateTime() {
        const now = new Date();

        // Time: HH:MM with fallback for browser compatibility
        var timeStr;
        try {
            timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        } catch (e) {
            // Fallback for browsers that don't support the options
            var h = now.getHours();
            var m = now.getMinutes();
            timeStr = (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
        }

        var clockEl = document.getElementById('clock');
        if (clockEl) {
            clockEl.innerText = timeStr;
        }

        // Date: Month DD, YYYY
        var dateEl = document.getElementById('date-display');
        if (dateEl) {
            try {
                const options = { year: 'numeric', month: 'long', day: 'numeric' };
                dateEl.innerText = now.toLocaleDateString(undefined, options);
            } catch (e) {
                dateEl.innerText = now.toDateString();
            }
        }
    }

    // Format alarm datetimes inserted by /components/alarm
    function formatAlarmTimes() {
        var els = document.querySelectorAll('.alarm-time[data-start]');
        var now = new Date();
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            var startIso = el.getAttribute('data-start');
            var endIso = el.getAttribute('data-end');
            var allDay = el.getAttribute('data-allday') === 'true';
            if (!startIso) continue;
            try {
                var start = new Date(startIso);
                var end = endIso ? new Date(endIso) : null;
                var text = '';
                var dayText = '';
                var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                var startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate());
                var diffDays = Math.round((startDay - today) / 86400000);
                if (diffDays === 0) {
                    dayText = "Aujourd'hui";
                } else if (diffDays === 1) {
                    dayText = "Demain";
                } else {
                    var days = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
                    var months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
                    var month = months[start.getMonth()];
                    var dayNum = start.getDate();
                    var yearPart = start.getFullYear() === now.getFullYear() ? '' : ' ' + start.getFullYear();
                    dayText = days[start.getDay()] + ", " + dayNum + " " + month + yearPart;
                }

                if (allDay) {
                    text = dayText;
                } else {
                    var pad = function (n) { return n < 10 ? '0' + n : n; };
                    var t1 = pad(start.getHours()) + ':' + pad(start.getMinutes());
                    var t2 = end ? pad(end.getHours()) + ':' + pad(end.getMinutes()) : '';
                    var timeText = t1 + (t2 && t2 !== t1 ? '–' + t2 : '');
                    text = dayText + ' ' + timeText;
                }
                el.innerText = text;
            } catch (e) {
                el.innerText = startIso;
            }
        }
    }

})();
