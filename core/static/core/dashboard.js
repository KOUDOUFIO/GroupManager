(function () {
  "use strict";

  var counters = document.querySelectorAll("[data-counter]");
  if (!counters.length) {
    return;
  }

  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion) {
    counters.forEach(function (node) {
      var target = Number(node.getAttribute("data-target") || 0);
      var suffix = node.getAttribute("data-suffix") || "";
      var decimals = String(node.getAttribute("data-target") || "").includes(".") ? 1 : 0;
      node.textContent = target.toFixed(decimals) + suffix;
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
      var rawTarget = node.getAttribute("data-target") || "0";
      var target = Number(rawTarget);
      var suffix = node.getAttribute("data-suffix") || "";
      var decimals = rawTarget.includes(".") ? 1 : 0;
      var current = target * eased;
      node.textContent = current.toFixed(decimals) + suffix;
    });

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
})();
