/**
 * Legacy Slideshow Engine (ES5 for iOS 9.3)
 *
 * Extracted from legacy/index.html to improve maintainability.
 * All code is ES5-compatible for iPad 2 (iOS 9.3.5).
 *
 * Dependencies:
 * - CONFIG object (defined inline in HTML due to Jinja2 template variables)
 * - DOM elements: slide-wrapper, weather-wrapper, alarm-wrapper, clock, date-display
 */

/* global CONFIG */

/* eslint-disable no-console */

(function () {
    'use strict';

    /**
     * Helper: XHR Request
     */
    function fetchHTML(url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    callback(xhr.responseText);
                } else {
                    console.error("Error fetching " + url);
                }
            }
        };
        xhr.send();
    }

    /**
     * Helper: XHR JSON Request
     */
    function fetchJSON(url, onSuccess, onError) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) return;
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    onSuccess(JSON.parse(xhr.responseText || '{}'));
                } catch (e) {
                    if (onError) onError(e);
                }
                return;
            }
            if (onError) onError(new Error('JSON request failed: ' + xhr.status));
        };
        xhr.send();
    }

    /**
     * Helper: POST Request (for Dismiss)
     */
    function postAction(url, targetId) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                // Returns updated content
                var html = xhr.responseText;
                document.getElementById(targetId).innerHTML = html;
                // Normalize tracker the same way `checkAlarm` compares updates
                try {
                    lastAlarmHtml = html.replace(/\s/g, '').toLowerCase();
                } catch (e) {
                    lastAlarmHtml = html.trim();
                }
                bindDismissButtons(); // Re-bind after update
                try { formatAlarmTimesLegacy(); } catch (e) { console.error(e); }
                try { fetchTodayPayloadLegacy('dismiss'); } catch (e) { console.error(e); }
            }
        };
        xhr.send();
    }

    // --- Components ---

    var lastAlarmHtml = "";
    var dayPayload = { alarms: [], events: [] };
    var dayPayloadTimerId = null;
    var nextAlarmTimerId = null;
    var DAY_FETCH_BASE_MS = (typeof CONFIG !== 'undefined' && CONFIG.dayFetchIntervalMs > 0)
        ? CONFIG.dayFetchIntervalMs
        : 60 * 60 * 1000;
    var WEATHER_REFRESH_MS = (typeof CONFIG !== 'undefined' && CONFIG.weatherInterval > 0)
        ? CONFIG.weatherInterval
        : 15 * 60 * 1000;

    function getBrowserTzOffset() {
        return (new Date()).getTimezoneOffset();
    }
    function bindDismissButtons() {
        var wrapper = document.getElementById('alarm-wrapper');
        if (!wrapper) return;

        var buttons = wrapper.querySelectorAll('.dismiss-btn-small');
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            var alarmId = btn.getAttribute('data-api-dismiss-alarm-id');
            var mock = btn.getAttribute('data-api-dismiss-mock');
            var postUrl = null;
            if (alarmId) {
                postUrl = '/api/v1/alarms/' + encodeURIComponent(alarmId) + '/dismiss';
                if (mock === 'true') {
                    postUrl += '?mock=true';
                }
            } else {
                postUrl = btn.getAttribute('hx-post');
            }
            if (postUrl) {
                btn.removeAttribute('hx-post'); // Prevent confusion
                // Create a closure for the URL
                (function (url) {
                    btn.onclick = function () {
                        postAction(url, 'alarm-wrapper');
                    };
                })(postUrl);
            }
        }
    }

    /**
     * Format alarm datetimes inserted into legacy alarm wrapper and today's event times
     */
    function formatAlarmTimesLegacy() {
        var els = document.querySelectorAll('.alarm-time[data-start], .today-event-time[data-start]');
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
                // Always show day information (Aujourd'hui/Demain or Weekday, D Month YYYY)
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

    function updateWeather() {
        fetchHTML('/components/weather', function (html) {
            document.getElementById('weather-wrapper').innerHTML = html;
        });
    }

    function updateSlide() {
        fetchHTML('/components/slide?mode=legacy', function (html) {
            var wrapper = document.getElementById('slide-wrapper');
            var slideContainer = wrapper.querySelector('.slide-container');

            // Extract image URL from HTML to preload
            var tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            var imgElement = tempDiv.querySelector('img');
            var imgUrl = imgElement ? imgElement.src : null;

            // Preload the image before transition
            if (imgUrl) {
                var preloadImg = new Image();
                preloadImg.onload = function () {
                    // Image is loaded, now do the transition
                    if (slideContainer) {
                        slideContainer.classList.add('fade-out');
                        setTimeout(function () {
                            wrapper.innerHTML = html;
                            var newSlide = wrapper.querySelector('.slide-container');
                            if (newSlide) {
                                // Add fade-out class first (opacity: 0)
                                newSlide.classList.add('fade-out');
                                // Trigger reflow to ensure transition applies
                                void newSlide.offsetHeight;
                                // Remove fade-out class to trigger fade-in (opacity: 1)
                                newSlide.classList.remove('fade-out');
                            }
                        }, 500);
                    } else {
                        wrapper.innerHTML = html;
                    }
                };
                preloadImg.src = imgUrl;
            } else {
                // No image found, just swap
                if (slideContainer) {
                    slideContainer.classList.add('fade-out');
                    setTimeout(function () {
                        wrapper.innerHTML = html;
                    }, 500);
                } else {
                    wrapper.innerHTML = html;
                }
            }
        });
    }

    function checkAlarm() {
        var tzOffset = (new Date()).getTimezoneOffset();
        fetchHTML('/components/alarm?tz_offset=' + tzOffset, function (html) {
            var wrapper = document.getElementById('alarm-wrapper');
            // Strip all whitespace and newlines for a robust comparison
            var normalize = function (s) {
                return s.replace(/\s/g, '').toLowerCase();
            };
            var normalizedHtml = normalize(html);
            // Only update if content changed significantly
            if (normalizedHtml !== lastAlarmHtml) {
                lastAlarmHtml = normalizedHtml;
                wrapper.innerHTML = html;
                bindDismissButtons(); // Bind listeners to new buttons
                try { formatAlarmTimesLegacy(); } catch (e) { console.error(e); }
            }
        });
    }

    function renderTodayEventsLegacy(events) {
        var wrapper = document.getElementById('today-events-wrapper');
        var list = document.getElementById('today-events-list');
        var count = document.getElementById('today-events-count');
        if (!wrapper || !list) return;

        var safeEvents = events && events.length ? events : [];
        safeEvents.sort(function (a, b) {
            var aStart = a && a.start_iso ? Date.parse(a.start_iso) : Infinity;
            var bStart = b && b.start_iso ? Date.parse(b.start_iso) : Infinity;
            return aStart - bStart;
        });
        if (count) {
            count.innerText = String(safeEvents.length);
        }
        if (!safeEvents.length) {
            wrapper.className = 'today-events-wrapper d-none';
            list.innerHTML = '<li class="today-events-empty">No items.</li>';
            return;
        }

        wrapper.className = 'today-events-wrapper';
        var html = '';
        for (var i = 0; i < safeEvents.length; i++) {
            var event = safeEvents[i] || {};
            var title = event.name ? String(event.name) : (event.fallback_text ? String(event.fallback_text) : 'No time available');
            var timeText = event.fallback_text ? String(event.fallback_text) : '';
            var startAttr = event.start_iso ? ' data-start="' + String(event.start_iso) + '"' : '';
            var endAttr = event.end_iso ? ' data-end="' + String(event.end_iso) + '"' : '';
            var alldayAttr = (event.all_day === true || event.all_day === 'true') ? ' data-allday="true"' : ' data-allday="false"';
            var timeSpan = '<span class="today-event-time"' + startAttr + endAttr + alldayAttr + '>' + (timeText || '') + '</span>';
            html += '<li class="today-event-item">'
                + '<span class="today-event-title">' + title + '</span>'
                + timeSpan
                + '</li>';
        }
        list.innerHTML = html;
    }

    function scheduleNextDayPayloadFetchLegacy() {
        if (dayPayloadTimerId) clearTimeout(dayPayloadTimerId);
        dayPayloadTimerId = setTimeout(function () {
            console.log('[espace-image] Auto-refresh: fetching events & alarms (interval ' + (DAY_FETCH_BASE_MS / 1000) + 's)');
            fetchTodayPayloadLegacy('scheduled');
        }, DAY_FETCH_BASE_MS);
    }

    function applyRefreshHintsLegacy(hints) {
        if (hints && hints.events_refresh_ms > 0) {
            DAY_FETCH_BASE_MS = hints.events_refresh_ms;
        }
        if (hints && hints.weather_refresh_ms > 0) {
            WEATHER_REFRESH_MS = hints.weather_refresh_ms;
        }
        console.log('[espace-image] Refresh hints applied: events=' + (DAY_FETCH_BASE_MS / 1000) + 's, weather=' + (WEATHER_REFRESH_MS / 1000) + 's');
    }

    function scheduleNextAlarmCheckLegacy() {
        if (nextAlarmTimerId) clearTimeout(nextAlarmTimerId);

        var alarms = dayPayload && dayPayload.alarms ? dayPayload.alarms : [];
        var nowMs = Date.now();
        var hasDue = false;
        var nextTs = null;

        for (var i = 0; i < alarms.length; i++) {
            var alarm = alarms[i] || {};
            var triggerIso = alarm.trigger_iso || alarm.start_iso;
            if (!triggerIso) continue;
            var ts = Date.parse(triggerIso);
            if (isNaN(ts)) continue;
            if (ts <= nowMs) {
                hasDue = true;
                continue;
            }
            if (nextTs === null || ts < nextTs) {
                nextTs = ts;
            }
        }

        if (hasDue) {
            checkAlarm();
        }

        if (nextTs === null) return;
        var waitMs = Math.max(1000, nextTs - nowMs + 1000);
        nextAlarmTimerId = setTimeout(function () {
            checkAlarm();
            fetchTodayPayloadLegacy('alarm-trigger');
        }, waitMs);
    }

    function fetchTodayPayloadLegacy(reason) {
        var tzOffset = getBrowserTzOffset();
        fetchJSON(
            '/api/v1/alarms/today?tz_offset=' + encodeURIComponent(String(tzOffset)),
            function (payload) {
                dayPayload = payload || { alarms: [], events: [] };
                renderTodayEventsLegacy(dayPayload.events || []);
                try {
                    formatAlarmTimesLegacy();
                } catch (e) {
                    console.error('formatAlarmTimesLegacy error', e);
                }
                if (reason === 'init' || reason === 'sync-event') {
                    checkAlarm();
                }
                scheduleNextAlarmCheckLegacy();
                scheduleNextDayPayloadFetchLegacy();
            },
            function () {
                scheduleNextDayPayloadFetchLegacy();
            }
        );
    }

    function bindEventsPanelToggleLegacy() {
        var toggle = document.getElementById('today-events-toggle');
        var panel = document.getElementById('today-events-panel');
        if (!toggle || !panel) return;

        toggle.onclick = function () {
            var isHidden = panel.className.indexOf('d-none') !== -1;
            if (isHidden) {
                panel.className = 'today-events-panel';
                toggle.setAttribute('aria-label', 'Hide Events');
            } else {
                panel.className = 'today-events-panel d-none';
                toggle.setAttribute('aria-label', 'Show Events');
            }
        };
    }

    function bindCrossTabSyncRefreshLegacy() {
        window.addEventListener('storage', function (event) {
            if (event.key !== 'espaceImageCalendarSyncAt') return;
            fetchTodayPayloadLegacy('sync-event');
        });
    }

    /**
     * Update clock
     */
    function updateTime() {
        var now = new Date();
        var hours = now.getHours();
        var minutes = now.getMinutes();
        if (minutes < 10) minutes = '0' + minutes;
        var timeStr = hours + ':' + minutes;

        var clockEl = document.getElementById('clock');
        if (clockEl) clockEl.innerText = timeStr;

        var months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
        var days = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
        var dateStr = days[now.getDay()] + " " + now.getDate() + " " + months[now.getMonth()];

        var dateEl = document.getElementById('date-display');
        if (dateEl) dateEl.innerText = dateStr;
    }

    /**
     * Initialization
     */
    function init() {
        updateTime();
        updateWeather();
        updateSlide(); // Immediate load
        // Suppress noisy HTMX out-of-band target errors when fragments
        // reference elements not present on the current page (legacy clients).
        if (window && window.addEventListener) {
            document.body.addEventListener('htmx:oobErrorNoTarget', function (evt) {
                if (evt && evt.preventDefault) evt.preventDefault();
                return false;
            });
        }
        checkAlarm();
        bindEventsPanelToggleLegacy();
        bindCrossTabSyncRefreshLegacy();
        fetchTodayPayloadLegacy('init');

        setInterval(updateTime, 1000);
        setInterval(updateSlide, CONFIG.slideInterval);
        // Weather refresh rate is driven by /api/v1/config/refresh-hints after init.
        fetchJSON('/api/v1/config/refresh-hints',
            function (hints) {
                applyRefreshHintsLegacy(hints);
                setInterval(function () {
                    console.log('[espace-image] Auto-refresh: refreshing weather (interval ' + (WEATHER_REFRESH_MS / 1000) + 's)');
                    updateWeather();
                }, WEATHER_REFRESH_MS);
            },
            function () {
                console.warn('[espace-image] Could not load refresh hints; using default weather interval');
                setInterval(updateWeather, WEATHER_REFRESH_MS);
            }
        );
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
