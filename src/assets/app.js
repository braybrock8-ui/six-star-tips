// Site-wide behaviour: saved checkboxes, launch countdown, relative times, search.
(function () {
  "use strict";

  // ---- storage that never throws (private windows, blocked storage)
  var store = {
    get: function (key, fallback) {
      try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
    }
  };
  window.atlasStore = store;

  // ---- checkboxes with progress
  var checks = store.get("atlas:checks", {});
  document.querySelectorAll("[data-check-scope]").forEach(function (scope) {
    var boxes = scope.querySelectorAll("input[data-check]");
    var progress = scope.querySelector(".progress");
    function update() {
      if (!progress || !boxes.length) return;
      var done = 0;
      boxes.forEach(function (b) { if (b.checked) done++; });
      progress.hidden = false;
      var big = progress.querySelector(".big");
      if (big) big.textContent = Math.round(100 * done / boxes.length) + "%";
      progress.querySelector(".bar span").style.width = (100 * done / boxes.length) + "%";
      progress.querySelector("small").textContent = done + " of " + boxes.length + " done";
    }
    boxes.forEach(function (box) {
      box.checked = !!checks[box.dataset.check];
      box.addEventListener("change", function () {
        if (box.checked) checks[box.dataset.check] = 1; else delete checks[box.dataset.check];
        store.set("atlas:checks", checks);
        update();
      });
    });
    update();
  });

  // ---- today's date in the utility bar
  var today = document.querySelector("[data-today]");
  if (today) {
    today.textContent = new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  }

  // ---- countdowns: big one on the home page, compact one in the utility bar
  var pad = function (n) { return n < 10 ? "0" + n : String(n); };
  var counters = document.querySelectorAll("[data-launch]");
  var tick = function () {
    counters.forEach(function (cd) {
      var launch = new Date(cd.dataset.launch).getTime();
      if (isNaN(launch)) return;
      var ms = launch - Date.now();
      var mini = cd.classList.contains("countdown-mini");
      if (ms <= 0) {
        cd.innerHTML = mini
          ? '<span class="live-dot"></span>Live coverage'
          : '<span class="live"><span class="live-dot"></span>Out now · updating live</span>';
        return;
      }
      var d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5) % 24,
          m = Math.floor(ms / 6e4) % 60, s = Math.floor(ms / 1e3) % 60;
      if (mini) {
        cd.innerHTML = "Launch in <b>" + d + "d " + pad(h) + "h " + pad(m) + "m</b>";
        return;
      }
      cd.innerHTML = [[d, "Days"], [pad(h), "Hours"], [pad(m), "Min"], [pad(s), "Sec"]].map(function (p) {
        return '<div class="unit"><b>' + p[0] + "</b><small>" + p[1] + "</small></div>";
      }).join("");
    });
  };
  if (counters.length) { tick(); setInterval(tick, 1000); }

  // ---- "5 min ago" times
  function rel(iso) {
    var d = new Date(iso), s = (Date.now() - d.getTime()) / 1000;
    if (isNaN(s)) return iso;
    if (s < 0) return d.toLocaleDateString();
    if (s < 60) return "just now";
    if (s < 3600) return Math.floor(s / 60) + " min ago";
    if (s < 86400) return Math.floor(s / 3600) + " hr ago";
    if (s < 7 * 86400) return Math.floor(s / 86400) + " d ago";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  function paintTimes() {
    document.querySelectorAll("time[data-rel]").forEach(function (t) {
      t.textContent = rel(t.getAttribute("datetime"));
      t.title = new Date(t.getAttribute("datetime")).toLocaleString();
    });
  }
  paintTimes();
  setInterval(paintTimes, 60000);

  // ---- search
  var input = document.getElementById("search");
  var results = document.getElementById("search-results");
  if (input && results) {
    var index = null;
    var load = function () {
      if (index) return Promise.resolve(index);
      return fetch("/search-index.json").then(function (r) { return r.json(); }).then(function (d) { index = d; return d; });
    };
    var esc = function (s) {
      return String(s).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    };
    var run = function () {
      var q = input.value.trim().toLowerCase();
      if (q.length < 2) { results.hidden = true; return; }
      load().then(function (items) {
        var terms = q.split(/\s+/);
        var hits = items.map(function (it) {
          var title = it.title.toLowerCase(), hay = title + " " + (it.text || "").toLowerCase();
          if (!terms.every(function (t) { return hay.indexOf(t) !== -1; })) return null;
          var score = terms.reduce(function (s, t) { return s + (title.indexOf(t) !== -1 ? 2 : 1); }, 0);
          return { it: it, score: score };
        }).filter(Boolean).sort(function (a, b) { return b.score - a.score; }).slice(0, 8);
        results.innerHTML = hits.length
          ? hits.map(function (h) {
              return '<a href="' + esc(h.it.url) + '">' + esc(h.it.title) + "<small>" + esc(h.it.type) + "</small></a>";
            }).join("")
          : '<a href="/submit/">No match. Know where it is? Tell us<small>submit</small></a>';
        results.hidden = false;
      });
    };
    input.addEventListener("focus", load);
    input.addEventListener("input", run);
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".search")) results.hidden = true;
    });
  }
})();
