// Menu, carrousel, tabbladen en nieuwsfilter
(function () {
  // tijdelijke banners verbergen na hun einddatum
  var vandaag = new Date().toISOString().slice(0, 10);
  document.querySelectorAll('[data-tot]').forEach(function (b) { if (b.dataset.tot && b.dataset.tot < vandaag) b.hidden = true; });

  // fotocarrousels in berichten
  document.querySelectorAll('[data-show]').forEach(function (show) {
    var imgs = show.querySelectorAll('.fotoshow-baan img'), teller = show.querySelector('.show-teller'), nu = 0;
    function toon(i) {
      nu = (i + imgs.length) % imgs.length;
      imgs.forEach(function (x, k) { x.classList.toggle('actief', k === nu); });
      if (teller) teller.textContent = (nu + 1) + ' / ' + imgs.length;
    }
    show.querySelector('.vorige').addEventListener('click', function () { toon(nu - 1); });
    show.querySelector('.volgende').addEventListener('click', function () { toon(nu + 1); });
    // vegen op telefoon
    var x0 = null;
    show.addEventListener('touchstart', function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
    show.addEventListener('touchend', function (ev) { if (x0 === null) return; var dx = ev.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) toon(nu + (dx < 0 ? 1 : -1)); x0 = null; });
  });

  // Facebook-tijdlijn pas laden na een klik (privacy)
  document.querySelectorAll('[data-fb-pagina]').forEach(function (vak) {
    var knop = vak.querySelector('button');
    if (!knop) return;
    knop.addEventListener('click', function () {
      // smaller dan de kaart, zodat de foto's in de berichten niet te groot worden
      var breed = Math.max(220, Math.min(380, Math.floor(vak.clientWidth)));
      var hoog = 560;
      var src = 'https://www.facebook.com/plugins/page.php?href=' + encodeURIComponent(vak.dataset.fbPagina) +
        '&tabs=timeline&width=' + breed + '&height=' + hoog +
        '&small_header=true&hide_cover=true&show_facepile=false&adapt_container_width=false&lazy=true&locale=nl_NL';
      var f = document.createElement('iframe');
      f.src = src; f.title = 'Facebook-berichten van DVSA';
      f.width = breed; f.height = hoog;
      f.setAttribute('allow', 'encrypted-media'); f.setAttribute('scrolling', 'no');
      f.style.cssText = 'border:0;overflow:hidden;display:block;margin:0 auto;max-width:100%;border-radius:12px;background:#fff';
      vak.innerHTML = ''; vak.appendChild(f);
      vak.classList.add('geladen');
    });
  });

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
    // /nieuws/#dvsa-1 opent direct met dat filter
    var h = location.hash.slice(1);
    if (h) filter.querySelectorAll('button').forEach(function (b) { if (b.dataset.filter.toLowerCase().replace(/[^a-z0-9]+/g, '-') === h) b.click(); });
  }
})();
