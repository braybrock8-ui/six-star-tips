// Six Star Map: interactive Leonida map.
// Regions you can click, pins with a synced list, search, category filters,
// found-tracking, shareable #m= / #r= links, and ?edit=1 for placing new pins.
(function () {
  "use strict";
  var cfgEl = document.getElementById("map-config");
  var root = document.getElementById("atlas");
  if (!cfgEl || !root || !window.L) return;

  var cfg = JSON.parse(cfgEl.textContent);
  var store = window.atlasStore || { get: function (k, d) { return d; }, set: function () {} };
  var W = cfg.width, H = cfg.height;
  var editMode = new URLSearchParams(location.search).has("edit");

  // ---------- helpers
  function $(sel) { return root.querySelector(sel); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function toLL(p) { return [H - p[1], p[0]]; }
  function toXY(ll) { return [Math.round(ll.lng), Math.round(H - ll.lat)]; }
  function mobile() { return window.matchMedia("(max-width: 760px)").matches; }

  // ---------- map
  var map = L.map("map", {
    crs: L.CRS.Simple, minZoom: -2.5, maxZoom: 1.5, zoomSnap: 0.25, zoomDelta: 0.5,
    zoomControl: false, attributionControl: false, wheelPxPerZoomLevel: 100
  });
  var bounds = [[0, 0], [H, W]];
  L.imageOverlay(cfg.image, bounds).addTo(map);
  // layer order: regions (overlay 400) < roads < buildings < pins (600) < names
  map.createPane("roads").style.zIndex = 410;
  map.createPane("bldg").style.zIndex = 420;
  map.createPane("names").style.zIndex = 640;
  map.getPane("names").style.pointerEvents = "none";

  // Atlas grid: 128px squares, A-P across, 1-16 down (matches the frame printed on the map)
  function gridRef(p) {
    var col = "ABCDEFGHIJKLMNOP".charAt(Math.max(0, Math.min(15, Math.floor(p[0] / 128))));
    return col + (Math.max(0, Math.min(15, Math.floor(p[1] / 128))) + 1);
  }

  // ---------- roads (from data, so they can be replaced with traced ones)
  var ROAD_STYLES = {
    highway: [{ color: "#7a6a45", weight: 7 }, { color: "#f6efdc", weight: 3.5 }],
    road: [{ color: "#8f8264", weight: 2.5 }],
    rail: [{ color: "#3b3833", weight: 2.5 }, { color: "#3b3833", weight: 8, dashArray: "1 9", lineCap: "butt" }],
    tunnel: [{ color: "#3b3833", weight: 2.5, dashArray: "5 5" }]
  };
  var roadLayers = [];
  (cfg.roads || []).forEach(function (rd) {
    var styles = ROAD_STYLES[rd.kind] || ROAD_STYLES.road;
    var traced = rd.status === "traced";
    styles.forEach(function (st) {
      var line = L.polyline(rd.points.map(toLL), Object.assign({
        pane: "roads", interactive: false, lineJoin: "round", lineCap: "round",
        opacity: traced ? 1 : 0.72
      }, st));
      line.baseWeight = st.weight * (traced ? 1.15 : 1);
      line.addTo(map);
      roadLayers.push(line);
    });
  });

  // ---------- town, district and feature names (shown as you zoom in)
  (cfg.labels || []).forEach(function (lb) {
    L.marker(toLL(lb.pos), {
      pane: "names", interactive: false, keyboard: false,
      icon: L.divIcon({ className: "name-label k-" + lb.kind + (lb.water ? " on-water" : ""), html: "<span>" + esc(lb.name) + "</span>", iconSize: null })
    }).addTo(map);
  });
  // generous pan limits so the floating panels never trap part of the land underneath them
  map.setMaxBounds(L.latLngBounds(bounds).pad(0.6));
  var landBounds = L.latLngBounds([toLL([90, 1960]), toLL([1680, 230])]);

  function pad() {
    if (mobile()) return { paddingTopLeft: [12, 60], paddingBottomRight: [12, 150] };
    var panel = $(".atlas-panel");
    var left = panel ? panel.offsetWidth + 32 : 40;
    return { paddingTopLeft: [left, 32], paddingBottomRight: [root.classList.contains("has-detail") ? 380 : 72, 32] };
  }
  function fitHome() { map.fitBounds(landBounds, pad()); }

  // ---------- state
  var found = store.get("atlas:found", {});
  var prefs = store.get("atlas:prefs", { off: [], hideFound: false });
  var query = "";
  var selected = null;
  var selectedRegion = null;
  var cats = {}, regions = {}, items = [], byId = {};

  cfg.categories.forEach(function (c) {
    c.on = (prefs.off || []).indexOf(c.id) === -1;
    c.items = [];
    cats[c.id] = c;
  });

  // ---------- regions
  var REST = { fillOpacity: 0.07, opacity: 0 }, HOT = { fillOpacity: 0.2, opacity: 0.95 };
  cfg.regions.forEach(function (r) {
    r.items = [];
    r.poly = L.polygon(r.polygon.map(toLL), {
      color: r.color, weight: 2.5, fillColor: r.color, fillOpacity: REST.fillOpacity, opacity: 0,
      className: "region-poly"
    }).addTo(map);
    r.poly.on("mouseover", function () { r.poly.setStyle(HOT); });
    r.poly.on("mouseout", function () { if (selectedRegion !== r.id) r.poly.setStyle(REST); });
    r.poly.on("click", function (e) { L.DomEvent.stop(e); if (!editMode) showRegion(r.id, true); else editClick(e); });
    r.label = L.marker(toLL(r.label), {
      icon: L.divIcon({
        className: "region-label",
        html: '<span><em>' + esc(r.name) + '</em><b class="cnt" style="--c:' + r.color + '"></b></span>',
        iconSize: null
      }),
      keyboard: false, zIndexOffset: -1000, title: "Show " + r.name
    }).addTo(map);
    r.label.on("click", function () { showRegion(r.id, true); });
    regions[r.id] = r;
  });

  // ---------- pins
  function pinIcon(it) {
    var cls = "pin" + (found[it.m.id] ? " is-found" : "") + (selected === it.m.id ? " is-selected" : "");
    return L.divIcon({
      className: cls,
      html: '<span class="p" style="--c:' + it.c.color + '"><i>' + esc(it.c.icon) + "</i></span>",
      iconSize: [30, 30], iconAnchor: [15, 36], tooltipAnchor: [0, -30]
    });
  }
  cfg.markers.forEach(function (m) {
    var c = cats[m.category];
    if (!c) { console.warn("Unknown category", m.id, m.category); return; }
    var it = { m: m, c: c, r: regions[m.region] };
    it.mk = L.marker(toLL(m.pos), { icon: pinIcon(it), title: m.title, riseOnHover: true });
    it.mk.bindTooltip(esc(m.title), { direction: "top", className: "pin-tip" });
    it.mk.on("click", function (e) { L.DomEvent.stop(e); select(m.id, false); });
    if (m.area) {
      it.area = L.circle(toLL(m.pos), {
        radius: m.area, color: c.color, weight: 2, dashArray: "6 7", fillColor: c.color, fillOpacity: 0.1, interactive: false
      });
    } else {
      // building footprint + name, shown only when zoomed right in
      var s = 15;
      it.bldg = L.rectangle([toLL([m.pos[0] - s, m.pos[1] + s]), toLL([m.pos[0] + s, m.pos[1] - s])], {
        pane: "bldg", color: c.color, weight: 2, fillColor: c.color, fillOpacity: 0.32, interactive: false
      });
    }
    it.name = L.marker(toLL(m.pos), {
      pane: "names", interactive: false, keyboard: false,
      icon: L.divIcon({ className: "name-label k-place", html: "<span>" + esc(m.title) + "</span>", iconSize: null })
    });
    m.grid = gridRef(m.pos);
    it.hay = [m.title, m.place, it.r && it.r.name, m.desc, c.label, m.chapter, m.grid].join(" ").toLowerCase();
    items.push(it);
    byId[m.id] = it;
    c.items.push(it);
    if (it.r) it.r.items.push(it);
  });

  function visible(it) {
    return it.c.on && !(prefs.hideFound && found[it.m.id] && selected !== it.m.id) &&
      (!query || it.hay.indexOf(query) !== -1);
  }
  function refreshIcon(id) { var it = byId[id]; if (it) it.mk.setIcon(pinIcon(it)); }

  // ---------- panel: chips
  var chipBox = $("#atlas-chips");
  cfg.categories.forEach(function (c) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "chip-cat";
    b.dataset.cat = c.id;
    b.title = "Click to toggle. Shift-click to show only " + c.label + ".";
    b.innerHTML = '<span class="dot" style="--c:' + c.color + '"></span>' + esc(c.label) +
      '<span class="n">' + c.items.length + "</span>";
    b.addEventListener("click", function (e) {
      if (e.shiftKey) cfg.categories.forEach(function (o) { o.on = o.id === c.id; });
      else c.on = !c.on;
      apply();
    });
    chipBox.appendChild(b);
  });

  // ---------- panel: list
  var list = $("#atlas-list");
  function renderList() {
    var html = "", shown = 0;
    cfg.regions.forEach(function (r) {
      var its = r.items.filter(visible);
      if (!its.length) return;
      html += '<section class="list-group"><button type="button" class="list-region" data-region="' + r.id + '">' +
        '<span class="swatch" style="--c:' + r.color + '"></span>' + esc(r.name) +
        '<span class="n">' + its.length + "</span></button><ul>";
      its.forEach(function (it) {
        shown++;
        var f = !!found[it.m.id];
        html += '<li><button type="button" class="list-item' + (f ? " is-found" : "") +
          (selected === it.m.id ? " is-selected" : "") + '" data-id="' + it.m.id + '">' +
          '<span class="dot" style="--c:' + it.c.color + '">' + esc(it.c.icon) + "</span>" +
          '<span class="t">' + esc(it.m.title) + "<small>" + esc(it.m.place || "") +
          (it.m.chapter ? " · " + esc(it.m.chapter) : "") + " · " + esc(it.m.grid) + "</small></span>" +
          (f ? '<span class="tick" title="Found">✓</span>' : "") + "</button></li>";
      });
      html += "</ul></section>";
    });
    list.innerHTML = shown ? html :
      '<p class="empty">No places match.<br><button type="button" class="linkish" data-reset>Clear search and filters</button></p>';
    $("#atlas-count").textContent = shown;
  }
  list.addEventListener("click", function (e) {
    var item = e.target.closest(".list-item");
    if (item) { select(item.dataset.id, true); if (mobile()) setSheet(false); return; }
    var reg = e.target.closest(".list-region");
    if (reg) { showRegion(reg.dataset.region, true); if (mobile()) setSheet(false); return; }
    if (e.target.closest("[data-reset]")) resetFilters();
  });
  list.addEventListener("mouseover", function (e) {
    var item = e.target.closest(".list-item");
    items.forEach(function (it) {
      var el = it.mk.getElement();
      if (el) el.classList.toggle("is-hover", !!item && item.dataset.id === it.m.id);
    });
  });
  list.addEventListener("mouseleave", function () {
    items.forEach(function (it) { var el = it.mk.getElement(); if (el) el.classList.remove("is-hover"); });
  });

  // ---------- progress
  function renderProgress() {
    var total = items.length, got = items.filter(function (it) { return found[it.m.id]; }).length;
    $("#atlas-progress").textContent = got + " / " + total + " found";
    $("#atlas-bar").style.width = (total ? 100 * got / total : 0) + "%";
  }

  // ---------- apply everything
  // Zoomed out, each region collapses to its label plus a count; zoom in (or pick a region) to see pins.
  // Three tiers: far (region badges), near (pins + town names), close (buildings + every name).
  var NEAR = -0.75, CLOSE = 0.25;
  function tier() { var z = map.getZoom(); return z >= CLOSE ? "close" : z >= NEAR ? "near" : "far"; }
  function near() { return tier() !== "far"; }
  function show(layer, on) { if (!layer) return; if (on) { if (!map.hasLayer(layer)) layer.addTo(map); } else map.removeLayer(layer); }
  function apply() {
    var t = tier(), isNear = t !== "far", isClose = t === "close";
    root.dataset.zoom = t;
    var scale = isClose ? 1.8 : isNear ? 1.3 : 1;
    roadLayers.forEach(function (l) { l.setStyle({ weight: l.baseWeight * scale }); });
    cfg.regions.forEach(function (r) {
      var n = r.items.filter(visible).length;
      var el = r.label.getElement();
      if (el) {
        var cnt = el.querySelector(".cnt");
        cnt.textContent = n;
        cnt.hidden = isNear || !n;
      }
    });
    items.forEach(function (it) {
      var vis = visible(it);
      var v = vis && (isNear || selected === it.m.id);
      show(it.mk, v);
      show(it.area, v);
      show(it.bldg, vis && isClose);
      show(it.name, vis && isClose);
    });
    setTimeout(declutter, 0);
    chipBox.querySelectorAll(".chip-cat").forEach(function (b) {
      b.setAttribute("aria-pressed", cats[b.dataset.cat].on ? "true" : "false");
    });
    renderList();
    renderProgress();
    prefs.off = cfg.categories.filter(function (c) { return !c.on; }).map(function (c) { return c.id; });
    store.set("atlas:prefs", prefs);
  }
  // Hide place names that would overlap one already shown. The selected place goes first,
  // then larger categories in data order. Pins stay visible and keep their hover names.
  function declutter() {
    if (root.dataset.zoom !== "close") return;
    var shown = items.filter(function (it) { return map.hasLayer(it.name) && it.name.getElement(); });
    shown.sort(function (a, b) { return (b.m.id === selected) - (a.m.id === selected); });
    var placed = [];
    shown.forEach(function (it) {
      var el = it.name.getElement();
      el.style.visibility = "visible";
      var r = el.firstChild.getBoundingClientRect();
      var hit = placed.some(function (p) {
        return !(r.right + 4 < p.left || r.left - 4 > p.right || r.bottom + 2 < p.top || r.top - 2 > p.bottom);
      });
      if (hit) el.style.visibility = "hidden"; else placed.push(r);
    });
  }
  map.on("zoomend", function () { setTimeout(declutter, 0); });

  function resetFilters() {
    cfg.categories.forEach(function (c) { c.on = true; });
    query = ""; search.value = "";
    prefs.hideFound = false; hideFound.checked = false;
    apply();
  }

  // ---------- detail card
  var detail = $("#atlas-detail");
  function openDetail(html) {
    detail.innerHTML = '<button type="button" class="detail-close" aria-label="Close" data-close>×</button>' + html;
    detail.hidden = false;
    root.classList.add("has-detail");
  }
  function closeDetail() {
    var prev = selected;
    selected = null;
    if (prev) refreshIcon(prev);
    if (selectedRegion) { regions[selectedRegion].poly.setStyle(REST); selectedRegion = null; }
    detail.hidden = true;
    root.classList.remove("has-detail");
    history.replaceState(null, "", location.pathname + location.search);
    renderList();
  }
  function placeDetail(it) {
    var m = it.m, f = !!found[m.id];
    var more = (it.r ? it.r.items : []).filter(function (o) { return o !== it; }).slice(0, 4);
    openDetail(
      '<p class="detail-cat" style="--c:' + it.c.color + '"><span class="dot"></span>' + esc(it.c.label) + "</p>" +
      "<h2>" + esc(m.title) + "</h2>" +
      '<p class="detail-meta">' + esc(m.place || "") + (it.r ? " · " + esc(it.r.name) : "") +
      (m.chapter ? ' · <span class="ch">' + esc(m.chapter) + "</span>" : "") +
      ' · <span class="grid-ref" title="Atlas grid square">Grid ' + esc(m.grid) + "</span></p>" +
      '<p class="detail-desc">' + esc(m.desc) + "</p>" +
      '<p class="detail-acc">' + (m.area ? "Somewhere in the dashed area." : "Approximate position: placed in " + esc(m.place || "the right area") + ".") +
      " The exact spot gets pinned once it's verified.</p>" +
      '<div class="detail-actions">' +
      '<button type="button" class="btn-sm' + (f ? " is-on" : "") + '" data-found="' + m.id + '" aria-pressed="' + f + '">' + (f ? "✓ Found" : "Mark found") + "</button>" +
      '<button type="button" class="btn-sm" data-copy="' + m.id + '">Copy link</button>' +
      (m.link ? '<a class="btn-sm btn-accent" href="' + esc(m.link) + '">' + esc(m.linkText || "Guide") + " →</a>" : "") +
      "</div>" +
      (more.length ? '<p class="detail-more-h">More in ' + esc(it.r.name) + '</p><div class="detail-more">' +
        more.map(function (o) {
          return '<button type="button" data-goto="' + o.m.id + '"><span class="dot" style="--c:' + o.c.color + '"></span>' + esc(o.m.title) + "</button>";
        }).join("") + "</div>" : "")
    );
  }
  function regionDetail(r) {
    openDetail(
      '<p class="detail-cat" style="--c:' + r.color + '"><span class="dot"></span>Region</p>' +
      "<h2>" + esc(r.name) + "</h2>" +
      '<p class="detail-desc">' + esc(r.desc) + "</p>" +
      (r.facts && r.facts.length ? '<ul class="detail-facts">' + r.facts.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ul>" : "") +
      '<p class="detail-more-h">' + r.items.length + " place" + (r.items.length === 1 ? "" : "s") + " here</p>" +
      '<div class="detail-more">' + r.items.map(function (o) {
        return '<button type="button" data-goto="' + o.m.id + '"><span class="dot" style="--c:' + o.c.color + '"></span>' + esc(o.m.title) + "</button>";
      }).join("") + "</div>" +
      '<div class="detail-actions"><a class="btn-sm btn-accent" href="' + esc(r.guide) + '">Region guide →</a>' +
      '<button type="button" class="btn-sm" data-copy-region="' + r.id + '">Copy link</button></div>'
    );
  }
  detail.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest("[data-close]")) return closeDetail();
    var fb = t.closest("[data-found]");
    if (fb) {
      var id = fb.dataset.found;
      if (found[id]) delete found[id]; else found[id] = 1;
      store.set("atlas:found", found);
      refreshIcon(id); apply(); placeDetail(byId[id]);
      return;
    }
    var cp = t.closest("[data-copy], [data-copy-region]");
    if (cp) {
      var url = location.origin + location.pathname + (cp.dataset.copy ? "#m=" + cp.dataset.copy : "#r=" + cp.dataset.copyRegion);
      var done = function () { cp.textContent = "Copied"; setTimeout(function () { cp.textContent = "Copy link"; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt("Copy this link", url); });
      else prompt("Copy this link", url);
      return;
    }
    var go = t.closest("[data-goto]");
    if (go) select(go.dataset.goto, true);
  });

  // Fly so the point lands in the middle of the part of the map the panels don't cover.
  function flyToVisible(latlng, zoom) {
    var box = root.getBoundingClientRect();
    var occ = { left: 0, right: 0, top: 0, bottom: 0 };
    [$(".atlas-panel"), detail].forEach(function (el) {
      if (!el || el.hidden) return;
      var r = el.getBoundingClientRect();
      if (mobile()) occ.bottom = Math.max(occ.bottom, box.bottom - r.top);
      else if (r.left - box.left < box.width / 2) occ.left = Math.max(occ.left, r.right - box.left);
      else occ.right = Math.max(occ.right, box.right - r.left);
    });
    var shift = L.point((occ.right - occ.left) / 2, (occ.bottom - occ.top) / 2);
    var center = map.unproject(map.project(latlng, zoom).add(shift), zoom);
    map.flyTo(center, zoom, { duration: 0.6 });
  }

  // ---------- selection
  function select(id, fly) {
    var it = byId[id];
    if (!it) return;
    if (!it.c.on) it.c.on = true;
    if (query && it.hay.indexOf(query) === -1) { query = ""; search.value = ""; }
    if (selectedRegion) { regions[selectedRegion].poly.setStyle(REST); selectedRegion = null; }
    var prev = selected;
    selected = id;
    apply();
    if (prev) refreshIcon(prev);
    refreshIcon(id);
    placeDetail(it);
    if (fly) flyToVisible(toLL(it.m.pos), Math.max(map.getZoom(), 0.75));
    history.replaceState(null, "", "#m=" + id);
    var row = list.querySelector('.list-item[data-id="' + id + '"]');
    if (row && !mobile()) row.scrollIntoView({ block: "nearest" });
  }
  function showRegion(id, fly) {
    var r = regions[id];
    if (!r) return;
    var prev = selected;
    selected = null;
    if (prev) refreshIcon(prev);
    if (selectedRegion && selectedRegion !== id) regions[selectedRegion].poly.setStyle(REST);
    selectedRegion = id;
    r.poly.setStyle(HOT);
    regionDetail(r);
    renderList();
    if (fly) map.flyToBounds(r.poly.getBounds(), Object.assign({ duration: 0.7, maxZoom: 0.5 }, pad()));
    history.replaceState(null, "", "#r=" + id);
  }

  // ---------- search
  var search = $("#atlas-search");
  search.addEventListener("input", function () { query = search.value.trim().toLowerCase(); apply(); });
  search.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      var first = list.querySelector(".list-item");
      if (first) { select(first.dataset.id, true); if (mobile()) setSheet(false); }
    }
    if (e.key === "Escape") { search.value = ""; query = ""; apply(); search.blur(); }
  });

  // ---------- hide found
  var hideFound = $("#atlas-hide-found");
  hideFound.checked = !!prefs.hideFound;
  hideFound.addEventListener("change", function () { prefs.hideFound = hideFound.checked; apply(); });

  // ---------- tools
  function setSheet(open) {
    root.classList.toggle("sheet-open", open);
    $("[data-sheet]").setAttribute("aria-expanded", open ? "true" : "false");
  }
  $("[data-sheet]").addEventListener("click", function () { setSheet(!root.classList.contains("sheet-open")); });
  search.addEventListener("focus", function () { if (mobile()) setSheet(true); });

  $("[data-zoom-in]").addEventListener("click", function () { map.zoomIn(); });
  $("[data-zoom-out]").addEventListener("click", function () { map.zoomOut(); });
  $("[data-home]").addEventListener("click", function () { closeDetail(); fitHome(); });
  $("[data-full]").addEventListener("click", function () {
    var native = root.requestFullscreen && !document.fullscreenElement;
    if (document.fullscreenElement) { document.exitFullscreen(); return; }
    if (native) { root.requestFullscreen().catch(function () { root.classList.toggle("is-full"); map.invalidateSize(); }); }
    else { root.classList.toggle("is-full"); setTimeout(function () { map.invalidateSize(); }, 50); }
  });
  document.addEventListener("fullscreenchange", function () { setTimeout(function () { map.invalidateSize(); }, 60); });

  map.on("click", function (e) { if (editMode) editClick(e); else if (selected || selectedRegion) closeDetail(); });
  var wasTier = null;
  map.on("zoomend", function () {
    var t = tier();
    if (t !== wasTier) { wasTier = t; apply(); }
  });

  document.addEventListener("keydown", function (e) {
    var typing = /input|textarea|select/i.test((e.target.tagName || ""));
    if (e.key === "/" && !typing) { e.preventDefault(); search.focus(); }
    else if (e.key === "Escape" && !typing && (selected || selectedRegion)) closeDetail();
  });

  // ---------- deep links
  function fromHash() {
    var m = location.hash.match(/^#m=([\w-]+)/), r = location.hash.match(/^#r=([\w-]+)/);
    if (m && byId[m[1]]) select(m[1], true);
    else if (r && regions[r[1]]) showRegion(r[1], true);
  }
  window.addEventListener("hashchange", fromHash);

  // ---------- edit mode: /map/?edit=1
  // "Place" mode: click once to get a new place. "Trace road" mode: click along a road you've
  // driven in-game, then Finish. Paste the JSON into data/markers.json or the "roads" list in data/map.json.
  var tempPin = null, trace = [], traceLine = null, traceDots = null;
  function editEl(id) { return document.getElementById(id); }
  function editMode_() { var r = document.querySelector('input[name="edit-mode"]:checked'); return r ? r.value : "pin"; }
  function copyOut(text) {
    editEl("edit-out").value = text;
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(function () {});
  }
  function roadJSON() {
    return JSON.stringify({
      id: "road-" + Date.now().toString(36), kind: editEl("edit-kind").value, status: "traced", points: trace
    }) + ",";
  }
  function redrawTrace() {
    var lls = trace.map(toLL);
    if (!traceLine) traceLine = L.polyline(lls, { color: "#ffcf5c", weight: 4, dashArray: "8 6" }).addTo(map);
    else traceLine.setLatLngs(lls);
    if (traceDots) map.removeLayer(traceDots);
    traceDots = L.layerGroup(lls.map(function (ll) { return L.circleMarker(ll, { radius: 4, color: "#ffcf5c", weight: 2 }); })).addTo(map);
    editEl("edit-count").textContent = trace.length + " point" + (trace.length === 1 ? "" : "s");
    if (trace.length > 1) copyOut(roadJSON());
  }
  function editClick(e) {
    var xy = toXY(e.latlng);
    if (editMode_() === "road") { trace.push(xy); redrawTrace(); return; }
    copyOut(JSON.stringify({
      id: "new-place", category: "landmark", title: "", region: "", place: "", pos: xy,
      chapter: null, desc: "", link: "", linkText: ""
    }, null, 2) + ",");
    if (tempPin) map.removeLayer(tempPin);
    tempPin = L.circleMarker(e.latlng, { radius: 9, color: "#ffcf5c", weight: 3 }).addTo(map);
  }
  if (editMode) {
    editEl("edit-box").hidden = false;
    editEl("edit-undo").addEventListener("click", function () { trace.pop(); redrawTrace(); });
    editEl("edit-finish").addEventListener("click", function () {
      if (trace.length < 2) return;
      copyOut(roadJSON());
      L.polyline(trace.map(toLL), { color: "#ffcf5c", weight: 3, pane: "roads" }).addTo(map); // keep it visible
      trace = []; redrawTrace();
      editEl("edit-count").textContent = "Copied. Paste it into the roads list in data/map.json.";
    });
    document.addEventListener("keydown", function (e) {
      if (editMode_() !== "road") return;
      if (e.key === "Enter") editEl("edit-finish").click();
      if (e.key === "Backspace" && !/input|textarea|select/i.test(e.target.tagName)) { e.preventDefault(); editEl("edit-undo").click(); }
    });
  }

  // ---------- go
  root.atlasMap = map; // handy for debugging in the console
  fitHome();
  wasTier = tier();
  apply();
  fromHash();
  window.addEventListener("resize", function () { map.invalidateSize(); });
})();
