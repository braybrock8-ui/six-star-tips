// Interactive map: category filters, found tracking, shareable #m=id links,
// and ?edit=1 mode for dropping new markers fast on launch day.
(function () {
  "use strict";
  var cfgEl = document.getElementById("map-config");
  if (!cfgEl || !window.L) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var store = window.atlasStore;
  var W = cfg.width, H = cfg.height;
  var editMode = new URLSearchParams(location.search).has("edit");

  var map = L.map("map", {
    crs: L.CRS.Simple, minZoom: -2.5, maxZoom: 2, zoomSnap: 0.25, zoomDelta: 0.5, attributionControl: false
  });
  var bounds = [[0, 0], [H, W]];
  L.imageOverlay(cfg.image, bounds).addTo(map);
  map.fitBounds(bounds);
  map.setMaxBounds(L.latLngBounds(bounds).pad(0.3));

  // Marker positions are [x, y] in map-image pixels, measured from the top-left.
  var toLatLng = function (p) { return [H - p[1], p[0]]; };
  var toXY = function (ll) { return [Math.round(ll.lng), Math.round(H - ll.lat)]; };

  var found = store.get("atlas:found", {});
  var state = store.get("atlas:filters", {});
  var hideFound = document.getElementById("hide-found");
  var search = document.getElementById("map-search");
  var statusEl = document.getElementById("map-status");
  if (cfg.placeholder) statusEl.textContent = cfg.placeholder;
  hideFound.checked = !!state.hideFound;

  var cats = {};
  cfg.categories.forEach(function (c) {
    cats[c.id] = c;
    c.on = state.off ? state.off.indexOf(c.id) === -1 : true;
    c.layer = L.layerGroup().addTo(map);
    c.items = [];
  });
  var byId = {};

  function icon(cat, isFound) {
    return L.divIcon({
      className: "pin" + (isFound ? " pin-found" : ""),
      html: '<span style="--c:' + cat.color + '">' + cat.icon + "</span>",
      iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -14]
    });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function popup(item) {
    var m = item.m, cat = item.cat;
    var box = el("div", "popup");
    box.appendChild(el("h3", null, m.title));
    box.appendChild(el("p", "cat", cat.label + (m.region ? " · " + m.region : "")));
    if (m.desc) box.appendChild(el("p", null, m.desc));
    if (!m.verified) box.appendChild(el("p", "small muted", "Unconfirmed in the released game."));
    if (m.credit) box.appendChild(el("p", "small muted", "Found by " + m.credit));
    var actions = el("div", "actions");
    if (cat.style !== "label") {
      var fb = el("button", null, found[m.id] ? "Mark not found" : "Mark found");
      fb.type = "button";
      fb.onclick = function () {
        if (found[m.id]) delete found[m.id]; else found[m.id] = 1;
        store.set("atlas:found", found);
        fb.textContent = found[m.id] ? "Mark not found" : "Mark found";
        item.mk.setIcon(icon(cat, !!found[m.id]));
        apply();
      };
      actions.appendChild(fb);
    }
    var cb = el("button", null, "Copy link");
    cb.type = "button";
    cb.onclick = function () {
      var url = location.origin + "/map/#m=" + m.id;
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { cb.textContent = "Copied"; });
      else prompt("Copy this link", url);
    };
    actions.appendChild(cb);
    box.appendChild(actions);
    return box;
  }

  function add(m) {
    var cat = cats[m.category];
    if (!cat) { console.warn("Unknown category for marker", m.id, m.category); return; }
    var mk;
    if (cat.style === "label") {
      var span = document.createElement("span"); span.textContent = m.title;
      mk = L.marker(toLatLng(m.pos), {
        icon: L.divIcon({ className: "pin-label", html: span.outerHTML, iconSize: null }),
        title: m.title, zIndexOffset: -1000
      });
    } else {
      mk = L.marker(toLatLng(m.pos), { icon: icon(cat, !!found[m.id]), title: m.title, riseOnHover: true });
    }
    var item = { m: m, cat: cat, mk: mk, hay: (m.title + " " + (m.region || "") + " " + (m.desc || "")).toLowerCase() };
    mk.bindPopup(function () { return popup(item); });
    mk.on("popupopen", function () { history.replaceState(null, "", "#m=" + m.id); });
    cat.items.push(item);
    byId[m.id] = item;
  }

  function apply() {
    var q = search.value.trim().toLowerCase();
    var total = 0, got = 0;
    cfg.categories.forEach(function (c) {
      c.items.forEach(function (it) {
        if (c.style !== "label") { total++; if (found[it.m.id]) got++; }
        var show = c.on && (!q || it.hay.indexOf(q) !== -1) && !(hideFound.checked && found[it.m.id]);
        if (show && !c.layer.hasLayer(it.mk)) c.layer.addLayer(it.mk);
        if (!show && c.layer.hasLayer(it.mk)) c.layer.removeLayer(it.mk);
      });
    });
    document.getElementById("found-count").textContent = total ? "You've found " + got + " of " + total + " locations." : "";
    store.set("atlas:filters", {
      hideFound: hideFound.checked,
      off: cfg.categories.filter(function (c) { return !c.on; }).map(function (c) { return c.id; })
    });
  }

  function buildFilters() {
    var box = document.getElementById("filters");
    cfg.categories.forEach(function (c) {
      var label = el("label");
      var cb = el("input"); cb.type = "checkbox"; cb.checked = c.on;
      cb.onchange = function () { c.on = cb.checked; apply(); };
      var dot = el("span", "dot", c.style === "label" ? "A" : c.icon);
      dot.style.setProperty("--c", c.color);
      label.appendChild(cb); label.appendChild(dot); label.appendChild(el("span", null, c.label));
      label.appendChild(el("span", "count", String(c.items.length)));
      box.appendChild(label);
    });
  }

  function openFromHash() {
    var m = location.hash.match(/m=([\w-]+)/);
    var item = m && byId[m[1]];
    if (!item) return;
    if (!item.cat.on) { item.cat.on = true; document.getElementById("filters").innerHTML = ""; buildFilters(); }
    search.value = "";
    apply();
    map.setView(toLatLng(item.m.pos), Math.max(map.getZoom(), 0.5));
    item.mk.openPopup();
  }

  fetch("/data/markers.json").then(function (r) { return r.json(); }).then(function (data) {
    data.markers.forEach(add);
    buildFilters();
    apply();
    openFromHash();
  }).catch(function (e) {
    statusEl.textContent = "Couldn't load map markers.";
    console.error(e);
  });

  search.addEventListener("input", apply);
  hideFound.addEventListener("change", apply);
  window.addEventListener("hashchange", openFromHash);

  // ---- edit mode: /map/?edit=1
  if (editMode) {
    var boxEl = document.getElementById("edit-box"), out = document.getElementById("edit-out");
    boxEl.hidden = false;
    var temp = null;
    map.on("click", function (e) {
      var xy = toXY(e.latlng);
      var snippet = JSON.stringify({
        id: "new-marker", category: "collectible", title: "", region: "", pos: xy, desc: "", verified: true, credit: ""
      }, null, 2);
      out.value = snippet + ",";
      if (navigator.clipboard) navigator.clipboard.writeText(out.value).catch(function () {});
      if (temp) map.removeLayer(temp);
      temp = L.circleMarker(e.latlng, { radius: 8, color: "#ffcf5c" }).addTo(map);
    });
  }
})();
