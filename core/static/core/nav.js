(function () {
  "use strict";

  // Bouton "Retour" : revient a la page precedente du site, sinon au tableau de bord.
  document.querySelectorAll("[data-back]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      var fromSite = document.referrer && document.referrer.indexOf(window.location.origin + "/") === 0;
      if (fromSite && window.history.length > 1) {
        event.preventDefault();
        window.history.back();
      }
    });
  });

  // Fenetre "Tous vos modules" : ouverte par chaque bouton [data-modules-open].
  var dialog = document.querySelector("[data-modules]");
  if (!dialog) {
    return;
  }
  var openers = document.querySelectorAll("[data-modules-open]");
  var lastOpener = null;

  function focusables() {
    return Array.prototype.slice.call(
      dialog.querySelectorAll("a[href], button:not([disabled])")
    );
  }

  function setOpen(open, opener) {
    dialog.hidden = !open;
    document.documentElement.classList.toggle("modules-open", open);
    openers.forEach(function (btn) {
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    if (open) {
      lastOpener = opener || null;
      var current = dialog.querySelector(".module-tile.is-active") || dialog.querySelector(".module-tile");
      if (current) {
        current.focus();
      }
    } else if (lastOpener) {
      lastOpener.focus();
    }
  }

  openers.forEach(function (btn) {
    btn.addEventListener("click", function () {
      setOpen(dialog.hidden, btn);
    });
  });

  dialog.querySelectorAll("[data-modules-close]").forEach(function (node) {
    node.addEventListener("click", function () {
      setOpen(false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (dialog.hidden) {
      return;
    }
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    // Garde le focus clavier a l'interieur de la fenetre.
    if (event.key === "Tab") {
      var items = focusables();
      if (!items.length) {
        return;
      }
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
})();
