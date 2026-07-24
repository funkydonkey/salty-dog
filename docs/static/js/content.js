/**
 * Content fetching and caching layer for Salty Dog PWA.
 *
 * Handles network requests with localStorage fallback for offline use.
 * The backend serves content as a single JSON bundle at /api/content
 * and exposes a lightweight version check at /api/content/version.
 */

// eslint-disable-next-line no-var
var SaltyContent = (function () {
  'use strict';

  var STORAGE_KEY = 'saltydog_content';
  var STORAGE_HASH_KEY = 'saltydog_content_hash';

  /**
   * Check whether the browser reports network connectivity.
   * Note: navigator.onLine can return false positives (connected to a network
   * but no internet), so we always attempt network requests and fall back.
   */
  function isOnline() {
    return navigator.onLine;
  }

  /**
   * Read cached content bundle from localStorage.
   * Returns null if nothing is cached or data is corrupted.
   */
  function getCachedContent() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (err) {
      console.warn('Failed to read cached content:', err);
      return null;
    }
  }

  /**
   * Write content bundle to localStorage.
   * Also stores the content_hash separately for quick version checks.
   */
  function cacheContent(data) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      if (data && data.content_hash) {
        localStorage.setItem(STORAGE_HASH_KEY, data.content_hash);
      }
    } catch (err) {
      // Storage might be full — not critical, app still works without cache
      console.warn('Failed to cache content:', err);
    }
  }

  /**
   * Fetch the full content bundle from the API.
   * Returns parsed JSON or throws on network/server error.
   */
  function fetchContent() {
    var url = (typeof window !== 'undefined' && window.SALTY_CONTENT_URL) || '/api/content';
    return fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Server returned ' + response.status);
        }
        return response.json();
      });
  }

  /**
   * Lightweight version check — only fetches hash and built_at.
   * Returns { content_hash, built_at } or throws on error.
   * On static hosts (no dedicated version endpoint) this can point at the
   * same URL as fetchContent(); the caller only reads content_hash/built_at.
   */
  function checkVersion() {
    var url = (typeof window !== 'undefined' && window.SALTY_VERSION_URL) || '/api/content/version';
    return fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Version check failed: ' + response.status);
        }
        return response.json();
      });
  }

  /**
   * Main content retrieval function.
   *
   * Strategy:
   * 1. If online, check version against cached hash.
   *    - If hash differs (or no cache), fetch full content and cache it.
   *    - If hash matches, return cached content (saves bandwidth).
   * 2. If offline, return cached content.
   * 3. If offline and no cache, throw an error.
   *
   * Returns a Promise that resolves to the content bundle object.
   */
  function getContent() {
    var cached = getCachedContent();
    var cachedHash = localStorage.getItem(STORAGE_HASH_KEY) || '';

    if (!isOnline()) {
      if (cached) {
        console.log('Offline — using cached content');
        return Promise.resolve(cached);
      }
      return Promise.reject(new Error('Нет подключения к сети и нет сохранённых данных'));
    }

    // Online: try version check first to avoid downloading unchanged content
    return checkVersion()
      .then(function (version) {
        if (version.content_hash && version.content_hash === cachedHash && cached) {
          console.log('Content unchanged (hash match), using cache');
          return cached;
        }
        // Content has changed or we have no cache — fetch full bundle
        return fetchContent().then(function (data) {
          cacheContent(data);
          console.log('Content updated and cached');
          return data;
        });
      })
      .catch(function (err) {
        // Version check failed (server down?) — try full fetch, then cache
        console.warn('Version check failed, trying full fetch:', err.message);
        return fetchContent()
          .then(function (data) {
            cacheContent(data);
            return data;
          })
          .catch(function () {
            // Network completely unavailable — fall back to cache
            if (cached) {
              console.log('Network error — using cached content');
              return cached;
            }
            throw new Error('Не удалось загрузить данные. Проверьте подключение к сети.');
          });
      });
  }

  // Public API
  return {
    getContent: getContent,
    fetchContent: fetchContent,
    getCachedContent: getCachedContent,
    cacheContent: cacheContent,
    checkVersion: checkVersion,
    isOnline: isOnline
  };
})();
