// Espace-Image PWA Service Worker
const CACHE_NAME = 'espaceimage-cache-v2';  // Bumped version to force refresh
const urlsToCache = [
    '/static/espaceimage-192.png',
    '/static/espaceimage-512.png',
    '/static/manifest.json',
    '/static/legacy-manifest.json',
    '/static/admin-manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())  // Activate immediately
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);  // Delete old caches
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    // Network-first strategy for HTML, JS, CSS (always get fresh version)
    if (event.request.url.match(/\.(html|js|css)$/i) || event.request.url.endsWith('/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))  // Fallback to cache on network error
        );
    } else {
        // Cache-first for images and static assets
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
    }
});
