// wovemind site: copy buttons, install tabs, catalog filter, hero terminal, scroll reveals. No dependencies.
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce) root.classList.add("w-motion");
  var live = doc.getElementById("w-live");
  function announce(msg) {
    if (!live) return;
    live.textContent = "";
    setTimeout(function () { live.textContent = msg; }, 30);
  }

  // Theme toggle: system -> light -> dark. System = no data-theme, so the CSS follows prefers-color-scheme.
  var themeBtn = doc.querySelector("[data-theme-toggle]");
  if (themeBtn) {
    var modes = ["system", "light", "dark"], mode = "system";
    try { var saved = localStorage.getItem("w-theme"); if (saved === "light" || saved === "dark") mode = saved; } catch (e) {}
    var paint = function () {
      themeBtn.dataset.mode = mode;
      themeBtn.setAttribute("aria-label", "Theme: " + mode);
      themeBtn.title = "Theme: " + mode;
    };
    paint();
    themeBtn.addEventListener("click", function () {
      mode = modes[(modes.indexOf(mode) + 1) % 3];
      if (mode === "system") root.removeAttribute("data-theme"); else root.dataset.theme = mode;
      try { if (mode === "system") localStorage.removeItem("w-theme"); else localStorage.setItem("w-theme", mode); } catch (e) {}
      paint();
      announce("Theme: " + mode);
    });
  }

  // Copy buttons: clipboard API, with a hidden-textarea fallback; the button and a live region both say "Copied".
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = doc.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;top:0;left:0;opacity:0;font-size:16px";
      doc.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = doc.execCommand("copy"); } catch (e) { ok = false; }
      doc.body.removeChild(ta);
      if (ok) resolve(); else reject(new Error("copy failed"));
    });
  }
  doc.addEventListener("click", function (ev) {
    var btn = ev.target.closest && ev.target.closest(".w-copy");
    if (!btn) return;
    var label = btn.querySelector("span");
    copyText(btn.getAttribute("data-copy")).then(function () {
      btn.classList.add("w-copied");
      label.textContent = "Copied";
      announce("Copied");
      clearTimeout(btn._t);
      btn._t = setTimeout(function () { btn.classList.remove("w-copied"); label.textContent = "Copy"; }, 1800);
    }, function () { announce("Could not copy. Select the command and copy it by hand."); });
  });

  // Install tabs: arrow keys move between tabs, as in the WAI-ARIA tabs pattern.
  Array.prototype.forEach.call(doc.querySelectorAll("[data-tabs]"), function (box) {
    var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));
    function select(i, focus) {
      tabs.forEach(function (t, k) {
        var on = k === i;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        doc.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) tabs[i].focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(i, false); });
      t.addEventListener("keydown", function (e) {
        var n = tabs.length, j = null;
        if (e.key === "ArrowRight") j = (i + 1) % n;
        else if (e.key === "ArrowLeft") j = (i - 1 + n) % n;
        else if (e.key === "Home") j = 0;
        else if (e.key === "End") j = n - 1;
        if (j !== null) { e.preventDefault(); select(j, true); }
      });
    });
    select(0, false);
  });

  // Catalog filter: free-text search over each card's words plus one category chip.
  var q = doc.getElementById("w-q"), grid = doc.getElementById("w-grid");
  if (q && grid) {
    var cards = Array.prototype.slice.call(grid.children);
    var chips = Array.prototype.slice.call(doc.querySelectorAll(".w-chip"));
    var results = doc.getElementById("w-results"), empty = doc.getElementById("w-empty");
    var cat = "";
    var apply = function () {
      var terms = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean), shown = 0;
      cards.forEach(function (c) {
        var words = c.getAttribute("data-search");
        var ok = (!cat || c.getAttribute("data-cat") === cat) && terms.every(function (t) { return words.indexOf(t) !== -1; });
        if (ok && c.hidden) {
          c.classList.remove("w-fade");
          void c.offsetWidth; // restart the fade on cards that come back
          c.classList.add("w-fade");
        }
        c.hidden = !ok;
        if (ok) { shown++; c.classList.add("w-in"); }
      });
      var total = cards.length;
      results.textContent = shown === total ? "Showing all " + total + " plugins"
        : "Showing " + shown + " of " + total + " plugins";
      empty.hidden = shown !== 0;
    };
    var timer;
    q.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(apply, 60); });
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        cat = chip.getAttribute("data-cat");
        chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
        apply();
      });
    });
    doc.getElementById("w-clear").addEventListener("click", function () {
      q.value = "";
      chips[0].click();
      q.focus();
    });
    // "/" focuses search, unless the reader is already typing somewhere or holds a modifier.
    doc.addEventListener("keydown", function (e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      var el = doc.activeElement, tag = el && el.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (el && el.isContentEditable)) return;
      e.preventDefault();
      q.focus();
      q.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    });
    if (q.value) apply();
  }

  // Hero terminal: types its lines while on screen, pauses off screen, loops. Static under reduced motion or without JS.
  var term = doc.querySelector(".w-term-body");
  if (term && !reduce && "IntersectionObserver" in window) {
    var lines = Array.prototype.map.call(term.children, function (el) { return { el: el, text: el.textContent }; });
    var caret = doc.createElement("span");
    caret.className = "w-caret";
    var li = 0, ci = 0, visible = false, pending = null;
    var reset = function () {
      lines.forEach(function (l) { l.el.textContent = ""; l.el.hidden = true; });
      li = 0; ci = 0;
    };
    var tick = function () {
      pending = null;
      if (!visible) return;
      if (li >= lines.length) { pending = setTimeout(function () { reset(); tick(); }, 4200); return; }
      var line = lines[li], comment = line.el.classList.contains("w-t-cmt");
      line.el.hidden = false;
      if (comment) { // comments appear whole, commands are typed
        line.el.textContent = line.text;
        li++; ci = 0;
        pending = setTimeout(tick, 380);
        return;
      }
      ci++;
      line.el.textContent = line.text.slice(0, ci);
      line.el.appendChild(caret);
      if (ci >= line.text.length) { li++; ci = 0; pending = setTimeout(tick, 650); }
      else pending = setTimeout(tick, 26 + Math.random() * 40);
    };
    reset();
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible && !pending) tick();
      if (!visible && pending) { clearTimeout(pending); pending = null; }
    }, { threshold: 0.25 }).observe(term);
  }

  // One-time reveals as sections scroll in.
  var rev = doc.querySelectorAll(".w-reveal");
  if (!reduce && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("w-in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    Array.prototype.forEach.call(rev, function (el) { io.observe(el); });
  } else {
    Array.prototype.forEach.call(rev, function (el) { el.classList.add("w-in"); });
  }
})();
