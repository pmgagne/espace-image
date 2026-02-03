// Espace-Image PWA Service Worker
const CACHE_NAME = 'espaceimage-cache-v1';
const urlsToCache = [
    '/',
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
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
