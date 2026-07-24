/**
 * Salty Dog — Main application controller.
 *
 * Handles tab navigation, content rendering, hash routing,
 * and online/offline status monitoring.
 */

(function () {
  'use strict';

  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------
  var contentData = null;  // The full content bundle from the API
  var activeTab = 'map';   // Currently visible tab id
  var mapInitialized = false;

  // Tab IDs must match both the hash fragments and the data-tab attributes
  var TABS = ['map', 'plan', 'tips', 'crew'];

  // -----------------------------------------------------------------------
  // DOM references (resolved once on init)
  // -----------------------------------------------------------------------
  var dom = {};

  function cacheDom() {
    dom.headerTitle = document.getElementById('header-title');
    dom.headerSubtitle = document.getElementById('header-subtitle');
    dom.statusDot = document.getElementById('status-dot');
    dom.loadingScreen = document.getElementById('loading-screen');
    dom.errorScreen = document.getElementById('error-screen');
    dom.errorMessage = document.getElementById('error-message');
    dom.btnRetry = document.getElementById('btn-retry');
    dom.tabBar = document.getElementById('tab-bar');

    dom.panels = {};
    dom.buttons = {};
    dom.contentAreas = {};

    TABS.forEach(function (tab) {
      dom.panels[tab] = document.getElementById('tab-' + tab);
      dom.buttons[tab] = document.getElementById('btn-tab-' + tab);
    });

    dom.contentAreas.map = document.getElementById('map-content');
    dom.contentAreas.plan = document.getElementById('plan-content');
    dom.contentAreas.tips = document.getElementById('tips-content');
    dom.contentAreas.crew = document.getElementById('crew-content');
  }

  // -----------------------------------------------------------------------
  // Online/offline status
  // -----------------------------------------------------------------------
  function updateOnlineStatus() {
    var online = SaltyContent.isOnline();
    if (dom.statusDot) {
      dom.statusDot.classList.toggle('offline', !online);
      dom.statusDot.title = online ? 'Online' : 'Offline';
    }
  }

  // -----------------------------------------------------------------------
  // Tab navigation
  // -----------------------------------------------------------------------

  /**
   * Switch to a given tab. Updates URL hash, button states, and panel visibility.
   */
  function switchTab(tabId) {
    if (TABS.indexOf(tabId) === -1) tabId = 'map';
    activeTab = tabId;

    // Update hash without triggering hashchange
    if (window.location.hash !== '#' + tabId) {
      history.replaceState(null, '', '#' + tabId);
    }

    // Update button active states
    TABS.forEach(function (t) {
      var btn = dom.buttons[t];
      var panel = dom.panels[t];
      var isActive = t === tabId;

      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
      panel.classList.toggle('hidden', !isActive);
    });

    // Leaflet map needs a size invalidation when its container becomes visible
    if (tabId === 'map') {
      if (!mapInitialized && contentData) {
        initMap();
      } else {
        SaltyMap.invalidateSize();
      }
    }

    // Scroll content area to top on tab switch
    window.scrollTo(0, 0);
  }

  /**
   * Read the current hash and switch to that tab. Falls back to 'map'.
   */
  function handleHashRoute() {
    var hash = window.location.hash.replace('#', '');
    switchTab(hash || 'map');
  }

  // -----------------------------------------------------------------------
  // Content rendering
  // -----------------------------------------------------------------------

  /**
   * Find sections matching a given tab value and optionally a section id.
   */
  function findSections(tabValue, sectionId) {
    if (!contentData || !contentData.sections) return [];
    return contentData.sections.filter(function (s) {
      if (sectionId) return s.id === sectionId;
      return s.tab === tabValue;
    });
  }

  /**
   * Wrap all <table> elements in a scrollable container for mobile.
   * Also add ids to pages for wikilink navigation.
   */
  function postProcessHtml(html, slug) {
    // Wrap tables in a scrollable div
    var processed = html.replace(
      /<table/g,
      '<div class="table-wrap"><table'
    ).replace(
      /<\/table>/g,
      '</table></div>'
    );
    return processed;
  }

  /**
   * Generate a URL-safe slug from a page title or filename.
   */
  function slugify(text) {
    return text
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9\u0400-\u04ff-]/g, '');
  }

  /**
   * Create the SVG chevron icon used in accordion headers.
   */
  function chevronSvg() {
    return '<svg class="card-chevron" viewBox="0 0 20 20" fill="currentColor">' +
           '<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"/>' +
           '</svg>';
  }

  /**
   * Render an accordion card for a single content page.
   * @param {Object} page - { title, html_content, filename }
   * @param {Object} options - { icon, expanded, cssClass, dayBadge }
   */
  function renderAccordionCard(page, options) {
    var opts = options || {};
    var slug = slugify(page.filename || page.title);
    var expanded = opts.expanded || false;
    var extraClass = opts.cssClass ? ' ' + opts.cssClass : '';
    var html = '';

    html += '<div class="card' + extraClass + '" id="page-' + slug + '">';

    // Header
    html += '<div class="card-header" role="button" tabindex="0" ' +
            'aria-expanded="' + expanded + '" ' +
            'aria-controls="card-body-' + slug + '">';
    if (opts.icon) {
      html += '<span class="card-icon">' + opts.icon + '</span>';
    }
    if (opts.dayBadge) {
      html += '<span class="day-badge">' + escapeHtml(opts.dayBadge) + '</span>';
    }
    html += '<span class="card-title">' + escapeHtml(page.title) + '</span>';
    html += chevronSvg();
    html += '</div>';

    // Body
    html += '<div class="card-body' + (expanded ? ' open' : '') + '" id="card-body-' + slug + '">';
    html += postProcessHtml(page.html_content, slug);
    html += '</div>';

    html += '</div>';
    return html;
  }

  /**
   * Render a static (non-collapsible) card for a content page.
   */
  function renderStaticCard(page, options) {
    var opts = options || {};
    var slug = slugify(page.filename || page.title);
    var html = '';

    html += '<div class="card card--static" id="page-' + slug + '">';
    html += '<div class="card-header">';
    if (opts.icon) {
      html += '<span class="card-icon">' + opts.icon + '</span>';
    }
    html += '<span class="card-title">' + escapeHtml(page.title) + '</span>';
    html += '</div>';
    html += '<div class="card-body">';
    html += postProcessHtml(page.html_content, slug);
    html += '</div>';
    html += '</div>';
    return html;
  }

  /**
   * Render a page using rich template if available, otherwise fallback.
   */
  function renderPageOrFallback(page, section, fallbackOpts) {
    if (typeof SaltyTemplates !== 'undefined' && SaltyTemplates.canRender(page)) {
      var result = SaltyTemplates.render(page, section, contentData.trip);
      if (result !== null) return result;
    }
    return renderAccordionCard(page, fallbackOpts);
  }

  /**
   * Render the Map tab: route section pages as cards below the map.
   */
  function renderMapTab() {
    var container = dom.contentAreas.map;
    if (!container) return;

    var sections = findSections('map');
    if (sections.length === 0) {
      container.innerHTML = renderEmptyState('\u041C\u0430\u0440\u0448\u0440\u0443\u0442 \u043F\u043E\u043A\u0430 \u043D\u0435 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D');
      return;
    }

    var html = '';
    sections.forEach(function (section) {
      section.pages.forEach(function (page, i) {
        html += renderPageOrFallback(page, section, {
          icon: section.icon,
          expanded: i === 0
        });
      });
    });
    html += renderLastUpdated();
    container.innerHTML = html;
    attachAccordionListeners(container);
  }

  /**
   * Render the Plan tab: plan section pages as accordion cards.
   */
  function renderPlanTab() {
    var container = dom.contentAreas.plan;
    if (!container) return;

    var sections = findSections('plan');
    if (sections.length === 0) {
      container.innerHTML = renderEmptyState('\u041F\u043B\u0430\u043D \u043F\u043E\u043A\u0430 \u043D\u0435 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D');
      return;
    }

    var html = '';
    sections.forEach(function (section) {
      section.pages.forEach(function (page, i) {
        var dayMatch = page.title.match(/(?:Day|День)\s*(\d+)/i);
        html += renderPageOrFallback(page, section, {
          icon: section.icon,
          expanded: i === 0,
          dayBadge: dayMatch ? '\u0414\u0435\u043D\u044C ' + dayMatch[1] : null
        });
      });
    });
    html += renderLastUpdated();
    container.innerHTML = html;
    attachAccordionListeners(container);
  }

  /**
   * Render the Tips tab: safety section pages as accordion cards.
   */
  function renderTipsTab() {
    var container = dom.contentAreas.tips;
    if (!container) return;

    var sections = findSections(null, 'safety');
    if (sections.length === 0) {
      // Also try tab="tips" sections that aren't crew
      sections = contentData.sections.filter(function (s) {
        return s.tab === 'tips' && s.id !== 'crew';
      });
    }

    if (sections.length === 0) {
      container.innerHTML = renderEmptyState('\u0421\u043E\u0432\u0435\u0442\u044B \u043F\u043E\u043A\u0430 \u043D\u0435 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u044B');
      return;
    }

    var html = '';
    sections.forEach(function (section) {
      if (sections.length > 1) {
        html += renderSectionHeader(section);
      }
      section.pages.forEach(function (page) {
        html += renderPageOrFallback(page, section, {
          icon: section.icon,
          cssClass: 'card--safety'
        });
      });
    });
    html += renderLastUpdated();
    container.innerHTML = html;
    attachAccordionListeners(container);
  }

  /**
   * Render the Crew tab: crew section pages as static (non-collapsible) cards.
   */
  function renderCrewTab() {
    var container = dom.contentAreas.crew;
    if (!container) return;

    var sections = findSections(null, 'crew');
    if (sections.length === 0) {
      // Fall back: look for sections with tab="tips" and id="crew"
      // or any section with tab="crew"
      sections = contentData.sections.filter(function (s) {
        return s.tab === 'crew' || s.id === 'crew';
      });
    }

    if (sections.length === 0) {
      container.innerHTML = renderEmptyState('\u042D\u043A\u0438\u043F\u0430\u0436 \u043F\u043E\u043A\u0430 \u043D\u0435 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D');
      return;
    }

    var html = '';
    sections.forEach(function (section) {
      section.pages.forEach(function (page) {
        html += renderPageOrFallback(page, section, { icon: section.icon });
      });
    });
    html += renderLastUpdated();
    container.innerHTML = html;

    attachAccordionListeners(container);

    // Attach sub-tab listeners
    attachSubTabListeners(container);
  }

  /**
   * Render a section divider header (icon + title).
   */
  function renderSectionHeader(section) {
    return '<div class="section-header">' +
           '<span class="section-header-icon">' + section.icon + '</span>' +
           '<span class="section-header-title">' + escapeHtml(section.title) + '</span>' +
           '</div>';
  }

  /**
   * Render an empty state placeholder.
   */
  function renderEmptyState(message) {
    return '<div class="empty-state">' +
           '<div class="empty-state-icon">&#x26F5;</div>' +
           '<p class="empty-state-text">' + escapeHtml(message) + '</p>' +
           '</div>';
  }

  /**
   * Render "last updated" footer from built_at timestamp.
   */
  function renderLastUpdated() {
    if (!contentData || !contentData.built_at) return '';
    var date = new Date(contentData.built_at);
    if (isNaN(date.getTime())) return '';
    var formatted = date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
    return '<div class="last-updated">\u041E\u0431\u043D\u043E\u0432\u043B\u0435\u043D\u043E: ' + formatted + '</div>';
  }

  // -----------------------------------------------------------------------
  // Map initialization
  // -----------------------------------------------------------------------

  function initMap() {
    // Collect waypoints from the route section or top-level route object
    var waypoints = extractWaypoints();

    SaltyMap.init('map-container', waypoints);
    mapInitialized = true;
  }

  /**
   * Extract waypoints from content data.
   * Supports two data shapes:
   * 1. section.waypoints (array on a section with tab="map")
   * 2. contentData.route.waypoints (top-level route object)
   */
  function extractWaypoints() {
    if (!contentData) return [];

    // Try section-level waypoints first
    var mapSections = findSections('map');
    for (var i = 0; i < mapSections.length; i++) {
      if (mapSections[i].waypoints && mapSections[i].waypoints.length > 0) {
        return mapSections[i].waypoints;
      }
    }

    // Fall back to top-level route
    if (contentData.route && contentData.route.waypoints && contentData.route.waypoints.length > 0) {
      return contentData.route.waypoints;
    }

    return [];
  }

  // -----------------------------------------------------------------------
  // Accordion behavior
  // -----------------------------------------------------------------------

  /**
   * Attach click and keyboard listeners to all card headers within a container.
   */
  function attachAccordionListeners(container) {
    var headers = container.querySelectorAll('.card-header[role="button"]');
    headers.forEach(function (header) {
      header.addEventListener('click', toggleAccordion);
      header.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleAccordion.call(this, e);
        }
      });
    });
  }

  /**
   * Toggle an accordion card open/closed.
   */
  function toggleAccordion(e) {
    var header = e.currentTarget;
    var targetId = header.getAttribute('aria-controls');
    var body = document.getElementById(targetId);
    if (!body) return;

    var isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    header.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
  }

  // -----------------------------------------------------------------------
  // Sub-tab behavior (for nested tabs within main tabs)
  // -----------------------------------------------------------------------

  /**
   * Attach click listeners to sub-tab buttons within a container.
   */
  function attachSubTabListeners(container) {
    var buttons = container.querySelectorAll('.sub-tab-btn');
    buttons.forEach(function (button) {
      button.addEventListener('click', switchSubTab);
    });
  }

  /**
   * Switch between sub-tabs.
   */
  function switchSubTab(e) {
    var button = e.currentTarget;
    var targetSubTab = button.getAttribute('data-subtab');
    if (!targetSubTab) return;

    // Find parent container with sub-tabs
    var container = button.closest('.tab-content') || button.closest('.tab-panel');
    if (!container) return;

    // Update button states
    var allButtons = container.querySelectorAll('.sub-tab-btn');
    allButtons.forEach(function (btn) {
      btn.classList.toggle('active', btn === button);
    });

    // Update content visibility
    var allContents = container.querySelectorAll('.sub-tab-content');
    allContents.forEach(function (content) {
      var contentId = content.getAttribute('id');
      var isTarget = contentId === 'subtab-' + targetSubTab;
      content.classList.toggle('active', isTarget);
    });
  }

  // -----------------------------------------------------------------------
  // Wikilink navigation
  // -----------------------------------------------------------------------

  /**
   * Handle clicks on wikilinks — scroll to the target page card or switch tabs.
   */
  function handleWikilinkClick(e) {
    var link = e.target.closest('a.wikilink');
    if (!link) return;

    e.preventDefault();
    var href = link.getAttribute('href');
    if (!href || href.charAt(0) !== '#') return;

    var targetId = href.substring(1); // e.g., "page-safety-briefing"
    var target = document.getElementById(targetId);

    if (target) {
      // Target is in the current tab — scroll to it and open if collapsed
      var body = target.querySelector('.card-body');
      var header = target.querySelector('.card-header');
      if (body && !body.classList.contains('open') && header) {
        body.classList.add('open');
        header.setAttribute('aria-expanded', 'true');
      }
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    // Target might be in a different tab — search all panels
    for (var i = 0; i < TABS.length; i++) {
      var panel = dom.panels[TABS[i]];
      // Temporarily show panel to find element
      var wasHidden = panel.classList.contains('hidden');
      if (wasHidden) panel.classList.remove('hidden');

      var found = panel.querySelector('#' + CSS.escape(targetId));

      if (wasHidden) panel.classList.add('hidden');

      if (found) {
        switchTab(TABS[i]);
        // Wait for tab switch animation, then scroll
        setTimeout(function () {
          var el = document.getElementById(targetId);
          if (el) {
            var elBody = el.querySelector('.card-body');
            var elHeader = el.querySelector('.card-header');
            if (elBody && !elBody.classList.contains('open') && elHeader) {
              elBody.classList.add('open');
              elHeader.setAttribute('aria-expanded', 'true');
            }
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 250);
        return;
      }
    }
  }

  // -----------------------------------------------------------------------
  // Header updates
  // -----------------------------------------------------------------------

  function updateHeader() {
    if (!contentData || !contentData.trip) return;

    var trip = contentData.trip;
    dom.headerTitle.textContent = trip.name || 'Salty Dog';

    var parts = [];
    if (trip.boat && trip.boat !== 'TBD') parts.push(trip.boat);
    if (trip.dates && trip.dates !== 'TBD') parts.push(trip.dates);
    dom.headerSubtitle.textContent = parts.join(' \u2022 ');
  }

  // -----------------------------------------------------------------------
  // Screens (loading / error / content)
  // -----------------------------------------------------------------------

  function showLoading() {
    dom.loadingScreen.classList.remove('hidden');
    dom.errorScreen.classList.add('hidden');
    TABS.forEach(function (t) { dom.panels[t].classList.add('hidden'); });
    dom.tabBar.style.display = 'none';
  }

  function showError(message) {
    dom.loadingScreen.classList.add('hidden');
    dom.errorScreen.classList.remove('hidden');
    dom.errorMessage.textContent = message;
    TABS.forEach(function (t) { dom.panels[t].classList.add('hidden'); });
    dom.tabBar.style.display = 'none';
  }

  function showContent() {
    dom.loadingScreen.classList.add('hidden');
    dom.errorScreen.classList.add('hidden');
    dom.tabBar.style.display = '';
    handleHashRoute();
  }

  // -----------------------------------------------------------------------
  // Utility
  // -----------------------------------------------------------------------

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------

  function loadContent() {
    showLoading();

    SaltyContent.getContent()
      .then(function (data) {
        contentData = data;
        updateHeader();
        renderMapTab();
        renderPlanTab();
        renderTipsTab();
        renderCrewTab();
        showContent();
      })
      .catch(function (err) {
        console.error('Failed to load content:', err);
        showError(err.message || '\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044C \u0434\u0430\u043D\u043D\u044B\u0435');
      });
  }

  function init() {
    cacheDom();
    updateOnlineStatus();

    // Tab button clicks
    TABS.forEach(function (tab) {
      dom.buttons[tab].addEventListener('click', function () {
        switchTab(tab);
      });
    });

    // Hash routing
    window.addEventListener('hashchange', handleHashRoute);

    // Online/offline events
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    // Retry button
    dom.btnRetry.addEventListener('click', loadContent);

    // Wikilink clicks (delegated to document)
    document.addEventListener('click', handleWikilinkClick);

    // Load content
    loadContent();
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
