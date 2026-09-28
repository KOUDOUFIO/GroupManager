(function () {
  "use strict";

  var counters = document.querySelectorAll("[data-counter]");
  if (!counters.length) {
    return;
  }

  var locale = document.documentElement.lang || undefined;

  function decimalsOf(raw) {
    var parts = String(raw).split(".");
    return parts.length > 1 ? Math.min(parts[1].length, 2) : 0;
  }

  function render(node, value) {
    var raw = node.getAttribute("data-target") || "0";
    var decimals = decimalsOf(raw);
    var suffix = node.getAttribute("data-suffix") || "";
    node.textContent = value.toLocaleString(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }) + suffix;
  }

  function target(node) {
    var value = Number(node.getAttribute("data-target") || 0);
    return isNaN(value) ? 0 : value;
  }

  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion) {
    counters.forEach(function (node) {
      render(node, target(node));
    });
    return;
  }

  var duration = 1200;
  var start = performance.now();

  function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  function tick(now) {
    var progress = Math.min((now - start) / duration, 1);
    var eased = easeOutCubic(progress);

    counters.forEach(function (node) {
      render(node, target(node) * eased);
    });

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
})();
