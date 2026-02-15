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
                lastAlarmHtml = html.trim(); // Update tracker
                bindDismissButtons(); // Re-bind after update
                try { formatAlarmTimesLegacy(); } catch (e) { console.error(e); }
            }
        };
        xhr.send();
    }

    // --- Components ---

    var lastAlarmHtml = "";
    function bindDismissButtons() {
        var wrapper = document.getElementById('alarm-wrapper');
        if (!wrapper) return;

        var buttons = wrapper.querySelectorAll('.dismiss-btn-small');
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            var postUrl = btn.getAttribute('hx-post');
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
     * Format alarm datetimes inserted into legacy alarm wrapper
     */
    function formatAlarmTimesLegacy() {
        var wrapper = document.getElementById('alarm-wrapper');
        if (!wrapper) return;
        var els = wrapper.querySelectorAll('.alarm-time[data-start]');
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
        checkAlarm();

        setInterval(updateTime, 1000);
        setInterval(updateSlide, CONFIG.slideInterval);
        setInterval(updateWeather, CONFIG.weatherInterval);
        setInterval(checkAlarm, CONFIG.alarmInterval);
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
