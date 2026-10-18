(function () {
  // Índice cerrado en pantallas pequeñas
  var t = document.querySelector('.toc details');
  if (t && window.innerWidth < 900) t.removeAttribute('open');
  if (t) t.addEventListener('click', function (e) {
    if (e.target.tagName === 'A' && window.innerWidth < 900) t.removeAttribute('open');
  });

  // Tooltip de siglas (funciona con toque en móvil)
  var tip = null;
  function hide() { if (tip) { tip.remove(); tip = null; } }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('abbr[title]');
    hide();
    if (!a) return;
    tip = document.createElement('div');
    tip.id = 'tip';
    tip.textContent = a.textContent + ': ' + a.getAttribute('title');
    document.body.appendChild(tip);
    var r = a.getBoundingClientRect();
    var x = Math.min(Math.max(8, r.left), window.innerWidth - tip.offsetWidth - 8);
    var y = r.bottom + 6;
    if (y + tip.offsetHeight > window.innerHeight) y = r.top - tip.offsetHeight - 6;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  });
  window.addEventListener('scroll', hide, { passive: true });

  // Filtro de la tabla de siglas
  var f = document.getElementById('filtro');
  if (f) {
    var rows = document.querySelectorAll('#siglas-tabla tbody tr');
    var norm = function (s) { return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
    f.addEventListener('input', function () {
      var q = norm(f.value.trim());
      var n = 0;
      rows.forEach(function (r) {
        var ok = !q || norm(r.textContent).indexOf(q) > -1;
        r.style.display = ok ? '' : 'none';
        if (ok) n++;
      });
      document.getElementById('nfilt').textContent = n;
    });
  }
})();
