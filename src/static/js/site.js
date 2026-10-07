(function () {
  'use strict';
  var body = document.body;
  var toggle = document.querySelector('.menu-toggle');
  var menu = document.getElementById('mobile-menu');
  var FOCUSABLE = 'a[href], button:not([disabled])';
  var lastFocus = null;

  function openMenu() {
    if (!menu) return;
    lastFocus = document.activeElement;
    body.classList.add('menu-open');
    toggle.setAttribute('aria-expanded', 'true');
    var first = menu.querySelector(FOCUSABLE);
    if (first) setTimeout(function () { first.focus(); }, 50);
  }
  function closeMenu(returnFocus) {
    if (!body.classList.contains('menu-open')) return;
    body.classList.remove('menu-open');
    toggle.setAttribute('aria-expanded', 'false');
    if (returnFocus !== false && lastFocus) lastFocus.focus();
  }

  if (toggle && menu) {
    toggle.addEventListener('click', openMenu);
    document.querySelectorAll('[data-menu-close]').forEach(function (el) {
      el.addEventListener('click', function () { closeMenu(); });
    });
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { closeMenu(false); });
    });
    menu.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var items = menu.querySelectorAll(FOCUSABLE);
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    window.matchMedia('(min-width: 1024px)').addEventListener('change', function (m) {
      if (m.matches) closeMenu(false);
    });
  }

  // Desktop dropdowns: hover/focus handled in CSS; button toggles for touch + keyboard
  var dropdowns = document.querySelectorAll('.has-dropdown');
  function closeDropdowns(except) {
    dropdowns.forEach(function (d) {
      if (d === except) return;
      d.classList.remove('is-open');
      d.querySelector('.dropdown-toggle').setAttribute('aria-expanded', 'false');
    });
  }
  dropdowns.forEach(function (d) {
    var btn = d.querySelector('.dropdown-toggle');
    btn.addEventListener('click', function () {
      var open = !d.classList.contains('is-open');
      closeDropdowns(d);
      d.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', String(open));
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-dropdown')) closeDropdowns();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    closeMenu();
    var open = document.querySelector('.has-dropdown.is-open');
    if (open) { open.querySelector('.dropdown-toggle').focus(); closeDropdowns(); }
  });

  // Section reveal
  var items = document.querySelectorAll('[data-reveal]');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!('IntersectionObserver' in window) || reduce) {
    items.forEach(function (el) { el.classList.add('is-visible'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    items.forEach(function (el) { io.observe(el); });
  }
})();