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
        var dayPayload = { alarms: [], events: [] };
        var dayPayloadTimerId = null;
        var nextAlarmTimerId = null;
        var DAY_FETCH_BASE_MS = 2 * 60 * 60 * 1000;
        var DAY_FETCH_JITTER_MS = 15 * 60 * 1000;

        function getBrowserTzOffset() {
            return (new Date()).getTimezoneOffset();
        }

        function buildAlarmRefreshPath(tzOffset) {
            if (tzOffset === undefined || tzOffset === null || tzOffset === '') {
                return '/components/alarm';
            }
            return '/components/alarm?tz_offset=' + encodeURIComponent(String(tzOffset));
        }

        function refreshAlarmPoller(tzOffset) {
            lastAlarmContent = '';
            var target = '#alarm-poller';
            var path = buildAlarmRefreshPath(tzOffset);
            if (window.htmx && typeof window.htmx.ajax === 'function') {
                window.htmx.ajax('GET', path, target);
                return;
            }
            fetch(path)
                .then(function (response) { return response.text(); })
                .then(function (html) {
                    var container = document.getElementById('alarm-poller');
                    if (container) {
                        container.innerHTML = html;
                    }
                })
                .catch(function () {
                    // Non-fatal refresh failure.
                });
        }

        function renderTodayEvents(events) {
            var wrapper = document.getElementById('today-events-wrapper');
            var list = document.getElementById('today-events-list');
            var count = document.getElementById('today-events-count');
            if (!wrapper || !list || !count) return;

            var safeEvents = Array.isArray(events) ? events : [];
            count.innerText = String(safeEvents.length);
            if (safeEvents.length === 0) {
                wrapper.classList.add('d-none');
                list.innerHTML = '<li class="today-events-empty">No events today.</li>';
                return;
            }

            wrapper.classList.remove('d-none');
            list.innerHTML = safeEvents.map(function (event) {
                var title = event && event.name ? String(event.name) : (event && event.fallback_text ? String(event.fallback_text) : 'No time available');
                return '<li class="today-event-item">'
                    + '<span class="today-event-title">' + title + '</span>'
                    + '</li>';
            }).join('');
        }

        function scheduleNextDayPayloadFetch() {
            if (dayPayloadTimerId) {
                clearTimeout(dayPayloadTimerId);
            }
            var jitter = Math.floor((Math.random() * (2 * DAY_FETCH_JITTER_MS + 1)) - DAY_FETCH_JITTER_MS);
            var delay = DAY_FETCH_BASE_MS + jitter;
            dayPayloadTimerId = setTimeout(function () {
                fetchDayPayload('scheduled');
            }, delay);
        }

        function scheduleNextAlarmCheck() {
            if (nextAlarmTimerId) {
                clearTimeout(nextAlarmTimerId);
            }

            var alarms = Array.isArray(dayPayload.alarms) ? dayPayload.alarms : [];
            var nowMs = Date.now();
            var hasDueAlarm = false;
            var nextTs = null;

            for (var i = 0; i < alarms.length; i++) {
                var alarm = alarms[i] || {};
                var triggerIso = alarm.trigger_iso || alarm.start_iso;
                if (!triggerIso) continue;
                var ts = Date.parse(triggerIso);
                if (isNaN(ts)) continue;
                if (ts <= nowMs) {
                    hasDueAlarm = true;
                    continue;
                }
                if (nextTs === null || ts < nextTs) {
                    nextTs = ts;
                }
            }

            if (hasDueAlarm) {
                refreshAlarmPoller(getBrowserTzOffset());
            }

            if (nextTs === null) {
                return;
            }

            var waitMs = Math.max(1000, nextTs - nowMs + 1000);
            nextAlarmTimerId = setTimeout(function () {
                refreshAlarmPoller(getBrowserTzOffset());
                fetchDayPayload('alarm-trigger');
            }, waitMs);
        }

        function fetchDayPayload(reason) {
            var tzOffset = getBrowserTzOffset();
            var url = '/api/v1/alarms/today?tz_offset=' + encodeURIComponent(String(tzOffset));
            fetch(url)
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Failed to fetch day payload');
                    }
                    return response.json();
                })
                .then(function (payload) {
                    dayPayload = payload || { alarms: [], events: [] };
                    renderTodayEvents(dayPayload.events || []);
                    if (reason === 'init' || reason === 'sync-event') {
                        refreshAlarmPoller(tzOffset);
                    }
                    scheduleNextAlarmCheck();
                    scheduleNextDayPayloadFetch();
                })
                .catch(function () {
                    scheduleNextDayPayloadFetch();
                });
        }

        function bindEventsPanelToggle() {
            var toggle = document.getElementById('today-events-toggle');
            var panel = document.getElementById('today-events-panel');
            if (!toggle || !panel) return;

            toggle.addEventListener('click', function () {
                var isHidden = panel.classList.contains('d-none');
                if (isHidden) {
                    panel.classList.remove('d-none');
                    toggle.setAttribute('aria-label', 'Hide Today\'s Events');
                } else {
                    panel.classList.add('d-none');
                    toggle.setAttribute('aria-label', 'Show Today\'s Events');
                }
            });
        }

        function bindCrossTabSyncRefresh() {
            window.addEventListener('storage', function (event) {
                if (event.key !== 'espaceImageCalendarSyncAt') {
                    return;
                }
                fetchDayPayload('sync-event');
            });
        }

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

        document.body.addEventListener('click', function (evt) {
            var button = evt.target.closest('[data-api-dismiss-alarm-id]');
            if (!button) return;

            evt.preventDefault();

            var alarmId = button.getAttribute('data-api-dismiss-alarm-id');
            var mock = button.getAttribute('data-api-dismiss-mock') === 'true';
            var tzOffset = button.getAttribute('data-api-dismiss-tz-offset');
            var query = mock ? '?mock=true' : '';

            fetch('/api/v1/alarms/' + encodeURIComponent(String(alarmId || '')) + '/dismiss' + query, {
                method: 'POST'
            }).then(function (response) {
                if (!response.ok) {
                    throw new Error('Failed to dismiss alarm');
                }
                return response.json();
            }).then(function () {
                refreshAlarmPoller(tzOffset);
            }).catch(function () {
                // Keep behavior unobtrusive in slideshow mode.
            });
        });

        // Start clock updates
        updateTime();
        setInterval(updateTime, 1000);
        bindEventsPanelToggle();
        bindCrossTabSyncRefresh();
        fetchDayPayload('init');
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
