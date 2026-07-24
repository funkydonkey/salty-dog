/**
 * Leaflet map integration for Salty Dog PWA.
 *
 * Displays the sailing route with numbered waypoint markers and a connecting
 * polyline. Falls back to a centered Croatia view when no waypoints exist.
 */

// eslint-disable-next-line no-var
var SaltyMap = (function () {
  'use strict';

  var map = null;
  var markersLayer = null;
  var routeLine = null;

  // Default center: roughly middle of Croatian coast
  var CROATIA_CENTER = [43.5, 16.0];
  var CROATIA_ZOOM = 7;

  // Route line style
  var ROUTE_LINE_OPTIONS = {
    color: '#506300',
    weight: 3,
    opacity: 0.7,
    dashArray: '8, 6',
    lineCap: 'round'
  };

  /**
   * Create a circular numbered marker icon using Leaflet DivIcon.
   * Returns a Leaflet DivIcon with the waypoint number centered inside.
   */
  function createNumberedIcon(number) {
    return L.divIcon({
      className: '', // Suppress default leaflet-div-icon styles
      html: '<div class="waypoint-marker">' + number + '</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -18]
    });
  }

  /**
   * Build popup HTML for a waypoint.
   */
  function waypointPopupHtml(waypoint, index) {
    var html = '<div class="waypoint-popup">';
    html += '<strong>' + (index + 1) + '. ' + escapeHtml(waypoint.name) + '</strong>';
    if (waypoint.description) {
      html += '<p>' + escapeHtml(waypoint.description) + '</p>';
    }
    html += '</div>';
    return html;
  }

  /**
   * Basic HTML escaping to prevent XSS in popup content.
   */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Show a placeholder message when no waypoints are available.
   */
  function showPlaceholder(container) {
    container.innerHTML =
      '<div class="map-placeholder">' +
        '<div class="map-placeholder-icon">&#x1F30A;</div>' +
        '<p class="map-placeholder-text">Капитан думает об этом, как надумает — так контент появится</p>' +
      '</div>';
  }

  /**
   * Initialize the Leaflet map inside the given container element.
   *
   * Must be called when the container is visible in the DOM (Leaflet requires
   * a visible container to calculate tile positions correctly).
   *
   * @param {string} containerId - DOM id of the map container
   * @param {Array} waypoints - Array of {name, lat, lng, description} objects
   */
  function init(containerId, waypoints) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error('Map container not found:', containerId);
      return;
    }

    // If no Leaflet loaded (offline without cached tiles), show placeholder
    if (typeof L === 'undefined') {
      showPlaceholder(container);
      return;
    }

    // If no waypoints, show placeholder instead of empty map
    if (!waypoints || waypoints.length === 0) {
      showPlaceholder(container);
      return;
    }

    // Destroy previous map instance if re-initializing
    if (map) {
      map.remove();
      map = null;
    }

    map = L.map(containerId, {
      zoomControl: true,
      attributionControl: true,
      // Disable scroll zoom on mobile to avoid hijacking page scroll
      scrollWheelZoom: false
    });

    // Enable scroll zoom only after user clicks the map
    map.once('focus', function () {
      map.scrollWheelZoom.enable();
    });

    // Tile layer — OpenStreetMap
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
    }).addTo(map);

    // Add waypoint markers
    markersLayer = L.layerGroup().addTo(map);
    var latLngs = [];

    waypoints.forEach(function (wp, i) {
      var latlng = [wp.lat, wp.lng];
      latLngs.push(latlng);

      var marker = L.marker(latlng, {
        icon: createNumberedIcon(i + 1),
        title: wp.name
      });

      marker.bindPopup(waypointPopupHtml(wp, i), {
        maxWidth: 220,
        closeButton: true
      });

      markersLayer.addLayer(marker);
    });

    // Draw route polyline connecting waypoints in order
    if (latLngs.length >= 2) {
      routeLine = L.polyline(latLngs, ROUTE_LINE_OPTIONS).addTo(map);
    }

    // Fit bounds to show all waypoints with comfortable padding
    if (latLngs.length > 0) {
      var bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    }
  }

  /**
   * Invalidate map size — call this whenever the map container becomes visible
   * (e.g., switching to the map tab). Leaflet needs this to recalculate tiles.
   */
  function invalidateSize() {
    if (map) {
      setTimeout(function () {
        map.invalidateSize();
      }, 100);
    }
  }

  /**
   * Check if the map has been initialized.
   */
  function isInitialized() {
    return map !== null;
  }

  return {
    init: init,
    invalidateSize: invalidateSize,
    isInitialized: isInitialized
  };
})();
