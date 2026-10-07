(function () {
  'use strict';
  var grid = document.getElementById('gallery-grid');
  var dlg = document.getElementById('lightbox');
  if (!grid || !dlg || typeof dlg.showModal !== 'function') return;

  var items = [].slice.call(grid.querySelectorAll('.gal-item'));
  var filters = [].slice.call(document.querySelectorAll('[data-filter]'));
  var img = document.getElementById('lb-img');
  var cap = document.getElementById('lb-cap');
  var visible = [], idx = 0, lastFocus = null, startX = null;

  function applyFilter(cat) {
    items.forEach(function (it) { it.hidden = !(cat === 'all' || it.dataset.category === cat); });
    filters.forEach(function (f) { f.setAttribute('aria-pressed', String(f.dataset.filter === cat)); });
  }
  filters.forEach(function (f) { f.addEventListener('click', function () { applyFilter(f.dataset.filter); }); });

  function show(i) {
    if (!visible.length) return;
    idx = (i + visible.length) % visible.length;
    var it = visible[idx];
    img.src = it.dataset.full;
    img.alt = it.dataset.alt;
    cap.textContent = it.dataset.caption || '';
    cap.hidden = !it.dataset.caption;
  }
  function open(it) {
    lastFocus = it;
    visible = items.filter(function (x) { return !x.hidden; });
    show(visible.indexOf(it));
    dlg.showModal();
  }
  items.forEach(function (it) { it.addEventListener('click', function () { open(it); }); });

  dlg.querySelector('.lb-close').addEventListener('click', function () { dlg.close(); });
  dlg.querySelector('.lb-prev').addEventListener('click', function () { show(idx - 1); });
  dlg.querySelector('.lb-next').addEventListener('click', function () { show(idx + 1); });
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener('close', function () { if (lastFocus) lastFocus.focus(); });
  dlg.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { show(idx - 1); }
    else if (e.key === 'ArrowRight') { show(idx + 1); }
  });
  dlg.addEventListener('touchstart', function (e) { startX = e.changedTouches[0].clientX; }, { passive: true });
  dlg.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 50) show(dx < 0 ? idx + 1 : idx - 1);
    startX = null;
  }, { passive: true });
})();