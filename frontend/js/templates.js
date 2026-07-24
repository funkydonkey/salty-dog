/**
 * Salty Dog — Template renderer module.
 *
 * Renders structured_data into rich HTML layouts matching the Aero Marine design.
 * Falls back gracefully: if canRender() is false, the caller uses accordion cards.
 */

var SaltyTemplates = (function () {
  'use strict';

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  function canRender(page) {
    return !!(page && page.template && page.structured_data &&
              Object.keys(page.structured_data).length > 0);
  }

  function render(page, section, tripData) {
    try {
      var renderer = RENDERERS[page.template];
      if (!renderer) return null;
      return renderer(page.structured_data, page, section, tripData);
    } catch (e) {
      console.warn('[SaltyTemplates] Render failed for', page.template, e);
      return null;
    }
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  function esc(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function pad2(n) {
    return n < 10 ? '0' + n : '' + n;
  }

  function daysUntil(dateStr) {
    if (!dateStr) return null;
    var target = new Date(dateStr + 'T00:00:00');
    if (isNaN(target.getTime())) return null;
    var now = new Date();
    now.setHours(0, 0, 0, 0);
    var diff = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    return diff >= 0 ? diff : null;
  }

  function hasValue(s) {
    if (!s) return false;
    var trimmed = s.trim();
    return trimmed !== '' && trimmed !== 'NM' && trimmed !== '[ ]';
  }

  // -----------------------------------------------------------------------
  // route_plan — Vertical timeline with day markers
  // -----------------------------------------------------------------------

  function renderRoutePlan(data) {
    var days = data.days || [];
    if (days.length === 0) return '<div class="tpl-placeholder">\u041C\u0430\u0440\u0448\u0440\u0443\u0442 \u0435\u0449\u0451 \u043D\u0435 \u0441\u043E\u0441\u0442\u0430\u0432\u043B\u0435\u043D</div>';

    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u041C\u0430\u0440\u0448\u0440\u0443\u0442 \u043F\u043E \u0434\u043D\u044F\u043C</div>';
    html += '<div class="page-hero__title">Route Plan</div>';
    html += '</div>';

    html += '<div class="timeline"><div class="timeline__track"></div>';

    for (var i = 0; i < days.length; i++) {
      var d = days[i];
      var dayLabel = '\u0414\u0435\u043D\u044C ' + d.day;
      var isEmpty = !hasValue(d.from) && !hasValue(d.to) && d.bullets.length === 0;
      var markerClass = isEmpty ? 'timeline__marker timeline__marker--empty' : 'timeline__marker';

      html += '<div class="timeline__day">';
      html += '<div class="' + markerClass + '">' + pad2(d.day) + '</div>';
      html += '<div class="timeline__step-number">' + pad2(d.day) + '</div>';
      html += '<div class="timeline__card">';
      html += '<div class="timeline__day-title">' + esc(dayLabel);
      if (d.title) html += ' \u2014 ' + esc(d.title);
      html += '</div>';

      // Details
      var details = [
        ['Откуда', d.from], ['Куда', d.to], ['Дистанция', d.nm],
        ['Курс', d.course], ['Стоянка', d.anchorage]
      ];
      var hasDetails = false;
      for (var j = 0; j < details.length; j++) {
        if (hasValue(details[j][1])) { hasDetails = true; break; }
      }

      if (hasDetails) {
        for (var k = 0; k < details.length; k++) {
          if (hasValue(details[k][1])) {
            html += '<div class="timeline__detail-row">';
            html += '<span class="timeline__detail-key">' + esc(details[k][0]) + '</span>';
            html += '<span class="timeline__detail-value">' + esc(details[k][1]) + '</span>';
            html += '</div>';
          }
        }
      }

      // Bullets (for day 0 etc.)
      if (d.bullets && d.bullets.length > 0) {
        html += '<ul class="timeline__bullets">';
        for (var b = 0; b < d.bullets.length; b++) {
          html += '<li>' + esc(d.bullets[b]) + '</li>';
        }
        html += '</ul>';
      }

      // Badges
      var badges = [];
      if (hasValue(d.to)) badges.push({text: d.to, type: 'location'});
      if (hasValue(d.nm)) badges.push({text: d.nm, type: 'info'});
      if (hasValue(d.highlights)) badges.push({text: d.highlights, type: 'info'});

      if (badges.length > 0) {
        html += '<div class="timeline__badges">';
        for (var bi = 0; bi < badges.length; bi++) {
          html += '<span class="timeline__badge timeline__badge--' + badges[bi].type + '">' + esc(badges[bi].text) + '</span>';
        }
        html += '</div>';
      }

      if (isEmpty) {
        html += '<div class="tpl-placeholder">\u0414\u0430\u043D\u043D\u044B\u0435 \u0431\u0443\u0434\u0443\u0442 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u044B</div>';
      }

      html += '</div></div>';
    }

    html += '</div>';
    return html;
  }

  // -----------------------------------------------------------------------
  // travel_logistics — Countdown hero + bento grid
  // -----------------------------------------------------------------------

  function renderTravelLogistics(data, page, section, tripData) {
    var html = '';

    // Countdown
    var departure = tripData && tripData.departure_date;
    var daysLeft = daysUntil(departure);

    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u041F\u0435\u0440\u0435\u043B\u0451\u0442\u044B \u0438 \u0442\u0440\u0430\u043D\u0441\u0444\u0435\u0440\u044B</div>';
    if (daysLeft !== null) {
      html += '<div class="countdown">';
      html += '<div class="countdown__number">' + daysLeft + '</div>';
      html += '<div class="countdown__unit">\u0434\u043D\u0435\u0439 \u0434\u043E \u0432\u044B\u0445\u043E\u0434\u0430</div>';
      html += '</div>';
    } else {
      html += '<div class="page-hero__title">Travel Logistics</div>';
    }
    html += '</div>';

    html += '<div class="bento-grid">';

    // Airports
    var airports = data.airports || [];
    if (airports.length > 0) {
      html += '<div class="bento-card bento-card--wide">';
      html += '<div class="bento-card__label">\u0410\u044D\u0440\u043E\u043F\u043E\u0440\u0442\u044B</div>';
      for (var a = 0; a < airports.length; a++) {
        var ap = airports[a];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(ap['\u0410\u044D\u0440\u043E\u043F\u043E\u0440\u0442'] || '') + '</span>';
        html += '<span class="bento-card__row-value">' + esc(ap['\u041A\u043E\u0434'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Flights
    var flights = data.flights || [];
    if (flights.length > 0) {
      html += '<div class="bento-card bento-card--wide">';
      html += '<div class="bento-card__label">\u041F\u0435\u0440\u0435\u043B\u0451\u0442\u044B</div>';
      for (var f = 0; f < flights.length; f++) {
        var fl = flights[f];
        var who = fl['\u0423\u0447\u0430\u0441\u0442\u043D\u0438\u043A / \u0441\u0435\u043C\u044C\u044F'] || '';
        var from = fl['\u041E\u0442\u043A\u0443\u0434\u0430'] || '';
        if (hasValue(who) || hasValue(from)) {
          html += '<div class="bento-card__row">';
          html += '<span class="bento-card__row-label">' + esc(who) + '</span>';
          html += '<span class="bento-card__row-value">' + esc(from) + '</span>';
          html += '</div>';
        }
      }
      if (!flights.some(function(fl) { return hasValue(fl['\u0423\u0447\u0430\u0441\u0442\u043D\u0438\u043A / \u0441\u0435\u043C\u044C\u044F']); })) {
        html += '<div class="tpl-placeholder">\u0414\u0430\u043D\u043D\u044B\u0435 \u043E \u043F\u0435\u0440\u0435\u043B\u0451\u0442\u0430\u0445 \u0431\u0443\u0434\u0443\u0442 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u044B</div>';
      }
      html += '</div>';
    }

    // Transfers
    var transfers = data.transfers || [];
    if (transfers.length > 0) {
      html += '<div class="bento-card">';
      html += '<div class="bento-card__icon"><span class="material-symbols-outlined">local_taxi</span></div>';
      html += '<div class="bento-card__label">\u0422\u0440\u0430\u043D\u0441\u0444\u0435\u0440</div>';
      for (var t = 0; t < transfers.length; t++) {
        var tr = transfers[t];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(tr['\u0412\u0430\u0440\u0438\u0430\u043D\u0442'] || '') + '</span>';
        html += '<span class="bento-card__row-value">' + esc(tr['\u0426\u0435\u043D\u0430'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Carry-on
    var carryOn = data.carry_on || [];
    if (carryOn.length > 0) {
      html += '<div class="bento-card">';
      html += '<div class="bento-card__icon"><span class="material-symbols-outlined">luggage</span></div>';
      html += '<div class="bento-card__label">\u0420\u0443\u0447\u043D\u0430\u044F \u043A\u043B\u0430\u0434\u044C</div>';
      for (var c = 0; c < carryOn.length; c++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(carryOn[c]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>';
    return html;
  }

  // -----------------------------------------------------------------------
  // safety_briefing — Protocol cards with numbered steps
  // -----------------------------------------------------------------------

  function renderSafetyBriefing(data) {
    var sections = data.sections || [];
    if (sections.length === 0) return '<div class="tpl-placeholder">\u0411\u0440\u0438\u0444\u0438\u043D\u0433 \u043D\u0435 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043D</div>';

    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="status-badge">';
    html += '<div class="status-badge__dot"></div>';
    html += '<span class="status-badge__text">\u0412\u0441\u0435 \u043F\u0440\u043E\u0442\u043E\u043A\u043E\u043B\u044B \u0430\u043A\u0442\u0438\u0432\u043D\u044B</span>';
    html += '</div>';
    html += '<div class="page-hero__title">Safety Briefing</div>';
    html += '<div class="page-hero__subtitle">\u041F\u0440\u043E\u0432\u0435\u0441\u0442\u0438 \u043F\u0435\u0440\u0435\u0434 \u0432\u044B\u0445\u043E\u0434\u043E\u043C \u0432 \u043F\u0435\u0440\u0432\u044B\u0439 \u0434\u0435\u043D\u044C</div>';
    html += '</div>';

    html += '<div class="protocol-grid">';

    for (var i = 0; i < sections.length; i++) {
      var sec = sections[i];
      var isEmergency = sec.number <= 2;

      html += '<div class="protocol-card' + (isEmergency ? ' protocol-card--emergency' : '') + '">';
      html += '<div class="protocol-card__header">';
      html += '<div class="protocol-card__title">' + esc(sec.title) + '</div>';
      html += '<div class="protocol-card__badge">' + pad2(sec.number) + '</div>';
      html += '</div>';

      for (var j = 0; j < sec.items.length; j++) {
        var item = sec.items[j];
        if (item.is_checkbox) {
          var doneClass = item.checked ? ' protocol-card__check--done' : '';
          html += '<div class="protocol-card__check' + doneClass + '">';
          html += '<div class="protocol-card__check-icon"></div>';
          html += '<span>' + esc(item.text) + '</span>';
          html += '</div>';
        } else {
          html += '<div class="protocol-card__step">';
          html += '<span class="protocol-card__step-number">' + pad2(j + 1) + '</span>';
          html += '<span class="protocol-card__step-text">' + esc(item.text) + '</span>';
          html += '</div>';
        }
      }

      html += '</div>';
    }

    html += '</div>';
    return html;
  }

  // -----------------------------------------------------------------------
  // emergency_contacts — Categorized contact cards
  // -----------------------------------------------------------------------

  function renderEmergencyContacts(data) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u042D\u043A\u0441\u0442\u0440\u0435\u043D\u043D\u044B\u0435 \u043A\u043E\u043D\u0442\u0430\u043A\u0442\u044B</div>';
    html += '<div class="page-hero__title">Emergency</div>';
    html += '</div>';

    // Emergency services
    var services = data.services || [];
    if (services.length > 0) {
      html += '<div class="contact-card contact-card--emergency">';
      html += '<div class="contact-card__title">\u042D\u043A\u0441\u0442\u0440\u0435\u043D\u043D\u044B\u0435 \u0441\u043B\u0443\u0436\u0431\u044B</div>';
      for (var s = 0; s < services.length; s++) {
        var svc = services[s];
        var num = svc['\u041D\u043E\u043C\u0435\u0440'] || '';
        var isMain = num.indexOf('**') >= 0 || num === '112' || num.indexOf('112') >= 0;
        var cleanNum = num.replace(/\*\*/g, '');
        html += '<div class="contact-card__row">';
        html += '<span class="contact-card__service">' + esc((svc['\u0421\u043B\u0443\u0436\u0431\u0430'] || '').replace(/\*\*/g, '')) + '</span>';
        html += '<span class="contact-card__number' + (isMain ? ' contact-card__number--prominent' : '') + '">' + esc(cleanNum) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    html += '<div class="contact-grid">';

    // Hospitals
    var hospitals = data.hospitals || [];
    if (hospitals.length > 0) {
      html += '<div class="contact-card">';
      html += '<div class="contact-card__title">\u0411\u043E\u043B\u044C\u043D\u0438\u0446\u044B</div>';
      for (var h = 0; h < hospitals.length; h++) {
        var hosp = hospitals[h];
        html += '<div class="contact-card__row">';
        html += '<span class="contact-card__service">' + esc(hosp['\u0413\u043E\u0440\u043E\u0434'] || '') + '</span>';
        html += '<span class="contact-card__number">' + esc(hosp['\u0422\u0435\u043B\u0435\u0444\u043E\u043D'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Charter company
    var charter = data.charter || {};
    if (Object.keys(charter).length > 0) {
      html += '<div class="contact-card">';
      html += '<div class="contact-card__title">\u0427\u0430\u0440\u0442\u0435\u0440\u043D\u0430\u044F \u043A\u043E\u043C\u043F\u0430\u043D\u0438\u044F</div>';
      var charterKeys = Object.keys(charter);
      for (var ck = 0; ck < charterKeys.length; ck++) {
        var cv = charter[charterKeys[ck]];
        if (hasValue(cv)) {
          html += '<div class="contact-card__row">';
          html += '<span class="contact-card__service">' + esc(charterKeys[ck]) + '</span>';
          html += '<span class="contact-card__number">' + esc(cv) + '</span>';
          html += '</div>';
        }
      }
      if (!charterKeys.some(function(k) { return hasValue(charter[k]); })) {
        html += '<div class="tpl-placeholder">\u0414\u0430\u043D\u043D\u044B\u0435 \u0431\u0443\u0434\u0443\u0442 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u044B</div>';
      }
      html += '</div>';
    }

    html += '</div>';

    // VHF channels
    var vhf = data.vhf || [];
    if (vhf.length > 0) {
      html += '<div class="tpl-section-title">VHF \u043A\u0430\u043D\u0430\u043B\u044B</div>';
      html += '<div class="vhf-grid">';
      for (var v = 0; v < vhf.length; v++) {
        html += '<div class="vhf-card">';
        html += '<div class="vhf-card__channel">' + esc(vhf[v]['\u041A\u0430\u043D\u0430\u043B'] || '') + '</div>';
        html += '<div class="vhf-card__label">' + esc(vhf[v]['\u041D\u0430\u0437\u043D\u0430\u0447\u0435\u043D\u0438\u0435'] || '') + '</div>';
        html += '</div>';
      }
      html += '</div>';
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // kids_on_board — Rules + equipment + activities + schedule
  // -----------------------------------------------------------------------

  function renderKidsOnBoard(data) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u0414\u0435\u0442\u0438 \u043D\u0430 \u0431\u043E\u0440\u0442\u0443</div>';
    html += '<div class="page-hero__title">Kids on Board</div>';
    html += '</div>';

    // Rules
    var rules = data.rules || [];
    if (rules.length > 0) {
      html += '<div class="tpl-section-title">\u041F\u0440\u0430\u0432\u0438\u043B\u0430 \u0431\u0435\u0437\u043E\u043F\u0430\u0441\u043D\u043E\u0441\u0442\u0438</div>';
      html += '<div class="rules-list">';
      for (var r = 0; r < rules.length; r++) {
        html += '<div class="rules-list__item">';
        html += '<span class="rules-list__number">' + pad2(r + 1) + '</span>';
        html += '<span class="rules-list__text">' + esc(rules[r]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Equipment
    var equipment = data.equipment || [];
    if (equipment.length > 0) {
      html += '<div class="tpl-section-title">\u0421\u043D\u0430\u0440\u044F\u0436\u0435\u043D\u0438\u0435</div>';
      html += '<div class="checklist-card">';
      for (var e = 0; e < equipment.length; e++) {
        var eq = equipment[e];
        var doneClass = eq.checked ? ' checklist-card__item--done' : '';
        html += '<div class="checklist-card__item' + doneClass + '">';
        html += '<div class="checklist-card__item-check"></div>';
        html += '<span>' + esc(eq.text) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Activities
    var activities = data.activities || {};
    var actKeys = Object.keys(activities);
    if (actKeys.length > 0) {
      html += '<div class="tpl-section-title">\u0410\u043A\u0442\u0438\u0432\u043D\u043E\u0441\u0442\u0438</div>';
      html += '<div class="activity-grid">';
      var icons = {'\u041D\u0430 \u0432\u043E\u0434\u0435': 'pool', '\u041D\u0430 \u043B\u043E\u0434\u043A\u0435': 'sailing', '\u041D\u0430 \u0431\u0435\u0440\u0435\u0433\u0443': 'castle'};
      for (var ai = 0; ai < actKeys.length; ai++) {
        var catName = actKeys[ai];
        var items = activities[catName];
        var icon = icons[catName] || 'interests';
        html += '<div class="activity-card">';
        html += '<div class="activity-card__title"><span class="material-symbols-outlined" style="font-size: 1.125rem;">' + icon + '</span>' + esc(catName) + '</div>';
        for (var aii = 0; aii < items.length; aii++) {
          html += '<div class="activity-card__item">' + esc(items[aii]) + '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }

    // Schedule
    var schedule = data.schedule || [];
    if (schedule.length > 0) {
      html += '<div class="tpl-section-title">\u0420\u0435\u0436\u0438\u043C \u0434\u043D\u044F</div>';
      html += '<div class="bento-card">';
      for (var si = 0; si < schedule.length; si++) {
        var sch = schedule[si];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(sch['\u0412\u0440\u0435\u043C\u044F'] || '') + '</span>';
        html += '<span class="bento-card__row-value">' + esc(sch['\u0410\u043A\u0442\u0438\u0432\u043D\u043E\u0441\u0442\u044C'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // crew_list — Crew roster cards + watch schedule
  // -----------------------------------------------------------------------

  function renderCrewList(data) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u042D\u043A\u0438\u043F\u0430\u0436</div>';
    html += '<div class="page-hero__title">Crew</div>';
    html += '</div>';

    // Sub-tabs navigation
    html += '<div class="sub-tabs">';
    html += '<button class="sub-tab-btn active" data-subtab="roster">\u0421\u043E\u0441\u0442\u0430\u0432</button>';
    html += '<button class="sub-tab-btn" data-subtab="organization">\u041E\u0440\u0433\u0430\u043D\u0438\u0437\u0430\u0446\u0438\u044F</button>';
    html += '</div>';

    // Tab 1: Roster (Crew members + roles)
    html += '<div class="sub-tab-content active" id="subtab-roster">';

    // Crew members
    var members = data.members || [];
    if (members.length > 0) {
      html += '<div class="crew-grid">';
      for (var m = 0; m < members.length; m++) {
        var mem = members[m];
        var name = mem['\u0418\u043C\u044F'] || '';
        var role = mem['\u0420\u043E\u043B\u044C \u043D\u0430 \u0431\u043E\u0440\u0442\u0443'] || '';
        var exp = mem['\u041E\u043F\u044B\u0442'] || '';

        if (!hasValue(name) && !hasValue(role)) continue;

        var initials = name ? name.charAt(0).toUpperCase() : (mem['#'] || '?');
        html += '<div class="crew-card">';
        html += '<div class="crew-card__avatar">' + esc(initials) + '</div>';
        html += '<div class="crew-card__info">';
        html += '<div class="crew-card__name">' + (hasValue(name) ? esc(name) : '\u0423\u0447\u0430\u0441\u0442\u043D\u0438\u043A ' + esc(mem['#'] || '')) + '</div>';
        if (hasValue(role)) html += '<span class="crew-card__role">' + esc(role) + '</span>';
        if (hasValue(exp)) html += '<div class="crew-card__detail">' + esc(exp) + '</div>';
        html += '</div></div>';
      }
      html += '</div>';
    }

    // Roles
    var roles = data.roles || [];
    if (roles.length > 0) {
      html += '<div class="tpl-section-title">\u0420\u043E\u043B\u0438</div>';
      html += '<div class="bento-card">';
      for (var ri = 0; ri < roles.length; ri++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(roles[ri]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>'; // End subtab-roster

    // Tab 2: Organization (Watch schedule + life jackets)
    html += '<div class="sub-tab-content" id="subtab-organization">';

    // Watch schedule
    var watch = data.watch_schedule || [];
    if (watch.length > 0) {
      html += '<div class="tpl-section-title">\u0412\u0430\u0445\u0442\u0435\u043D\u043D\u043E\u0435 \u0440\u0430\u0441\u043F\u0438\u0441\u0430\u043D\u0438\u0435</div>';
      html += '<div class="bento-card">';
      for (var w = 0; w < watch.length; w++) {
        var ws = watch[w];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(ws['\u0412\u0440\u0435\u043C\u044F'] || '') + '</span>';
        html += '<span class="bento-card__row-value">' + esc(ws['\u0417\u0430\u0434\u0430\u0447\u0438'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Life jackets
    var jackets = data.life_jackets || [];
    if (jackets.length > 0) {
      html += '<div class="tpl-section-title">\u0421\u043F\u0430\u0441\u0436\u0438\u043B\u0435\u0442\u044B \u0434\u043B\u044F \u0434\u0435\u0442\u0435\u0439</div>';
      html += '<div class="bento-card">';
      for (var lj = 0; lj < jackets.length; lj++) {
        var jk = jackets[lj];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(jk['\u0420\u0435\u0431\u0451\u043D\u043E\u043A'] || '') + '</span>';
        html += '<span class="bento-card__row-value">' + esc(jk['\u0420\u0430\u0437\u043C\u0435\u0440 \u0436\u0438\u043B\u0435\u0442\u0430'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>'; // End subtab-organization

    return html;
  }

  // -----------------------------------------------------------------------
  // equipment_checklist — Category cards with items
  // -----------------------------------------------------------------------

  function renderEquipmentChecklist(data) {
    var categories = data.categories || [];
    if (categories.length === 0) return '<div class="tpl-placeholder">\u0421\u043F\u0438\u0441\u043E\u043A \u043F\u0443\u0441\u0442</div>';

    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u0421\u043D\u0430\u0440\u044F\u0436\u0435\u043D\u0438\u0435</div>';
    html += '<div class="page-hero__title">Equipment</div>';
    html += '</div>';

    for (var c = 0; c < categories.length; c++) {
      var cat = categories[c];
      html += '<div class="tpl-section-title">' + esc(cat.name) + '</div>';
      html += '<div class="checklist-grid">';

      var subcats = cat.subcategories || [];
      for (var sc = 0; sc < subcats.length; sc++) {
        var sub = subcats[sc];
        var total = sub.items.length;
        var checked = sub.items.filter(function(it) { return it.checked; }).length;

        html += '<div class="checklist-card">';
        html += '<div class="checklist-card__header">';
        html += '<span class="checklist-card__title">' + esc(sub.name || 'Items') + '</span>';
        html += '<span class="checklist-card__count">' + checked + '/' + total + '</span>';
        html += '</div>';

        for (var it = 0; it < sub.items.length; it++) {
          var item = sub.items[it];
          var done = item.checked ? ' checklist-card__item--done' : '';
          html += '<div class="checklist-card__item' + done + '">';
          html += '<div class="checklist-card__item-check"></div>';
          html += '<span>' + esc(item.text) + '</span>';
          html += '</div>';
        }

        html += '</div>';
      }

      html += '</div>';
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // provisions — Shopping cards + meal plan
  // -----------------------------------------------------------------------

  function renderProvisions(data) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">\u041F\u0440\u043E\u0432\u0438\u0437\u0438\u044F</div>';
    html += '<div class="page-hero__title">Provisions</div>';
    html += '</div>';

    // Shopping lists
    var shopping = data.shopping || [];
    if (shopping.length > 0) {
      html += '<div class="provisions-grid">';
      for (var s = 0; s < shopping.length; s++) {
        var cat = shopping[s];
        html += '<div class="provisions-card">';
        html += '<div class="provisions-card__title">' + esc(cat.category) + '</div>';

        var items = cat.items || [];
        for (var i = 0; i < items.length; i++) {
          var item = items[i];
          var product = item['\u041F\u0440\u043E\u0434\u0443\u043A\u0442'] || '';
          var qty = item['\u041A\u043E\u043B-\u0432\u043E'] || item['\u041A\u043E\u043B\u044C\u0447\u0435\u0441\u0442\u0432\u043E'] || '';
          html += '<div class="provisions-card__item">';
          html += '<span class="provisions-card__product">' + esc(product) + '</span>';
          if (hasValue(qty)) {
            html += '<span class="provisions-card__qty">' + esc(qty) + '</span>';
          }
          html += '</div>';
        }

        html += '</div>';
      }
      html += '</div>';
    }

    // Meal plan
    var mealPlan = data.meal_plan || [];
    if (mealPlan.length > 0) {
      html += '<div class="tpl-section-title">\u041F\u043B\u0430\u043D \u043F\u0438\u0442\u0430\u043D\u0438\u044F</div>';
      html += '<div class="meal-plan-grid">';
      for (var mp = 0; mp < mealPlan.length; mp++) {
        var meal = mealPlan[mp];
        html += '<div class="meal-plan-row">';
        html += '<span class="meal-plan-row__day">' + esc(meal['\u0414\u0435\u043D\u044C'] || '') + '</span>';
        html += '<span class="meal-plan-row__meal">' + esc(meal['\u0417\u0430\u0432\u0442\u0440\u0430\u043A'] || '') + '</span>';
        html += '<span class="meal-plan-row__meal">' + esc(meal['\u041E\u0431\u0435\u0434'] || '') + '</span>';
        html += '<span class="meal-plan-row__meal">' + esc(meal['\u0423\u0436\u0438\u043D'] || '') + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Restock
    var restock = data.restock || [];
    if (restock.length > 0) {
      html += '<div class="tpl-section-title">\u0414\u043E\u043A\u0443\u043F\u043A\u0430 \u0432 \u043F\u0443\u0442\u0438</div>';
      html += '<div class="bento-card">';
      for (var rs = 0; rs < restock.length; rs++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(restock[rs]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // trip_overview — Facts card + status checklist + roster
  // -----------------------------------------------------------------------

  function renderTripOverview(data, page, section, tripData) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">Обзор поездки</div>';
    html += '<div class="page-hero__title">' + esc((tripData && tripData.boat) || 'Trip overview') + '</div>';
    html += '</div>';

    // Facts
    var facts = data.facts || {};
    var factKeys = Object.keys(facts);
    if (factKeys.length > 0) {
      html += '<div class="bento-grid">';
      html += '<div class="bento-card bento-card--wide">';
      html += '<div class="bento-card__label">На одном экране</div>';
      for (var fk = 0; fk < factKeys.length; fk++) {
        var key = factKeys[fk];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(key) + '</span>';
        html += '<span class="bento-card__row-value">' + esc(facts[key]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
      html += '</div>';
    }

    // Status checklist
    var status = data.status || [];
    if (status.length > 0) {
      var totalStatus = status.length;
      var doneStatus = status.filter(function (it) { return it.checked; }).length;

      html += '<div class="tpl-section-title">Статус подготовки</div>';
      html += '<div class="checklist-grid">';
      html += '<div class="checklist-card">';
      html += '<div class="checklist-card__header">';
      html += '<span class="checklist-card__title">Подготовка</span>';
      html += '<span class="checklist-card__count">' + doneStatus + '/' + totalStatus + '</span>';
      html += '</div>';
      for (var s = 0; s < status.length; s++) {
        var item = status[s];
        var done = item.checked ? ' checklist-card__item--done' : '';
        html += '<div class="checklist-card__item' + done + '">';
        html += '<div class="checklist-card__item-check"></div>';
        html += '<span>' + esc(item.text) + '</span>';
        html += '</div>';
      }
      html += '</div>';
      html += '</div>';
    }

    // Roster
    var roster = data.roster || [];
    var filledRoster = roster.filter(function (r) {
      return hasValue(r['Имя']);
    });
    if (roster.length > 0) {
      html += '<div class="tpl-section-title">Участники</div>';
      if (filledRoster.length === 0) {
        html += '<div class="tpl-placeholder">Состав будет добавлен</div>';
      } else {
        html += '<div class="crew-grid">';
        for (var r = 0; r < filledRoster.length; r++) {
          var member = filledRoster[r];
          var name = member['Имя'] || '';
          var phone = member['Телефон'] || '';
          var diet = member['Диета / Аллергии'] || '';
          var initials = name.charAt(0).toUpperCase();

          html += '<div class="crew-card">';
          html += '<div class="crew-card__avatar">' + esc(initials) + '</div>';
          html += '<div class="crew-card__info">';
          html += '<div class="crew-card__name">' + esc(name) + '</div>';
          if (hasValue(phone)) html += '<span class="crew-card__role">' + esc(phone) + '</span>';
          if (hasValue(diet)) html += '<div class="crew-card__detail">' + esc(diet) + '</div>';
          html += '</div></div>';
        }
        html += '</div>';
      }
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // boat_and_house_rules — Facts card + amenities + rule categories
  // -----------------------------------------------------------------------

  function renderBoatAndHouseRules(data, page, section, tripData) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">О лодке</div>';
    html += '<div class="page-hero__title">' + esc((tripData && tripData.boat) || 'Boat') + '</div>';
    html += '</div>';

    var facts = data.facts || {};
    var factKeys = Object.keys(facts);

    // Short summary — a handful of key facts, always visible
    var shortKeys = ['Каюты', 'Спальных мест', 'Гальюнов', 'Бак воды'];
    var shownShort = shortKeys.filter(function (k) { return facts[k]; });
    if (shownShort.length > 0) {
      html += '<div class="bento-grid">';
      html += '<div class="bento-card bento-card--wide">';
      html += '<div class="bento-card__label">Кратко</div>';
      for (var sk = 0; sk < shownShort.length; sk++) {
        var skey = shownShort[sk];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(skey) + '</span>';
        html += '<span class="bento-card__row-value">' + esc(facts[skey]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
      html += '</div>';
    }

    html += '<details class="tpl-details">';
    html += '<summary class="tpl-details__summary">Подробнее о лодке</summary>';

    // Full facts
    if (factKeys.length > 0) {
      html += '<div class="bento-grid">';
      html += '<div class="bento-card bento-card--wide">';
      html += '<div class="bento-card__label">Характеристики</div>';
      for (var fk = 0; fk < factKeys.length; fk++) {
        var key = factKeys[fk];
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(key) + '</span>';
        html += '<span class="bento-card__row-value">' + esc(facts[key]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
      html += '</div>';
    }

    // Amenities
    var amenities = data.amenities || [];
    if (amenities.length > 0) {
      html += '<div class="tpl-section-title">Оснащение</div>';
      html += '<div class="bento-card">';
      for (var a = 0; a < amenities.length; a++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(amenities[a]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    if (data.note) {
      html += '<div class="tpl-placeholder">' + esc(data.note) + '</div>';
    }

    // Rules by category
    var rules = data.rules || [];
    if (rules.length > 0) {
      html += '<div class="tpl-section-title">Правила пользования</div>';
      html += '<div class="checklist-grid">';
      for (var r = 0; r < rules.length; r++) {
        var cat = rules[r];
        html += '<div class="checklist-card">';
        html += '<div class="checklist-card__header">';
        html += '<span class="checklist-card__title">' + esc(cat.name) + '</span>';
        html += '</div>';
        for (var it = 0; it < cat.items.length; it++) {
          html += '<div class="checklist-card__item">';
          html += '<span>' + esc(cat.items[it]) + '</span>';
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</details>';

    return html;
  }

  // -----------------------------------------------------------------------
  // documents_and_money — Checklist categories + country facts + apps
  // -----------------------------------------------------------------------

  function renderDocumentsAndMoney(data, page, section, tripData) {
    var html = '';
    html += '<div class="page-hero">';
    html += '<div class="page-hero__label">План</div>';
    html += '<div class="page-hero__title">Документы и деньги</div>';
    html += '</div>';

    var checklists = data.checklists || [];
    if (checklists.length > 0) {
      html += '<div class="checklist-grid">';
      for (var c = 0; c < checklists.length; c++) {
        var cat = checklists[c];
        var total = cat.items.length;
        var checked = cat.items.filter(function (it) { return it.checked; }).length;

        html += '<div class="checklist-card">';
        html += '<div class="checklist-card__header">';
        html += '<span class="checklist-card__title">' + esc(cat.name) + '</span>';
        html += '<span class="checklist-card__count">' + checked + '/' + total + '</span>';
        html += '</div>';
        if (cat.note) {
          html += '<div class="tpl-placeholder">' + esc(cat.note) + '</div>';
        }
        for (var it = 0; it < cat.items.length; it++) {
          var item = cat.items[it];
          var done = item.checked ? ' checklist-card__item--done' : '';
          html += '<div class="checklist-card__item' + done + '">';
          html += '<div class="checklist-card__item-check"></div>';
          html += '<span>' + esc(item.text) + '</span>';
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }

    var facts = data.facts || [];
    if (facts.length > 0) {
      html += '<div class="tpl-section-title">Турция — что нужно знать</div>';
      html += '<div class="bento-card">';
      for (var f = 0; f < facts.length; f++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(facts[f].label) + '</span>';
        html += '<span class="bento-card__row-value">' + esc(facts[f].value) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    var apps = data.apps || [];
    if (apps.length > 0) {
      html += '<div class="tpl-section-title">Полезные приложения</div>';
      html += '<div class="bento-card">';
      for (var a = 0; a < apps.length; a++) {
        html += '<div class="bento-card__row">';
        html += '<span class="bento-card__row-label">' + esc(apps[a]) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    return html;
  }

  // -----------------------------------------------------------------------
  // Registry
  // -----------------------------------------------------------------------

  var RENDERERS = {
    route_plan: renderRoutePlan,
    travel_logistics: renderTravelLogistics,
    safety_briefing: renderSafetyBriefing,
    emergency_contacts: renderEmergencyContacts,
    kids_on_board: renderKidsOnBoard,
    crew_list: renderCrewList,
    equipment_checklist: renderEquipmentChecklist,
    provisions: renderProvisions,
    trip_overview: renderTripOverview,
    boat_and_house_rules: renderBoatAndHouseRules,
    documents_and_money: renderDocumentsAndMoney
  };

  return {
    canRender: canRender,
    render: render
  };
})();
