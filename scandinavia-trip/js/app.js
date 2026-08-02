/* ============================================================
   SCANDINAVIA '27 — app engine
   Renders itinerary / calendar / map from window.TRIP, layered
   with any additions saved locally in this browser.
   ============================================================ */
(function () {
  "use strict";

  var TRIP = window.TRIP;
  var LS_KEY = "scandi27.local.v1";

  /* Drafting-key legend: each type gets a two-letter mono key, printed in ink. */
  var TYPES = {
    flight:  { key: "FL", label: "Flight" },
    transit: { key: "TR", label: "Transit" },
    lodging: { key: "LO", label: "Lodging" },
    food:    { key: "FD", label: "Food & drink" },
    sight:   { key: "SG", label: "Sight" },
    museum:  { key: "MU", label: "Museum" },
    nature:  { key: "NA", label: "Nature" },
    other:   { key: "NB", label: "Plan" },
  };

  /* ---------------- utils ---------------- */

  function $(sel) { return document.querySelector(sel); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function parseISO(iso) {
    var p = iso.split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  function fmtLong(iso) {
    return parseISO(iso).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  }

  function fmtShort(iso) {
    return parseISO(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  }

  function toast(msg) {
    var t = document.querySelector(".toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    requestAnimationFrame(function () { t.classList.add("show"); });
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.remove("show"); }, 2600);
  }

  /* ---------------- local additions ---------------- */

  function readLocal() {
    try {
      return JSON.parse(localStorage.getItem(LS_KEY)) || { events: [] };
    } catch (e) {
      return { events: [] };
    }
  }

  function writeLocal(data) {
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  }

  /* Merged view: repo days + browser-local events, sorted by time. */
  function mergedDays() {
    var local = readLocal();
    return TRIP.days.map(function (day) {
      var events = (day.events || []).map(function (ev) { return Object.assign({}, ev); });
      local.events.forEach(function (ev, idx) {
        if (ev.date === day.date) {
          events.push(Object.assign({}, ev, { _local: true, _localIdx: idx }));
        }
      });
      events.sort(function (a, b) { return (a.time || "99:99") < (b.time || "99:99") ? -1 : 1; });
      return { date: day.date, label: day.label, events: events };
    });
  }

  /* ---------------- stats ---------------- */

  function renderStats() {
    var days = mergedDays();
    var evCount = 0, placeCount = 0;
    days.forEach(function (d) {
      evCount += d.events.length;
      d.events.forEach(function (e) {
        if (e.location && isFinite(e.location.lat)) placeCount++;
      });
    });
    (TRIP.bases || []).forEach(function (b) { if (isFinite(b.lat)) placeCount++; });
    $("#stats").innerHTML =
      '<div class="stat reveal"><b>' + days.length + "</b><span>days</span></div>" +
      '<div class="stat reveal"><b>' + (TRIP.bases || []).length + "</b><span>bases</span></div>" +
      '<div class="stat reveal"><b>' + evCount + "</b><span>plans</span></div>" +
      '<div class="stat reveal"><b>' + placeCount + "</b><span>pinned places</span></div>";
  }

  /* ---------------- itinerary ---------------- */

  var EMPTY_LINES = [
    "Nothing planned yet — the fjords can wait.",
    "A blank page. Snow, probably.",
    "Wide open. Aurora hours available.",
    "Unwritten. Suggest something.",
    "Free day — for now.",
  ];

  function eventHTML(ev) {
    var type = TYPES[ev.type] || TYPES.other;
    var html = '<li class="event">';
    html += '<div class="event-time">' + (ev.time ? esc(ev.time) : "—") + "</div>";
    html += '<span class="key-chip" title="' + esc(type.label) + '">' + type.key + "</span>";
    html += "<div>";
    html += '<div class="event-title">' + esc(ev.title);
    if (ev._local) html += '<span class="badge badge-local">local</span>';
    if (ev._local) html += '<button class="event-x" data-local-idx="' + ev._localIdx + '" title="Remove this local plan">remove</button>';
    html += "</div>";
    if (ev.location && ev.location.name) {
      html += '<div class="event-place">LOC · ' + esc(ev.location.name);
      if (ev.link) html += ' · <a href="' + esc(ev.link) + '" target="_blank" rel="noopener">link ↗</a>';
      html += "</div>";
    } else if (ev.link) {
      html += '<div class="event-place"><a href="' + esc(ev.link) + '" target="_blank" rel="noopener">link ↗</a></div>';
    }
    if (ev.notes) html += '<div class="event-notes">' + esc(ev.notes) + "</div>";
    html += "</div></li>";
    return html;
  }

  function renderTimeline() {
    var days = mergedDays();
    var html = "";
    days.forEach(function (day, i) {
      html += '<li class="day reveal" id="day-' + day.date + '">';
      html += '<div class="day-card">';
      html += '<div class="day-head">';
      html += '<span class="day-num">Day ' + (i + 1) + "</span>";
      html += '<span class="day-date">' + fmtLong(day.date) + "</span>";
      if (day.label) html += '<span class="day-label">' + esc(day.label) + "</span>";
      html += "</div>";
      if (!day.events.length) {
        html += '<div class="day-empty">' + EMPTY_LINES[i % EMPTY_LINES.length] + "</div>";
      } else {
        html += '<ol class="events">' + day.events.map(eventHTML).join("") + "</ol>";
      }
      html += "</div></li>";
    });
    $("#timeline").innerHTML = html;

    document.querySelectorAll(".event-x").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var local = readLocal();
        local.events.splice(+btn.dataset.localIdx, 1);
        writeLocal(local);
        renderAll();
        toast("Removed local plan");
      });
    });
  }

  function renderIdeas() {
    var ideas = TRIP.ideas || [];
    var box = $("#ideas");
    if (!ideas.length) {
      box.innerHTML = '<div class="ideas-empty">Empty shelf. Drop ideas into <code>data/trip-data.js → ideas</code> — or ask Claude to research some.</div>';
      return;
    }
    box.innerHTML = ideas.map(function (idea) {
      var text = typeof idea === "string" ? idea : (idea.title || "");
      return '<div class="idea-card reveal">' + esc(text) + "</div>";
    }).join("");
  }

  /* ---------------- calendar ---------------- */

  var selectedDate = null;

  function monthsInRange(startISO, endISO) {
    var start = parseISO(startISO), end = parseISO(endISO);
    var months = [];
    var cur = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cur <= end) {
      months.push(new Date(cur));
      cur.setMonth(cur.getMonth() + 1);
    }
    return months;
  }

  function isoOf(d) {
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }

  function renderCalendar() {
    var days = mergedDays();
    var byDate = {};
    days.forEach(function (d) { byDate[d.date] = d; });

    var dows = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    var html = "";
    monthsInRange(TRIP.meta.startDate, TRIP.meta.endDate).forEach(function (month) {
      var title = month.toLocaleDateString("en-US", { month: "long", year: "numeric" });
      html += '<div class="cal reveal"><div class="cal-title">' + title + '</div><div class="cal-grid">';
      html += dows.map(function (d) { return '<div class="cal-dow">' + d + "</div>"; }).join("");

      var first = new Date(month.getFullYear(), month.getMonth(), 1);
      var lead = (first.getDay() + 6) % 7; // Monday-first
      for (var i = 0; i < lead; i++) html += "<div></div>";

      var last = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
      for (var dNum = 1; dNum <= last; dNum++) {
        var iso = isoOf(new Date(month.getFullYear(), month.getMonth(), dNum));
        var day = byDate[iso];
        if (day) {
          var dots = Math.min(day.events.length, 4);
          var dotHTML = "";
          for (var k = 0; k < dots; k++) dotHTML += "<i></i>";
          html += '<button class="cal-cell trip' + (iso === selectedDate ? " selected" : "") + '" data-date="' + iso + '">' +
                  dNum + '<span class="cal-dots">' + dotHTML + "</span></button>";
        } else {
          html += '<div class="cal-cell">' + dNum + "</div>";
        }
      }
      html += "</div></div>";
    });
    $("#calendars").innerHTML = html;

    document.querySelectorAll(".cal-cell.trip").forEach(function (cellBtn) {
      cellBtn.addEventListener("click", function () {
        selectedDate = cellBtn.dataset.date;
        document.querySelectorAll(".cal-cell.selected").forEach(function (c) { c.classList.remove("selected"); });
        cellBtn.classList.add("selected");
        renderCalDetail();
      });
    });
    renderCalDetail();
    revealScan();
  }

  function renderCalDetail() {
    var box = $("#cal-detail");
    if (!selectedDate) { box.hidden = true; return; }
    var day = mergedDays().filter(function (d) { return d.date === selectedDate; })[0];
    if (!day) { box.hidden = true; return; }

    var idx = TRIP.days.findIndex(function (d) { return d.date === selectedDate; });
    var html = '<div class="day-head"><span class="day-num">Day ' + (idx + 1) + "</span>" +
               '<span class="day-date">' + fmtLong(day.date) + "</span>";
    if (day.label) html += '<span class="day-label">' + esc(day.label) + "</span>";
    html += "</div>";
    if (!day.events.length) {
      html += '<div class="day-empty">Nothing here yet. Hit ＋ Add, or ask Claude to plan this day.</div>';
    } else {
      html += '<ol class="events">' + day.events.map(eventHTML).join("") + "</ol>";
    }
    box.innerHTML = html;
    box.hidden = false;

    box.querySelectorAll(".event-x").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var local = readLocal();
        local.events.splice(+btn.dataset.localIdx, 1);
        writeLocal(local);
        renderAll();
        toast("Removed local plan");
      });
    });
  }

  /* ---------------- map ---------------- */

  var map = null;
  var mapLayer = null;

  function pinIcon(key, isBase) {
    var size = isBase ? 28 : 24;
    return L.divIcon({
      className: "pin" + (isBase ? " pin-base" : ""),
      html: '<div style="position:relative"><div class="pin-pulse"></div><div class="pin-key">' + key + "</div></div>",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      popupAnchor: [0, -size / 2 - 4],
    });
  }

  function initMap() {
    if (map) return;
    map = L.map("map", { zoomControl: true, scrollWheelZoom: true, attributionControl: true });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);
    mapLayer = L.layerGroup().addTo(map);
    renderMap();
  }

  function renderMap() {
    if (!map) return;
    mapLayer.clearLayers();

    var points = [];

    (TRIP.bases || []).forEach(function (base) {
      if (!isFinite(base.lat) || !isFinite(base.lng)) return;
      var m = L.marker([base.lat, base.lng], { icon: pinIcon("BA", true), zIndexOffset: 500 });
      var sub = [base.country, base.arrive && base.depart ? fmtShort(base.arrive) + " → " + fmtShort(base.depart) : ""]
        .filter(Boolean).join(" · ");
      m.bindPopup('<div class="popup-title">BASE — ' + esc(base.name) + '</div><div class="popup-sub">' + esc(sub) + "</div>" +
                  (base.lodging ? '<div class="popup-sub">' + esc(base.lodging) + "</div>" : ""));
      m.addTo(mapLayer);
      points.push([base.lat, base.lng]);
    });

    var basePts = points.slice();
    if (basePts.length > 1) {
      L.polyline(basePts, {
        color: "#1c1914", weight: 2, opacity: 0.85, className: "route-line",
      }).addTo(mapLayer);
    }

    mergedDays().forEach(function (day, i) {
      day.events.forEach(function (ev) {
        var loc = ev.location;
        if (!loc || !isFinite(loc.lat) || !isFinite(loc.lng)) return;
        var type = TYPES[ev.type] || TYPES.other;
        var m = L.marker([loc.lat, loc.lng], { icon: pinIcon(type.key) });
        m.bindPopup('<div class="popup-title">' + esc(ev.title) + '</div>' +
                    '<div class="popup-sub">Day ' + (i + 1) + " · " + fmtShort(day.date) +
                    (ev.time ? " · " + esc(ev.time) : "") + "</div>" +
                    (loc.name ? '<div class="popup-sub">LOC · ' + esc(loc.name) + "</div>" : ""));
        m.addTo(mapLayer);
        points.push([loc.lat, loc.lng]);
      });
    });

    var empty = $("#map-empty");
    if (points.length === 0) {
      map.setView([62.5, 14.5], 4); // Scandinavia at rest
      empty.hidden = false;
    } else {
      empty.hidden = true;
      /* Fit to the European leg — a Chicago departure pin would zoom the
         whole Atlantic into frame and crush the useful detail. */
      var fitPts = points.filter(function (p) { return p[1] > -20; });
      if (!fitPts.length) fitPts = points;
      if (fitPts.length === 1) map.setView(fitPts[0], 11);
      else map.fitBounds(fitPts, { padding: [46, 46] });
    }

    $("#map-legend").innerHTML =
      '<span class="leg"><span class="key-chip">BA</span>Base</span>' +
      Object.keys(TYPES).map(function (t) {
        return '<span class="leg"><span class="key-chip">' + TYPES[t].key + "</span>" + TYPES[t].label + "</span>";
      }).join("");
  }

  /* ---------------- tabs ---------------- */

  function moveGlider() {
    var active = document.querySelector(".tab.active");
    var glider = document.querySelector(".tab-glider");
    if (!active || !glider) return;
    glider.style.left = active.offsetLeft + "px";
    glider.style.width = active.offsetWidth + "px";
  }

  function switchView(name) {
    document.querySelectorAll(".tab").forEach(function (t) {
      var on = t.dataset.view === name;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".view").forEach(function (v) {
      var on = v.id === "view-" + name;
      v.classList.toggle("active", on);
      v.hidden = !on;
    });
    moveGlider();
    if (name === "map") {
      initMap();
      setTimeout(function () { map.invalidateSize(); renderMap(); }, 60);
    }
    $("#main").scrollIntoView({ behavior: "smooth", block: "start" });
    revealScan();
  }

  /* ---------------- countdown ---------------- */

  function tickCountdown() {
    var start = parseISO(TRIP.meta.startDate);
    var end = parseISO(TRIP.meta.endDate);
    end.setDate(end.getDate() + 1);
    var now = new Date();
    var box = $("#countdown");
    if (now >= start && now < end) {
      box.innerHTML = '<div class="count-cell"><span class="count-num">✈</span><span class="count-label">we\'re here — skål!</span></div>';
      return;
    }
    if (now >= end) {
      box.innerHTML = '<div class="count-cell"><span class="count-num">❄</span><span class="count-label">until next time</span></div>';
      return;
    }
    var ms = start - now;
    var d = Math.floor(ms / 86400000);
    var h = Math.floor(ms / 3600000) % 24;
    var m = Math.floor(ms / 60000) % 60;
    var s = Math.floor(ms / 1000) % 60;
    $("#cd-days").textContent = d;
    $("#cd-hours").textContent = String(h).padStart(2, "0");
    $("#cd-mins").textContent = String(m).padStart(2, "0");
    $("#cd-secs").textContent = String(s).padStart(2, "0");
  }

  /* ---------------- hero letters ---------------- */

  function splitHero() {
    var el = $("#hero-title");
    var text = el.textContent;
    el.innerHTML = text.split("").map(function (ch, i) {
      return '<span class="ch" style="animation-delay:' + (120 + i * 45) + 'ms">' + ch + "</span>";
    }).join("");
  }

  /* ---------------- reveal on scroll ---------------- */

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });

  function revealScan() {
    document.querySelectorAll(".reveal:not(.in)").forEach(function (el) { observer.observe(el); });
  }

  /* ---------------- add modal ---------------- */

  function openModal() {
    var sel = $("#f-date");
    sel.innerHTML = TRIP.days.map(function (d, i) {
      return '<option value="' + d.date + '">Day ' + (i + 1) + " — " + fmtShort(d.date) + "</option>";
    }).join("");
    if (selectedDate) sel.value = selectedDate;
    $("#modal-backdrop").hidden = false;
    $("#f-title").focus();
  }

  function closeModal() {
    $("#modal-backdrop").hidden = true;
    $("#add-form").reset();
  }

  function submitAdd(e) {
    e.preventDefault();
    var ev = {
      date: $("#f-date").value,
      time: $("#f-time").value || "",
      title: $("#f-title").value.trim(),
      type: $("#f-type").value,
    };
    if (!ev.title) return;
    var place = $("#f-place").value.trim();
    var lat = parseFloat($("#f-lat").value);
    var lng = parseFloat($("#f-lng").value);
    if (place || (isFinite(lat) && isFinite(lng))) {
      ev.location = { name: place };
      if (isFinite(lat) && isFinite(lng)) { ev.location.lat = lat; ev.location.lng = lng; }
    }
    var notes = $("#f-notes").value.trim();
    if (notes) ev.notes = notes;

    var local = readLocal();
    local.events.push(ev);
    writeLocal(local);
    closeModal();
    renderAll();
    toast("Added — saved in this browser");
  }

  /* ---------------- sync drawer ---------------- */

  var SYNC_HEADER =
    "/* SCANDINAVIA · SPRING BREAK 2027 — TRIP DATA\n" +
    "   Generated by the site's Sync panel (repo data + local additions).\n" +
    "   Replace the contents of data/trip-data.js with this file, commit,\n" +
    "   then use \"Clear local additions\" in the site so nothing doubles up.\n" +
    "   Schema reference lives in the repo history / README. */\n\n";

  function buildSyncText() {
    var local = readLocal();
    var merged = {
      meta: TRIP.meta,
      bases: TRIP.bases || [],
      days: TRIP.days.map(function (day) {
        var events = (day.events || []).slice();
        local.events.forEach(function (ev) {
          if (ev.date === day.date) {
            var copy = Object.assign({}, ev);
            delete copy.date;
            events.push(copy);
          }
        });
        events.sort(function (a, b) { return (a.time || "99:99") < (b.time || "99:99") ? -1 : 1; });
        return { date: day.date, label: day.label || "", events: events };
      }),
      ideas: TRIP.ideas || [],
    };
    return SYNC_HEADER + "window.TRIP = " + JSON.stringify(merged, null, 2) + ";\n";
  }

  function openSync() {
    $("#sync-out").value = buildSyncText();
    $("#sync-backdrop").hidden = false;
  }

  /* ---------------- boot ---------------- */

  function renderAll() {
    renderStats();
    renderTimeline();
    renderIdeas();
    renderCalendar();
    renderMap();
    revealScan();
  }

  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () { switchView(tab.dataset.view); });
  });

  $("#btn-add").addEventListener("click", openModal);
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal-cancel").addEventListener("click", closeModal);
  $("#modal-backdrop").addEventListener("click", function (e) { if (e.target.id === "modal-backdrop") closeModal(); });
  $("#add-form").addEventListener("submit", submitAdd);

  $("#btn-sync").addEventListener("click", openSync);
  $("#sync-close").addEventListener("click", function () { $("#sync-backdrop").hidden = true; });
  $("#sync-backdrop").addEventListener("click", function (e) { if (e.target.id === "sync-backdrop") $("#sync-backdrop").hidden = true; });
  $("#btn-copy-sync").addEventListener("click", function () {
    navigator.clipboard.writeText($("#sync-out").value).then(function () {
      toast("Copied — paste into data/trip-data.js");
    }, function () {
      $("#sync-out").select();
      document.execCommand("copy");
      toast("Copied");
    });
  });
  $("#btn-clear-local").addEventListener("click", function () {
    if (!readLocal().events.length) { toast("Nothing local to clear"); return; }
    if (confirm("Remove all plans saved in this browser? (Anything already committed to the data file stays.)")) {
      localStorage.removeItem(LS_KEY);
      renderAll();
      toast("Local additions cleared");
    }
  });

  $("#btn-export").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    window.exportTripDocx({ meta: TRIP.meta, ideas: TRIP.ideas }, mergedDays()).then(function () {
      toast("Word document downloaded");
      btn.disabled = false;
    }, function (err) {
      console.error(err);
      toast("Export failed — see console");
      btn.disabled = false;
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      $("#modal-backdrop").hidden = true;
      $("#sync-backdrop").hidden = true;
    }
  });

  window.addEventListener("resize", moveGlider);

  splitHero();
  tickCountdown();
  setInterval(tickCountdown, 1000);
  renderAll();
  moveGlider();
})();
