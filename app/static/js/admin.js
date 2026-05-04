// Global stubs to avoid "refreshAdminContent is not defined" when handlers
// or inline attributes invoke the functions before the full script initializes.
if (typeof window !== 'undefined') {
    window.__eai_admin_queue = window.__eai_admin_queue || [];
    if (typeof window.refreshAdminContent !== 'function') {
        window.refreshAdminContent = function (path) {
            window.__eai_admin_queue.push({ fn: 'refreshAdminContent', args: [path] });
        };
    }
    if (typeof window.parseJsonDetail !== 'function') {
        window.parseJsonDetail = function () {
            // placeholder: return a rejected Promise so callers hit error path
            return Promise.reject(new Error('admin.js not initialized'));
        };
    }
    if (typeof window.putJson !== 'function') {
        window.putJson = function () {
            return Promise.reject(new Error('admin.js not initialized'));
        };
    }
    if (typeof window.postJson !== 'function') {
        window.postJson = function () {
            return Promise.reject(new Error('admin.js not initialized'));
        };
    }
}

    // === Preset Combo-Box Add/Delete Handlers ===
    document.body.addEventListener('click', function (event) {
        // Add new preset (use closest to handle clicks on inner elements)
        var addBtn = event.target && event.target.closest ? event.target.closest('#add-preset-btn') : null;
        if (addBtn) {
            var nameInput = document.getElementById('add-preset-name');
            var name = nameInput ? String(nameInput.value || '').trim() : '';
            console.log('[admin] add-preset-btn clicked, name=', name);
            if (!name) {
                alert('Preset name required');
                return;
            }
            fetch('/api/v1/presets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            }).then(function (response) {
                if (!response.ok) {
                    return parseJsonDetail(response).then(function (detail) {
                        throw new Error(detail);
                    });
                }
                return response.json();
            }).then(function () {
                nameInput.value = '';
                refreshAdminContent('/admin/partials/gallery');
            }).catch(function (error) {
                alert(error.message || 'Failed to create preset');
            });
            return;
        }

        // Delete selected preset
        var delBtn = event.target && event.target.closest ? event.target.closest('#delete-preset-btn') : null;
        if (delBtn) {
            var select = document.getElementById('preset-combo-box');
            var presetId = select ? parseInt(select.value, 10) : null;
            console.log('[admin] delete-preset-btn clicked, presetId=', presetId);
            if (!presetId) {
                alert('Select a preset to delete');
                return;
            }
            if (!window.confirm('Delete this preset and all its photos?')) return;
            fetch('/api/v1/presets/' + presetId, {
                method: 'DELETE'
            }).then(function (response) {
                if (!response.ok) {
                    return parseJsonDetail(response).then(function (detail) {
                        throw new Error(detail);
                    });
                }
                refreshAdminContent('/admin/partials/gallery');
            }).catch(function (error) {
                alert(error.message || 'Failed to delete preset');
            });
            return;
        }
    });

    // Refresh gallery when preset selection changes and enable/disable delete button
    document.body.addEventListener('change', function (event) {
        if (event.target && event.target.id === 'preset-combo-box') {
            var select = event.target;
            var presetId = select.value;
            var path = '/admin/partials/gallery';
            if (presetId) path += '?preset_id=' + encodeURIComponent(presetId);
            refreshAdminContent(path);

            var deleteBtn = document.getElementById('delete-preset-btn');
            if (deleteBtn) {
                if (presetId) deleteBtn.removeAttribute('disabled'); else deleteBtn.setAttribute('disabled', 'disabled');
            }
        }
    });
// Admin page utilities: file input UI, timezone formatting for last-synced timestamps,
// and HTMX hooks. Loaded from /static/js/admin.js

(function () {
    'use strict';

    function refreshAdminContent(path) {
        // Prefer HTMX so existing active-link and afterSwap hooks keep working.
        if (window.htmx && typeof window.htmx.ajax === 'function') {
            try {
                // Use options object for target to be compatible with htmx API variations
                window.htmx.ajax('GET', path, { target: '#admin-content' });
                return;
            } catch (e) {
                // Fall back to fetch if htmx.ajax signature differs
            }
        }

        fetch(path)
            .then(function (response) { return response.text(); })
            .then(function (html) {
                var target = document.getElementById('admin-content');
                if (target) {
                    target.innerHTML = html;
                }
            })
            .catch(function () {
                // Ignore refresh errors; existing content remains visible.
            });
    }

    function parseJsonDetail(response) {
        return response.json().then(function (payload) {
            if (payload && payload.detail) {
                return String(payload.detail);
            }
            return 'Request failed';
        });
    }

    function toNullableInt(value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        var parsed = parseInt(value, 10);
        return isNaN(parsed) ? null : parsed;
    }

    function toNullableFloat(value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        var parsed = parseFloat(value);
        return isNaN(parsed) ? null : parsed;
    }

    function putJson(url, payload) {
        return fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) {
                return parseJsonDetail(response).then(function (detail) {
                    throw new Error(detail);
                });
            }
            return response.json();
        });
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) {
                return parseJsonDetail(response).then(function (detail) {
                    throw new Error(detail);
                });
            }
            return response.json();
        });
    }

    // Expose utilities for inline/top-level handlers
    try {
        window.refreshAdminContent = refreshAdminContent;
        window.parseJsonDetail = parseJsonDetail;
        window.putJson = putJson;
        window.postJson = postJson;
    } catch (e) {
        // Ignore if window is not available (e.g., unit test environment)
    }

    // Flush any queued early calls that happened before the script initialized
    try {
        var q = (window.__eai_admin_queue && window.__eai_admin_queue.splice(0)) || [];
        q.forEach(function (entry) {
            try {
                if (entry.fn === 'refreshAdminContent') {
                    refreshAdminContent.apply(null, entry.args || []);
                }
                // other queued fn types can be added here if needed
            } catch (e) {
                // ignore flush errors
            }
        });
    } catch (e) {
        // ignore
    }

    function refreshCalendarsPartial() {
        refreshAdminContent('/admin/partials/calendars');
    }

    function refreshDebugPartial() {
        refreshAdminContent('/admin/partials/debug');
    }

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

    // === Admin write actions through JSON APIs ===
    document.body.addEventListener('submit', function (event) {
        var form = event.target;
        if (!form || !form.id) return;

        if (form.id === 'admin-preset-create-form') {
            event.preventDefault();

            var nameInput = form.querySelector('input[name="name"]');
            var name = nameInput ? String(nameInput.value || '').trim() : '';
            if (!name) return;

            fetch('/api/v1/presets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            }).then(function (response) {
                if (!response.ok) {
                    return parseJsonDetail(response).then(function (detail) {
                        throw new Error(detail);
                    });
                }
                return response.json();
            }).then(function () {
                refreshAdminContent('/admin/partials/gallery');
            }).catch(function (error) {
                alert(error.message || 'Failed to create preset');
            });
            return;
        }

        if (form.id === 'admin-upload-form') {
            event.preventDefault();

            var presetInput = form.querySelector('input[name="preset_id"]');
            var presetId = presetInput ? parseInt(presetInput.value, 10) : null;
            if (!presetId) {
                alert('Preset is required for upload');
                return;
            }

            var formData = new FormData(form);
            fetch('/api/v1/presets/' + presetId + '/images', {
                method: 'POST',
                body: formData
            }).then(function (response) {
                if (!response.ok) {
                    return parseJsonDetail(response).then(function (detail) {
                        throw new Error(detail);
                    });
                }
                return response.json();
            }).then(function () {
                refreshAdminContent('/admin/partials/gallery?preset_id=' + presetId);
            }).catch(function (error) {
                alert(error.message || 'Failed to upload image(s)');
            });
            return;
        }

        if (form.id === 'admin-settings-form') {
            event.preventDefault();

            var activePreset = toNullableInt(
                form.querySelector('select[name="active_preset_id"]').value
            );
            var latitude = toNullableFloat(form.querySelector('input[name="latitude"]').value);
            var longitude = toNullableFloat(form.querySelector('input[name="longitude"]').value);
            var duration = toNullableInt(form.querySelector('input[name="duration"]').value);

            putJson('/api/v1/settings/weather-location', {
                latitude: latitude,
                longitude: longitude
            }).then(function () {
                return putJson('/api/v1/settings/active-preset', {
                    active_preset_id: activePreset
                });
            }).then(function () {
                return putJson('/api/v1/settings/slideshow-duration', {
                    slideshow_duration: duration
                });
            }).then(function () {
                window.location.href = '/';
            }).catch(function (error) {
                alert(error.message || 'Failed to save settings');
            });
            return;
        }

        if (form.id === 'admin-calendar-create-form') {
            event.preventDefault();

            var labelInput = form.querySelector('input[name="label"]');
            var urlInput = form.querySelector('input[name="url"]');
            var colorInput = form.querySelector('input[name="color"]');

            var label = labelInput ? String(labelInput.value || '').trim() : '';
            var url = urlInput ? String(urlInput.value || '').trim() : '';
            var color = colorInput ? String(colorInput.value || '').trim() : '#3182ce';

            if (!label || !url) {
                alert('Label and URL are required');
                return;
            }

            postJson('/api/v1/calendar/sources', {
                label: label,
                url: url,
                color: color || '#3182ce'
            }).then(function () {
                refreshCalendarsPartial();
            }).catch(function (error) {
                alert(error.message || 'Failed to add calendar source');
            });
            return;
        }

        if (form.id === 'admin-simulate-alarm-form') {
            event.preventDefault();

            var delayInput = form.querySelector('input[name="delay_seconds"]');
            var delaySeconds = delayInput ? parseInt(delayInput.value, 10) : 0;

            if (isNaN(delaySeconds) || delaySeconds < 0) {
                alert('Delay must be a non-negative integer');
                return;
            }

            postJson('/api/v1/alarms/simulated', {
                delay_seconds: delaySeconds
            }).then(function () {
                refreshDebugPartial();
            }).catch(function (error) {
                alert(error.message || 'Failed to create simulated alarm');
            });
        }
    });

    document.body.addEventListener('click', function (event) {
        var deleteButton = event.target.closest('[data-api-delete-image-id]');
        if (!deleteButton) return;

        event.preventDefault();
        var imageId = parseInt(deleteButton.getAttribute('data-api-delete-image-id'), 10);
        var presetId = parseInt(deleteButton.getAttribute('data-preset-id'), 10);
        console.log('[admin] delete image clicked, imageId=', imageId, 'presetId=', presetId);
        if (!window.confirm('Delete this photo?')) return;

        fetch('/api/v1/images/' + imageId, {
            method: 'DELETE'
        }).then(function (response) {
            if (!response.ok) {
                return parseJsonDetail(response).then(function (detail) {
                    throw new Error(detail);
                });
            }
            var path = '/admin/partials/gallery';
            if (!isNaN(presetId)) {
                path += '?preset_id=' + presetId;
            }
            refreshAdminContent(path);
        }).catch(function (error) {
            alert(error.message || 'Failed to delete image');
        });
    });

    document.body.addEventListener('click', function (event) {
        var syncButton = event.target.closest('#btn-sync-calendars');
        if (!syncButton) return;

        event.preventDefault();

        syncButton.setAttribute('disabled', 'disabled');

        var message = document.getElementById('cal-sync-msg');
        if (message) {
            message.classList.remove('d-none');
            message.textContent = 'Syncing...';
            message.style.color = '#9ae6b4';
        }

        fetch('/api/v1/calendar/sync', {
            method: 'POST'
        }).then(function (response) {
            if (!response.ok) {
                return parseJsonDetail(response).then(function (detail) {
                    throw new Error(detail);
                });
            }
            return response.json();
        }).then(function () {
            if (message) {
                message.textContent = 'Sync complete';
            }
            refreshCalendarsPartial();
        }).catch(function (error) {
            if (message) {
                message.textContent = 'Sync failed';
                message.style.color = '#f87171';
            }
            alert(error.message || 'Failed to sync calendars');
        }).finally(function () {
            syncButton.removeAttribute('disabled');
            setTimeout(function () {
                if (message) {
                    message.classList.add('d-none');
                }
            }, 2500);
        });
    });

    document.body.addEventListener('change', function (event) {
        var checkbox = event.target;
        if (!checkbox || !checkbox.matches('[data-api-calendar-default-source-id]')) {
            return;
        }

        var sourceId = parseInt(checkbox.getAttribute('data-api-calendar-default-source-id'), 10);
        if (!sourceId) return;

        putJson('/api/v1/calendar/sources/' + sourceId + '/default-alarm', {
            default_alarm_for_all_events: checkbox.checked
        }).then(function () {
            refreshCalendarsPartial();
        }).catch(function (error) {
            checkbox.checked = !checkbox.checked;
            alert(error.message || 'Failed to update default alarm policy');
        });
    });

    document.body.addEventListener('click', function (event) {
        var deleteCalendarButton = event.target.closest('[data-api-delete-calendar-source-id]');
        if (!deleteCalendarButton) return;

        event.preventDefault();

        if (!window.confirm('Are you sure you want to remove this calendar?')) {
            return;
        }

        var sourceId = parseInt(deleteCalendarButton.getAttribute('data-api-delete-calendar-source-id'), 10);
        if (!sourceId) return;

        fetch('/api/v1/calendar/sources/' + sourceId, {
            method: 'DELETE'
        }).then(function (response) {
            if (!response.ok) {
                return parseJsonDetail(response).then(function (detail) {
                    throw new Error(detail);
                });
            }
            refreshCalendarsPartial();
        }).catch(function (error) {
            alert(error.message || 'Failed to remove calendar source');
        });
    });

})();
