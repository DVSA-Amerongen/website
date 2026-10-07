// Gegevens uit Sportlink (Club.Dataservice) op de pagina zetten.
// Elk element met data-sl="..." wordt hier gevuld. De gegevens lopen via /api/sportlink/ (Cloudflare Function).
(function () {
  var API = '/api/sportlink/';
  var cache = {};

  function haal(onderdeel, params) {
    var qs = new URLSearchParams(params || {}).toString();
    var url = API + onderdeel + (qs ? '?' + qs : '');
    if (!cache[url]) {
      cache[url] = fetch(url).then(function (r) {
        if (!r.ok) throw new Error('Sportlink ' + r.status);
        return r.json();
      });
    }
    return cache[url];
  }
  function lijst(d) { return Array.isArray(d) ? d : (d && (d.items || d.data || d.wedstrijden)) || []; }
  function v(o) { for (var i = 1; i < arguments.length; i++) { var x = o && o[arguments[i]]; if (x !== undefined && x !== null && x !== '') return x; } return ''; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function datum(w) {
    var d = v(w, 'wedstrijddatum', 'datumopgemaakt');
    var t = d ? new Date(String(d).replace(/(\+\d{2})(\d{2})$/, '$1:$2')) : null;
    if (t && !isNaN(t)) return t;
    return null;
  }
  function dagTekst(t) { return t ? t.toLocaleDateString('nl-NL', { weekday: 'long', day: 'numeric', month: 'long' }) : ''; }
  function kort(t) { return t ? t.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' }) : ''; }
  function tijd(w) { return v(w, 'aanvangstijd', 'tijd') || (datum(w) ? datum(w).toTimeString().slice(0, 5) : ''); }
  function isDvsa(naam) { return /DVSA/i.test(naam || ''); }
  function resultaat(w) {
    var u = String(v(w, 'uitslag', 'uitslagregulier') || '');
    var m = u.match(/(\d+)\s*-\s*(\d+)/);
    if (!m) return null;
    var thuis = +m[1], uit = +m[2];
    var wijThuis = isDvsa(v(w, 'thuisteam'));
    var wij = wijThuis ? thuis : uit, zij = wijThuis ? uit : thuis;
    return { score: thuis + ' – ' + uit, r: wij > zij ? 'W' : wij < zij ? 'V' : 'G', wijThuis: wijThuis };
  }
  var LABEL = { W: 'Gewonnen', G: 'Gelijk', V: 'Verloren' };
  function fout(el, tekst) {
    el.innerHTML = '<p class="fout">' + (tekst || 'Deze gegevens konden even niet worden geladen. Bekijk ze in de Voetbal.nl-app.') + '</p>';
  }
  function teamFilter(naam) {
    return function (w) { var t = v(w, 'teamnaam'); return t ? t === naam : (v(w, 'thuisteam') === naam || v(w, 'uitteam') === naam); };
  }
  function hoofdletter(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }
  function uniekeTeams(d) { var gezien = {}; return lijst(d).filter(function (t) { var k = String(v(t, 'teamcode')); if (gezien[k]) return false; gezien[k] = 1; return true; }); }
  function persoonNaam(m) { var n = [v(m, 'voornaam'), v(m, 'tussenvoegsel'), v(m, 'achternaam')].filter(Boolean).join(' '); return n || v(m, 'naam'); }
  function afgeschermd(m) { return /afgeschermd/i.test(v(m, 'naam') + v(m, 'voornaam')); }
  var verslagenP = null;
  function verslagen() { if (!verslagenP) verslagenP = fetch('/data/verslagen.json').then(function (r) { return r.json(); }).catch(function () { return []; }); return verslagenP; }
  function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function vindVerslag(lijstV, w) {
    var t = norm(v(w, 'thuisteam')), u = norm(v(w, 'uitteam')), d = datum(w);
    return lijstV.filter(function (x) {
      if (norm(x.thuis) !== t || norm(x.uit) !== u) return false;
      if (!d) return true;
      var dv = new Date(x.datum); return Math.abs(dv - d) < 5 * 864e5;
    })[0];
  }
  function isJeugd(naam) { return /O\d|JO\d|MO\d|kabouter|mini/i.test(naam || ''); }

  var RENDER = {
    // Volgende wedstrijd van één team (home)
    volgende: function (el) {
      var team = el.dataset.team;
      return haal('programma', { aantaldagen: 30, eigenwedstrijden: 'JA' }).then(function (d) {
        var w = lijst(d).filter(teamFilter(team))[0];
        if (!w) { el.querySelector('[data-veld=tijd]').textContent = '–'; el.querySelector('[data-veld=dag]').textContent = 'Geen wedstrijd gepland'; return; }
        var t = datum(w);
        el.querySelector('[data-veld=thuis]').textContent = v(w, 'thuisteam');
        el.querySelector('[data-veld=uit]').textContent = v(w, 'uitteam');
        el.querySelector('[data-veld=tijd]').textContent = tijd(w);
        el.querySelector('[data-veld=dag]').textContent = dagTekst(t);
        el.querySelector('[data-veld=plek]').textContent = [v(w, 'accommodatie'), v(w, 'veld')].filter(Boolean).join(' · ');
        var thuisDvsa = isDvsa(v(w, 'thuisteam'));
        el.querySelector('[data-veld=embleem-thuis]').innerHTML = thuisDvsa ? '<img src="/img/dvsa-logo.png" alt="">' : esc(String(v(w, 'thuisteam')).slice(0, 3).toUpperCase());
        el.querySelector('[data-veld=embleem-uit]').innerHTML = !thuisDvsa ? '<img src="/img/dvsa-logo.png" alt="">' : esc(String(v(w, 'uitteam')).slice(0, 3).toUpperCase());
      });
    },
    'laatste-uitslag': function (el) {
      var team = el.dataset.team;
      return Promise.all([haal('uitslagen', { aantaldagen: 60, eigenwedstrijden: 'JA' }), verslagen()]).then(function (res) {
        var d = res[0], vl = res[1];
        var w = lijst(d).filter(teamFilter(team)).sort(function (a, b) { return (datum(b) || 0) - (datum(a) || 0); })[0];
        if (!w) { el.innerHTML = '<p class="laden">Nog geen uitslag dit seizoen.</p>'; return; }
        var r = resultaat(w);
        el.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;font-weight:600"><span>' + esc(v(w, 'thuisteam')) + '</span><span class="cijfer" style="font-size:34px">' + (r ? r.score : esc(v(w, 'uitslag'))) + '</span><span>' + esc(v(w, 'uitteam')) + '</span></div><span style="font-size:14px;color:var(--grijs)">' + dagTekst(datum(w)) + '</span>';
        var vs = vindVerslag(vl, w);
        if (vs) el.innerHTML += '<a class="btn btn-blauw" href="' + vs.url + '" style="margin-top:12px;padding:10px 18px;font-size:15px;width:100%">Lees het wedstrijdverslag →</a>';
      });
    },
    // Uitslagen: data-soort="jeugd" | "alles" | team
    uitslagen: function (el) {
      var soort = el.dataset.soort || 'alles', max = +(el.dataset.max || 50);
      return Promise.all([haal('uitslagen', { aantaldagen: +(el.dataset.dagen || 7), eigenwedstrijden: 'JA' }), verslagen()]).then(function (res) {
        var d = res[0], vl = res[1];
        var rijen = lijst(d);
        if (soort === 'jeugd') rijen = rijen.filter(function (w) { return isJeugd(v(w, 'teamnaam') || (isDvsa(v(w, 'thuisteam')) ? v(w, 'thuisteam') : v(w, 'uitteam'))); });
        else if (soort !== 'alles') rijen = rijen.filter(teamFilter(soort));
        rijen = rijen.slice(0, max);
        if (!rijen.length) { el.innerHTML = '<p class="laden">Geen uitslagen in de afgelopen week.</p>'; return; }
        el.innerHTML = rijen.map(function (w) {
          var r = resultaat(w) || { score: esc(v(w, 'uitslag')), r: 'G', wijThuis: isDvsa(v(w, 'thuisteam')) };
          var eigen = r.wijThuis ? v(w, 'thuisteam') : v(w, 'uitteam');
          var tegen = r.wijThuis ? v(w, 'uitteam') : v(w, 'thuisteam');
          return '<div class="rij uitslag-rij"><span class="res ' + r.r + '" title="' + LABEL[r.r] + '">' + r.r + '</span><span style="font-weight:700">' + esc(eigen) + '</span><span class="tegen">' + (r.wijThuis ? 'thuis tegen ' : 'uit bij ') + esc(tegen) + (vindVerslag(vl, w) ? ' · <a class="link" href="' + vindVerslag(vl, w).url + '">verslag →</a>' : '') + '</span><span class="cijfer">' + r.score + '</span></div>';
        }).join('');
      });
    },
    // Programma: data-thuis="ja" voor alleen thuiswedstrijden
    programma: function (el) {
      var p = { aantaldagen: +(el.dataset.dagen || 7), eigenwedstrijden: 'JA' };
      if (el.dataset.thuis) { p.thuis = 'JA'; p.uit = 'NEE'; }
      var team = el.dataset.team;
      return haal('programma', p).then(function (d) {
        var rijen = lijst(d);
        if (team) rijen = rijen.filter(teamFilter(team));
        if (!rijen.length) { el.innerHTML = '<p class="laden">Er staan deze week geen wedstrijden gepland.</p>'; return; }
        var html = '', dag = '';
        rijen.forEach(function (w) {
          var t = datum(w), dt = dagTekst(t);
          if (dt !== dag) { dag = dt; html += '<h3 style="font-size:24px;margin:22px 0 6px">' + esc(dt) + '</h3>'; }
          var eigen = isDvsa(v(w, 'thuisteam')) ? v(w, 'thuisteam') : v(w, 'uitteam');
          var thuis = isDvsa(v(w, 'thuisteam'));
          html += '<div class="rij prog-rij' + (eigen === 'DVSA 1' ? ' licht' : '') + '"><span class="cijfer">' + esc(tijd(w)) + '</span><span style="font-weight:700">' + esc(eigen) + '</span><span class="tegen">' + (thuis ? '' : 'uit bij ') + esc(thuis ? v(w, 'uitteam') : v(w, 'thuisteam')) + '</span><span class="veld" style="color:var(--grijs)">' + esc(thuis ? hoofdletter(v(w, 'veld')) : hoofdletter(String(v(w, 'plaats', 'accommodatie')).toLowerCase())) + '</span></div>';
        });
        el.innerHTML = html;
      });
    },
    afgelastingen: function (el) {
      return haal('afgelastingen', { aantaldagen: 7 }).then(function (d) {
        var rijen = lijst(d);
        if (!rijen.length) return;
        el.querySelector('[data-veld=titel]').textContent = rijen.length + (rijen.length === 1 ? ' wedstrijd afgelast' : ' wedstrijden afgelast');
        el.style.borderLeftColor = 'var(--oranje)';
        el.querySelector('[data-veld=lijst]').innerHTML = rijen.map(function (w) { return '<div style="padding:6px 0;border-top:1px solid var(--lijn-2)">' + esc(v(w, 'thuisteam')) + ' – ' + esc(v(w, 'uitteam')) + '</div>'; }).join('');
      });
    },
    // Stand van een team (data-team="DVSA 1" of via teamcode)
    stand: function (el) {
      var naam = el.dataset.team, code = el.dataset.code;
      return haal('teams').then(function (d) {
        var rijen = lijst(d).filter(function (t) { return code ? String(v(t, 'teamcode')) === String(code) : v(t, 'teamnaam') === naam; });
        var poule = rijen.filter(function (t) { return v(t, 'competitiesoort') === 'regulier'; })[0] || rijen[0];
        if (!poule) throw new Error('geen poule');
        var label = el.parentNode.querySelector('[data-veld=klasse]');
        if (label) label.textContent = v(poule, 'klassepoule', 'klasse');
        return haal('poulestand', { poulecode: v(poule, 'poulecode') });
      }).then(function (d) {
        var rijen = lijst(d);
        if (!rijen.length) { el.innerHTML = '<p class="laden">Nog geen stand beschikbaar.</p>'; return; }
        el.innerHTML = '<div class="rij stand-rij rijkop"><span>#</span><span>Team</span><span>G</span><span>DS</span><span>P</span></div>' + rijen.map(function (r) {
          var eigen = String(v(r, 'eigenteam')) === 'true';
          var ds = v(r, 'doelsaldo');
          return '<div class="rij stand-rij' + (eigen ? ' eigen' : '') + '"><span>' + esc(v(r, 'positie')) + '</span><span>' + esc(v(r, 'teamnaam')) + '</span><span>' + esc(v(r, 'gespeeldewedstrijden')) + '</span><span>' + (ds > 0 ? '+' : '') + esc(ds) + '</span><span style="font-weight:700">' + esc(v(r, 'punten')) + '</span></div>';
        }).join('') + '<p style="font-size:14px;color:var(--grijs);margin:10px 0 0">G = gespeeld · DS = doelsaldo · P = punten</p>';
      });
    },
    // Alle teams (Teams-pagina)
    teams: function (el) {
      return haal('teams').then(function (d) {
        var teams = uniekeTeams(d).filter(function (t) { return v(t, 'teamsoort') === 'bond' && !/futsal|zaal/i.test(v(t, 'spelsoort')); });
        // van jong naar oud: leeftijd uit de teamnaam (O8, MO13, O19), senioren daarna, 35+/45+ als laatste
        function leeftijd(t) { var n = v(t, 'teamnaam'), m = n.match(/M?O(\d+)/); if (m && isJeugd(n)) return +m[1]; m = n.match(/(\d+)\+/); return m ? 100 + +m[1] : 50; }
        function volgnr(t) { var m = v(t, 'teamnaam').match(/-(\d+)|DVSA (\d+)$/); return m ? +(m[1] || m[2]) : 0; }
        teams.sort(function (a, b) { return leeftijd(a) - leeftijd(b) || (/MO/.test(v(a, 'teamnaam')) - /MO/.test(v(b, 'teamnaam'))) || volgnr(a) - volgnr(b); });
        var jeugd = [], senioren = [];
        teams.forEach(function (t) { (/senior|veteraan|35|45|55/i.test(v(t, 'leeftijdscategorie')) && !isJeugd(v(t, 'teamnaam')) ? senioren : jeugd).push(t); });
        function kaart(t) {
          var naam = v(t, 'teamnaam');
          var url = '/teams/team/?code=' + encodeURIComponent(v(t, 'teamcode')) + '&lokaal=' + encodeURIComponent(v(t, 'lokaleteamcode')) + '&naam=' + encodeURIComponent(naam);
          return '<a class="team-kaart" href="' + url + '"><span><b>' + esc(naam) + '</b><br><small>' + esc([v(t, 'speeldag'), v(t, 'klassepoule')].filter(Boolean).join(' · ')) + '</small></span><span class="link" style="font-size:15px">Staf, selectie en programma →</span></a>';
        }
        el.querySelector('[data-veld=jeugd]').innerHTML = '<a class="team-kaart" href="/lid-worden/#kabouters"><span><b>Kabouters</b><br><small>3 t/m 7 jaar · zaterdag 9:00</small></span><span class="link" style="font-size:15px">Meer over de kabouters →</span></a>' + jeugd.map(kaart).join('');
        el.querySelector('[data-veld=senioren]').innerHTML = senioren.map(kaart).join('') + '<a class="team-kaart" href="/dc-dvsa/" style="background:var(--navy);color:#fff;border-color:var(--navy)"><span><b>DC DVSA</b><br><small style="color:#cfd5e2">Onze dartsclub, vrijdagavond</small></span><span style="color:var(--geel);font-weight:700;font-size:15px">Naar DC DVSA →</span></a>';
        var n = el.querySelector('[data-veld=aantal]'); if (n) n.textContent = jeugd.length + ' jeugdteams, inclusief de samenwerkingsteams met HDS.';
      });
    },
    // Teampagina (/teams/team/?code=..&lokaal=..&naam=..)
    team: function (el) {
      var q = new URLSearchParams(location.search);
      var naam = q.get('naam') || '';
      document.querySelectorAll('[data-veld=teamnaam]').forEach(function (x) { x.textContent = naam || 'Team'; });
      if (naam) document.title = naam + ' – DVSA';
      var code = q.get('code'), lokaal = q.get('lokaal');
      fetch('/data/teamfotos.json').then(function (r) { return r.json(); }).then(function (d) {
        var f = (d.teamfotos || []).filter(function (t) { return t.team && naam && t.team.toLowerCase().replace(/\s+/g, ' ') === naam.toLowerCase().replace(/\s+/g, ' '); })[0];
        if (!f || !f.foto) return;
        var img = document.querySelector('[data-veld=teamfoto]');
        img.src = f.foto; img.alt = 'Teamfoto ' + naam;
        document.querySelector('[data-veld=teamfoto-sectie]').hidden = false;
        var fotos = f.fotos || [];
        if (fotos.length) {
          var baan = document.querySelector('[data-veld=fotoshow-baan]'), st = document.querySelector('[data-veld=fotoshow-stippen]'), nu = 0, timer;
          baan.innerHTML = fotos.map(function (src, i) { return '<img src="' + esc(src) + '" alt="Foto ' + (i + 1) + ' van ' + esc(naam) + '" loading="lazy"' + (i ? '' : ' class="actief"') + '>'; }).join('');
          st.innerHTML = fotos.map(function (_, i) { return '<button aria-label="Foto ' + (i + 1) + '"' + (i ? '' : ' aria-current="true"') + '><span></span></button>'; }).join('');
          var imgs = baan.querySelectorAll('img'), knoppen = st.querySelectorAll('button');
          function toon(i) { nu = (i + imgs.length) % imgs.length; imgs.forEach(function (x, k) { x.classList.toggle('actief', k === nu); }); knoppen.forEach(function (x, k) { x.setAttribute('aria-current', k === nu ? 'true' : 'false'); }); }
          var show = document.querySelector('[data-veld=fotoshow]');
          show.querySelector('.vorige').onclick = function () { clearInterval(timer); toon(nu - 1); };
          show.querySelector('.volgende').onclick = function () { clearInterval(timer); toon(nu + 1); };
          knoppen.forEach(function (b, k) { b.onclick = function () { clearInterval(timer); toon(k); }; });
          if (!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) timer = setInterval(function () { toon(nu + 1); }, 5000);
          document.querySelector('[data-veld=fotos-sectie]').hidden = false;
        }
      }).catch(function () {});
      var taken = [];
      if (code) {
        taken.push(haal('team-indeling', { teamcode: code, lokaleteamcode: lokaal }).then(function (d) {
          var alle = lijst(d);
          var mensen = alle.filter(function (m) { return !afgeschermd(m); });
          var isSpeler = function (m) { return /speler/i.test(v(m, 'rol')); };
          var staf = mensen.filter(function (m) { return !isSpeler(m); });
          var spelers = mensen.filter(isSpeler);
          var verborgenStaf = alle.filter(function (m) { return afgeschermd(m) && !isSpeler(m); }).length;
          var verborgenSpelers = alle.filter(function (m) { return afgeschermd(m) && isSpeler(m); }).length;
          function ini(m) { return ((v(m, 'voornaam') || '?')[0] + (v(m, 'achternaam') || '')[0]).toUpperCase(); }
          el.querySelector('[data-veld=staf]').innerHTML = (staf.length ? staf.map(function (m) { return '<div class="persoon"><span class="initialen">' + esc(ini(m)) + '</span><span><b>' + esc(persoonNaam(m)) + '</b><br><small style="color:var(--grijs)">' + esc(v(m, 'functie') || v(m, 'rol')) + '</small></span></div>'; }).join('') : '<p class="laden">Geen staf bekend.</p>') +
            (verborgenStaf ? '<p style="font-size:14px;color:var(--grijs);margin:10px 0 0">' + verborgenStaf + (verborgenStaf === 1 ? ' staflid staat' : ' stafleden staan') + ' niet op de site vanwege de privacy-instelling in Sportlink.</p>' : '');
          el.querySelector('[data-veld=selectie]').innerHTML = (spelers.length ? '<div class="raster r2" style="gap:0 16px">' + spelers.map(function (m) { return '<span style="padding:9px 0;border-bottom:1px solid var(--lijn-2)">' + esc(persoonNaam(m)) + '</span>'; }).join('') + '</div>' : '<p class="laden">Geen spelers bekend.</p>') +
            (verborgenSpelers ? '<p style="font-size:14px;color:var(--grijs);margin:12px 0 0">' + verborgenSpelers + (verborgenSpelers === 1 ? ' speler staat' : ' spelers staan') + ' niet op de site vanwege de privacy-instelling in Sportlink.</p>' : '');
          var a = el.querySelector('[data-veld=aantal]'); if (a) a.textContent = (spelers.length + verborgenSpelers) + ' spelers';
        }).catch(function () { fout(el.querySelector('[data-veld=staf]')); }));
      }
      return Promise.all(taken);
    }
  };

  function vindTeam(naam, code) {
    return haal('teams').then(function (d) {
      return lijst(d).filter(function (t) { return code ? String(v(t, 'teamcode')) === String(code) : v(t, 'teamnaam') === naam; })[0];
    });
  }

  document.querySelectorAll('[data-sl]').forEach(function (el) {
    var f = RENDER[el.dataset.sl];
    if (!f) return;
    // teampagina: team uit de adresbalk doorgeven aan onderliggende blokken
    var q = new URLSearchParams(location.search);
    if (el.dataset.teamUitUrl !== undefined && q.get('naam')) { el.dataset.team = q.get('naam'); if (el.dataset.sl === 'uitslagen') el.dataset.soort = q.get('naam'); if (q.get('code')) el.dataset.code = q.get('code'); }
    Promise.resolve().then(function () { return f(el); }).catch(function () {
      if (el.dataset.sl === 'afgelastingen') return;
      fout(el.dataset.sl === 'volgende' || el.dataset.sl === 'teams' ? el.querySelector('[data-veld=foutplek]') || el : el);
    });
  });
})();
