(function () {
  "use strict";

  var root = document.documentElement;
  var toggle = document.querySelector(".theme-toggle");
  var label = document.querySelector(".theme-toggle-label");

  function paintLabel() {
    if (label) label.textContent = root.classList.contains("light") ? "Dark" : "Light";
  }
  paintLabel();

  if (toggle) {
    toggle.addEventListener("click", function () {
      root.classList.toggle("light");
      try {
        localStorage.setItem("nexoma-theme", root.classList.contains("light") ? "light" : "dark");
      } catch (e) {}
      paintLabel();
    });
  }

  var menuBtn = document.querySelector(".menu-toggle");
  var menu = document.getElementById("site-menu");
  if (menuBtn && menu) {
    menuBtn.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Mark the current page in the primary nav.
  var here = location.pathname.replace(/\/+$/, "") || "/";
  Array.prototype.forEach.call(document.querySelectorAll(".site-menu a"), function (a) {
    var href = a.getAttribute("href") || "";
    if (href.charAt(0) !== "/") return;
    if (href.replace(/\/+$/, "") === here || (here === "/" && href === "/")) {
      a.setAttribute("aria-current", "page");
    }
  });
})();
