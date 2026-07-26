/**
 * Salty Dog — Service Worker (GitHub Pages static build)
 *
 * Self-contained, path-relative variant for static hosting under a
 * project subpath (e.g. https://user.github.io/salty-dog/). Registered
 * from the site root (docs/) so its default scope covers the whole app.
 *
 * Caching strategy:
 * - App shell (HTML/CSS/JS/manifest/icons): cache-first
 * - content.json: network-first (fresh data when online, cached when offline)
 * - Map tiles (OpenStreetMap): cache-first with network fallback
 */

var CACHE_VERSION = 'saltydog-pages-v10';
var CACHE_NAME = CACHE_VERSION;
var TILE_CACHE_NAME = 'saltydog-tiles-v1';

var PRECACHE_URLS = [
  './',
  './index.html',
  './manifest.json',
  './static/css/style.css',
  './static/css/templates.css',
  './static/js/content.js',
  './static/js/map.js',
  './static/js/templates.js',
  './static/js/app.js',
  './static/content.json'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function (cache) {
        return cache.addAll(PRECACHE_URLS);
      })
      .then(function () {
        return self.skipWaiting();
      })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (cacheNames) {
        return Promise.all(
          cacheNames
            .filter(function (name) {
              return name !== CACHE_NAME && name !== TILE_CACHE_NAME;
            })
            .map(function (name) {
              return caches.delete(name);
            })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

self.addEventListener('fetch', function (event) {
  var url = new URL(event.request.url);

  if (event.request.method !== 'GET') return;
  if (url.origin !== self.location.origin && !isMapTile(url)) return;

  if (isMapTile(url)) {
    event.respondWith(tileFirst(event.request));
  } else if (isContentJson(url)) {
    event.respondWith(networkFirst(event.request));
  } else if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(event.request));
  } else {
    event.respondWith(networkFirst(event.request));
  }
});

function isMapTile(url) {
  return url.hostname === 'tile.openstreetmap.org' ||
         url.hostname.match(/^[a-c]\.tile\.openstreetmap\.org$/);
}

function isContentJson(url) {
  return url.pathname.indexOf('content.json') !== -1;
}

function isStaticAsset(url) {
  return url.pathname.match(/\.(css|js|png|jpg|jpeg|svg|ico|woff2?)$/i);
}

function cacheFirst(request) {
  return caches.match(request)
    .then(function (cached) {
      if (cached) return cached;
      return fetch(request)
        .then(function (response) {
          if (response.ok) {
            var clone = response.clone();
            caches.open(CACHE_NAME).then(function (cache) {
              cache.put(request, clone);
            });
          }
          return response;
        });
    })
    .catch(function () {
      return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
    });
}

function networkFirst(request) {
  return fetch(request)
    .then(function (response) {
      if (response.ok) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function (cache) {
          cache.put(request, clone);
        });
      }
      return response;
    })
    .catch(function () {
      return caches.match(request)
        .then(function (cached) {
          if (cached) return cached;
          if (request.mode === 'navigate') {
            return caches.match('./');
          }
          return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
        });
    });
}

function tileFirst(request) {
  return caches.open(TILE_CACHE_NAME)
    .then(function (cache) {
      return cache.match(request)
        .then(function (cached) {
          if (cached) return cached;
          return fetch(request)
            .then(function (response) {
              if (response.ok) {
                cache.put(request, response.clone());
                trimCache(cache, 500);
              }
              return response;
            })
            .catch(function () {
              return new Response(
                atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQABNjN9GQAAAABJRElEQkSuQmCC'),
                { headers: { 'Content-Type': 'image/png' } }
              );
            });
        });
    });
}

function trimCache(cache, maxEntries) {
  cache.keys().then(function (keys) {
    if (keys.length > maxEntries) {
      var toDelete = keys.length - maxEntries;
      for (var i = 0; i < toDelete; i++) {
        cache.delete(keys[i]);
      }
    }
  });
}
