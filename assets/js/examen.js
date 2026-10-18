(function () {
  var B = window.BANCO || { mcq: [], fill: [], casos: [] };
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var norm = function (s) { return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ''); };
  var shuffle = function (a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
  var store = {
    get: function () { try { return JSON.parse(localStorage.getItem('vistas') || '[]'); } catch (e) { return []; } },
    add: function (ids) { try { var v = store.get().concat(ids).slice(-600); localStorage.setItem('vistas', JSON.stringify(v)); } catch (e) {} },
    clear: function () { try { localStorage.removeItem('vistas'); } catch (e) {} }
  };
  var inS = function (item, ses) { var s = Array.isArray(item.s) ? item.s : [item.s]; return s.some(function (x) { return ses.indexOf(+x) > -1; }); };
  function pick(pool, n, ses, nuevas) {
    pool = pool.filter(function (x) { return inS(x, ses); });
    if (n === 'all') return shuffle(pool);
    var seen = nuevas ? store.get() : [];
    var fresh = shuffle(pool.filter(function (x) { return seen.indexOf(x.id) < 0; }));
    var old = shuffle(pool.filter(function (x) { return seen.indexOf(x.id) > -1; }));
    return fresh.concat(old).slice(0, n);
  }

  // Configuración inicial
  var counts = {};
  B.mcq.concat(B.fill).forEach(function (x) { counts[x.s] = (counts[x.s] || 0) + 1; });
  var pre = (location.search.match(/[?&]s=(\d)/) || [])[1];
  var chk = $('#ses');
  for (var i = 1; i <= 7; i++) {
    var l = document.createElement('label');
    l.innerHTML = '<input type="checkbox" value="' + i + '"' + (!pre || +pre === i ? ' checked' : '') + '> S' + i + ' <small>(' + (counts[i] || 0) + ')</small>';
    chk.appendChild(l);
  }
  $('#stats').textContent = B.mcq.length + ' preguntas de opción múltiple · ' + B.fill.length + ' para completar · ' + B.casos.length + ' casos';

  var state = null, t0 = 0, timer = null;

  function gen() {
    var ses = Array.prototype.map.call(document.querySelectorAll('#ses input:checked'), function (x) { return +x.value; });
    if (!ses.length) { alert('Elige al menos una sesión.'); return; }
    var val = function (id) { var v = $(id).value; return v === 'all' ? 'all' : +v; };
    var nuevas = $('#nuevas').checked;
    var M = pick(B.mcq, val('#nm'), ses, nuevas), F = pick(B.fill, val('#nf'), ses, nuevas), C = pick(B.casos, val('#nc'), ses, nuevas);
    state = { M: M, F: F, C: C, done: false };
    var h = [], k = 0;
    if (M.length || F.length) h.push('<h2 id="p1">Parte I · Teórica</h2>');
    if (M.length) h.push('<h3>A. Opción múltiple <span class="tag">' + M.length + ' preguntas · 1 correcta</span></h3>');
    M.forEach(function (q, qi) {
      var ord = shuffle([0, 1, 2, 3]);
      q._ord = ord;
      h.push('<div class="q" id="m' + qi + '"><p><span class="n">' + (++k) + '.</span> ' + esc(q.q) + ' <span class="tag">S' + q.s + '</span></p>');
      ord.forEach(function (oi, pos) {
        h.push('<label class="op" data-o="' + oi + '"><input type="radio" name="m' + qi + '" value="' + oi + '"><span><b>' + 'abcd'[pos] + ')</b> ' + esc(q.o[oi]) + '</span></label>');
      });
      h.push('<div class="exp"></div></div>');
    });
    if (F.length) h.push('<h3>B. Completa los espacios <span class="tag">' + F.length + ' ítems</span></h3>');
    F.forEach(function (q, qi) {
      var txt = esc(q.t).replace(/\{\{(\d+)\}\}/g, function (_, n) { return '<input type="text" class="fillin" data-q="' + qi + '" data-h="' + (n - 1) + '" autocomplete="off" aria-label="espacio ' + n + '">'; });
      h.push('<div class="q" id="f' + qi + '"><p><span class="n">' + (++k) + '.</span> ' + txt + ' <span class="tag">S' + q.s + '</span></p><div class="exp"></div></div>');
    });
    if (C.length) h.push('<h2 id="p2">Parte II · Práctica</h2>');
    C.forEach(function (c, ci) {
      h.push('<div class="q caso-ex"><h3>Caso ' + (ci + 1) + ' · ' + esc(c.titulo) + ' <span class="tag">S' + [].concat(c.s).join(', S') + '</span></h3><div class="enunciado">' + c.enunciado + '</div><h4>Se pide</h4><ol>' +
        c.preguntas.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ol><label>Tu respuesta (borrador)</label><textarea placeholder="Desarrolla tu análisis aquí…"></textarea>' +
        '<details class="sol"><summary>Ver solución modelo y criterios</summary>' + c.solucion + '<h4>Criterios de corrección</h4><ul>' + (c.criterios || []).map(function (x) { return '<li><label><input type="checkbox" class="crit"> ' + esc(x) + '</label></li>'; }).join('') + '</ul></details></div>');
    });
    if (!k && !C.length) h.push('<p>No hay preguntas para esa selección.</p>');
    $('#examen').innerHTML = h.join('');
    $('#examen').classList.remove('hide');
    $('#barra').classList.remove('hide');
    $('#res').textContent = '';
    $('#calificar').disabled = false;
    store.add(M.concat(F, C).map(function (x) { return x.id; }));
    t0 = Date.now();
    clearInterval(timer);
    timer = setInterval(function () { var s = Math.floor((Date.now() - t0) / 1000); $('#reloj').textContent = Math.floor(s / 60) + ':' + ('0' + s % 60).slice(-2); }, 1000);
    $('#examen').scrollIntoView();
  }

  function grade() {
    if (!state || state.done) return;
    state.done = true;
    clearInterval(timer);
    var okM = 0, okF = 0, totF = 0;
    state.M.forEach(function (q, qi) {
      var box = document.getElementById('m' + qi);
      var sel = box.querySelector('input:checked');
      var good = sel && +sel.value === q.a;
      if (good) okM++;
      box.querySelectorAll('.op').forEach(function (op) {
        var o = +op.getAttribute('data-o');
        if (o === q.a) op.classList.add('good');
        else if (sel && o === +sel.value) op.classList.add('badc');
        op.querySelector('input').disabled = true;
      });
      var letra = 'abcd'[q._ord.indexOf(q.a)];
      box.querySelector('.exp').innerHTML = '<b>' + (good ? '✔ Correcto' : '✘ Incorrecto') + '</b> · Respuesta: <b>' + letra + ')</b><br>' + esc(q.exp || '');
      box.classList.add('done');
    });
    state.F.forEach(function (q, qi) {
      var box = document.getElementById('f' + qi);
      var all = true;
      box.querySelectorAll('.fillin').forEach(function (inp) {
        var alts = q.r[+inp.getAttribute('data-h')] || [];
        var v = norm(inp.value);
        var good = v && alts.some(function (a) { return norm(a) === v; });
        totF++;
        if (good) okF++; else all = false;
        inp.classList.add(good ? 'good' : 'badc');
        inp.disabled = true;
      });
      box.querySelector('.exp').innerHTML = '<b>' + (all ? '✔ Correcto' : '✘ Revisa') + '</b> · Respuestas: ' + q.r.map(function (a, i) { return '(' + (i + 1) + ') <b>' + esc(a[0]) + '</b>'; }).join(' · ') + (q.exp ? '<br>' + esc(q.exp) : '');
      box.classList.add('done');
    });
    document.querySelectorAll('.caso-ex details').forEach(function (d) { d.open = true; });
    var tot = state.M.length + totF, ok = okM + okF;
    var nota = tot ? Math.round(20 * ok / tot * 10) / 10 : 0;
    $('#res').innerHTML = 'Opción múltiple: <b>' + okM + '/' + state.M.length + '</b> · Completar: <b>' + okF + '/' + totF + '</b> · Nota parte teórica: <span class="big">' + nota + '/20</span>' + (state.C.length ? ' · Autoevalúa los casos con los criterios.' : '');
    $('#calificar').disabled = true;
  }

  $('#generar').addEventListener('click', gen);
  $('#calificar').addEventListener('click', grade);
  $('#reiniciar').addEventListener('click', function () { store.clear(); alert('Historial de preguntas vistas borrado.'); });
})();
