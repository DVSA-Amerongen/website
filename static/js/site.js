// Menu, carrousel, tabbladen en nieuwsfilter
(function () {
  // mobiel menu
  var knop = document.querySelector('.menuknop');
  var nav = document.getElementById('hoofdmenu');
  if (knop && nav) {
    knop.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      knop.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // carrousel
  var car = document.querySelector('.carrousel');
  if (car) {
    var dias = car.querySelectorAll('.dia');
    var stippen = car.querySelectorAll('.stippen button');
    var nu = 0, timer;
    function toon(i) {
      nu = (i + dias.length) % dias.length;
      dias.forEach(function (d, k) { d.classList.toggle('actief', k === nu); d.setAttribute('aria-hidden', k === nu ? 'false' : 'true'); });
      stippen.forEach(function (s, k) { s.setAttribute('aria-current', k === nu ? 'true' : 'false'); });
    }
    function stop() { clearInterval(timer); }
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduce) timer = setInterval(function () { toon(nu + 1); }, 6000);
    car.querySelector('.vorige').addEventListener('click', function () { stop(); toon(nu - 1); });
    car.querySelector('.volgende').addEventListener('click', function () { stop(); toon(nu + 1); });
    stippen.forEach(function (s, k) { s.addEventListener('click', function () { stop(); toon(k); }); });
    toon(0);
  }

  // tabbladen
  document.querySelectorAll('[role=tablist]').forEach(function (lijst) {
    var tabs = lijst.querySelectorAll('[role=tab]');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) {
          var sel = t === tab;
          t.setAttribute('aria-selected', sel ? 'true' : 'false');
          document.getElementById(t.getAttribute('aria-controls')).hidden = !sel;
        });
        if (history.replaceState) history.replaceState(null, '', '#' + tab.dataset.naam);
      });
    });
    var hash = location.hash.slice(1);
    if (hash) { var t = lijst.querySelector('[data-naam="' + hash + '"]'); if (t) t.click(); }
  });

  // nieuwsfilter
  var filter = document.querySelector('[data-nieuwsfilter]');
  if (filter) {
    var kaarten = document.querySelectorAll('[data-cat]');
    var leeg = document.getElementById('nieuws-leeg');
    var teller = document.getElementById('nieuws-teller');
    filter.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        var cat = b.dataset.filter, n = 0;
        filter.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
        kaarten.forEach(function (k) { var ok = cat === 'Alles' || k.dataset.cat === cat; k.hidden = !ok; if (ok) n++; });
        leeg.hidden = n > 0;
        teller.textContent = n === 1 ? '1 bericht' : n + ' berichten';
      });
    });
  }
})();
