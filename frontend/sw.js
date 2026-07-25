/**
 * Salty Dog — Service Worker
 *
 * Caching strategy:
 * - Static assets (CSS, JS, manifest, icons): cache-first (fast loads)
 * - API responses (/api/content): network-first (fresh data when online, cached when offline)
 * - Map tiles (OpenStreetMap): cache-first with network fallback (tiles rarely change)
 * - HTML pages: network-first (always try to get latest shell)
 */

// Cache version — update this when deploying new frontend assets.
// The content hash from the API is separate; this is for the app shell.
var CACHE_VERSION = 'saltydog-v17';
var CACHE_NAME = CACHE_VERSION;
var TILE_CACHE_NAME = 'saltydog-tiles-v1';

// App shell files to pre-cache on install
var PRECACHE_URLS = [
  '/',
  '/static/css/style.css',
  '/static/css/templates.css',
  '/static/js/content.js',
  '/static/js/map.js',
  '/static/js/templates.js',
  '/static/js/app.js',
  '/static/manifest.json'
];

// -----------------------------------------------------------------------
// Install: pre-cache the app shell
// -----------------------------------------------------------------------
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function (cache) {
        console.log('[SW] Pre-caching app shell');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(function () {
        // Activate immediately without waiting for existing clients to close
        return self.skipWaiting();
      })
  );
});

// -----------------------------------------------------------------------
// Activate: clean up old caches
// -----------------------------------------------------------------------
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (cacheNames) {
        return Promise.all(
          cacheNames
            .filter(function (name) {
              // Remove old versioned caches but keep tile cache
              return name !== CACHE_NAME && name !== TILE_CACHE_NAME;
            })
            .map(function (name) {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(function () {
        // Take control of all open tabs immediately
        return self.clients.claim();
      })
  );
});

// -----------------------------------------------------------------------
// Fetch: routing by request type
// -----------------------------------------------------------------------
self.addEventListener('fetch', function (event) {
  var url = new URL(event.request.url);

  // Skip non-GET requests (POST, etc.)
  if (event.request.method !== 'GET') return;

  // Skip cross-origin requests that aren't map tiles
  if (url.origin !== self.location.origin && !isMapTile(url)) return;

  // Route to the appropriate caching strategy
  if (isMapTile(url)) {
    event.respondWith(tileFirst(event.request));
  } else if (isApiRequest(url)) {
    event.respondWith(networkFirst(event.request));
  } else if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(event.request));
  } else {
    // HTML pages and other requests: network-first
    event.respondWith(networkFirst(event.request));
  }
});

// -----------------------------------------------------------------------
// Request classification helpers
// -----------------------------------------------------------------------

function isMapTile(url) {
  return url.hostname === 'tile.openstreetmap.org' ||
         url.hostname.match(/^[a-c]\.tile\.openstreetmap\.org$/);
}

function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/') ||
         url.pathname.match(/\.(css|js|png|jpg|jpeg|svg|ico|woff2?)$/i);
}

// -----------------------------------------------------------------------
// Caching strategies
// -----------------------------------------------------------------------

/**
 * Cache-first: serve from cache if available, otherwise fetch and cache.
 * Best for static assets that change only on deployment.
 */
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
      // Both cache and network failed — return a basic offline response
      return new Response('Offline', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    });
}

/**
 * Network-first: try network, fall back to cache if offline.
 * Best for API responses and HTML where freshness matters.
 */
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

          // For navigation requests, return the cached index page (SPA)
          if (request.mode === 'navigate') {
            return caches.match('/');
          }

          return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable'
          });
        });
    });
}

/**
 * Cache-first for map tiles with a separate, long-lived tile cache.
 * Tiles rarely change and we want fast rendering even offline.
 * Limits tile cache to ~500 entries to avoid excessive storage usage.
 */
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

                // Evict old tiles if cache is getting large
                trimCache(cache, 500);
              }
              return response;
            })
            .catch(function () {
              // Tile not available offline — return transparent 1x1 PNG
              return new Response(
                atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQABNjN9GQAAAABJRElEQkSuQmCC'),
                { headers: { 'Content-Type': 'image/png' } }
              );
            });
        });
    });
}

/**
 * Trim a cache to a maximum number of entries by removing oldest first.
 */
function trimCache(cache, maxEntries) {
  cache.keys().then(function (keys) {
    if (keys.length > maxEntries) {
      // Remove the oldest entries (first in the list)
      var toDelete = keys.length - maxEntries;
      for (var i = 0; i < toDelete; i++) {
        cache.delete(keys[i]);
      }
    }
  });
}
