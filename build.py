#!/usr/bin/env python3
"""Bouwt de DVSA-website naar de map dist/.

Alleen standaard Python, geen extra pakketten nodig. Cloudflare Pages draait dit
script bij elke wijziging (build command: python3 build.py, output: dist).

Inhoud aanpassen doe je in content/:
  content/site.json          adres, mailadressen, melding bovenaan, kantinetijden, contributie
  content/sponsors.json      alle sponsors met logo, website en groep
  content/nieuws/*.md        nieuwsberichten (zie _VOORBEELD.md.txt)
  content/paginas/*.md       de pagina's onder Club (gedragscode, geschiedenis, ...)
"""
import datetime as dt
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
CONTENT = os.path.join(ROOT, 'content')
VANDAAG = dt.date.today()
NIEUWS_MAANDEN = 4

SITE = json.load(open(os.path.join(CONTENT, 'site.json'), encoding='utf-8'))
SPONSORDATA = json.load(open(os.path.join(CONTENT, 'sponsors.json'), encoding='utf-8'))
SPONSORS = SPONSORDATA['sponsors']
MAANDEN = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december']


def e(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- markdown
def inline(t):
    t = e(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    return t


def markdown(tekst):
    uit = []
    for blok in re.split(r'\n\s*\n', tekst.strip()):
        regels = [r for r in blok.strip().split('\n') if r.strip()]
        if not regels:
            continue
        if regels[0].startswith('## '):
            uit.append('<h2>%s</h2>' % inline(regels[0][3:]))
            regels = regels[1:]
            if not regels:
                continue
        if all(re.match(r'\d+\.\s', r) for r in regels):
            uit.append('<ol>%s</ol>' % ''.join('<li>%s</li>' % inline(re.sub(r'^\d+\.\s', '', r)) for r in regels))
        elif all(r.startswith('- ') for r in regels):
            uit.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(r[2:]) for r in regels))
        else:
            uit.append('<p>%s</p>' % '<br>'.join(inline(r) for r in regels))
    return '\n'.join(uit)


def lees_md(pad):
    tekst = open(pad, encoding='utf-8').read()
    meta = {}
    m = re.match(r'---\n(.*?)\n---\n?(.*)', tekst, re.S)
    if m:
        for regel in m.group(1).split('\n'):
            if ':' in regel:
                k, w = regel.split(':', 1)
                meta[k.strip()] = w.strip()
        tekst = m.group(2)
    meta['concept'] = meta.get('concept', '').lower() == 'true'
    meta['body'] = tekst
    return meta


def datum_nl(d):
    return '%d %s %d' % (d.day, MAANDEN[d.month - 1], d.year)


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# ---------------------------------------------------------------- inhoud
def laad_nieuws():
    items = []
    map_ = os.path.join(CONTENT, 'nieuws')
    grens = VANDAAG - dt.timedelta(days=NIEUWS_MAANDEN * 31)
    for f in sorted(os.listdir(map_), reverse=True):
        if not f.endswith('.md') or f.startswith('_'):
            continue
        m = lees_md(os.path.join(map_, f))
        d = dt.date.fromisoformat(m['datum'])
        if d < grens:
            continue
        m['date'] = d
        m['slug'] = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', f[:-3])
        m['url'] = '/nieuws/%s/' % m['slug']
        items.append(m)
    items.sort(key=lambda x: x['date'], reverse=True)
    return items


def laad_paginas():
    res = []
    map_ = os.path.join(CONTENT, 'paginas')
    for f in sorted(os.listdir(map_)):
        if f.endswith('.md'):
            m = lees_md(os.path.join(map_, f))
            m['slug'] = f[:-3]
            m['url'] = '/club/%s/' % m['slug']
            m['volgorde'] = int(m.get('volgorde', 9))
            res.append(m)
    return res


NIEUWS = laad_nieuws()
PAGINAS = laad_paginas()


# ---------------------------------------------------------------- layout
NAV = [('Nieuws', '/nieuws/'), ('Wedstrijden', '/wedstrijden/'), ('Teams', '/teams/'), ('DC DVSA', '/dc-dvsa/'),
       ('Club', '/club/'), ('Sponsoren', '/sponsoren/'), ('Contact', '/contact/')]


def sponsor_tegel(s, cls='', extra=''):
    licht = s['achtergrond'].lower() in ('#ffffff', '#fff')
    inner = '<img src="%s" alt="%s" loading="lazy">' % (e(s['logo']), e(s['naam']))
    stijl = 'background:%s' % s['achtergrond']
    c = (cls + (' licht' if licht else '')).strip()
    if s['website']:
        return '<a class="%s" href="%s" target="_blank" rel="noopener" title="%s" style="%s"%s>%s</a>' % (c, e(s['website']), e(s['naam']), stijl, extra, inner)
    return '<div class="%s" title="%s" style="%s"%s>%s</div>' % (c, e(s['naam']), stijl, extra, inner)


def layout(titel, inhoud, actief=None, beschrijving='', melding=False, scripts=('site',)):
    nav = ''.join('<a href="%s"%s>%s</a>' % (u, ' aria-current="page"' if n == actief else '', n) for n, u in NAV)
    nav += '<a class="knop-lid" href="/lid-worden/"%s>Lid worden</a>' % (' aria-current="page"' if actief == 'Lid worden' else '')
    mel = ''
    if melding and SITE['melding'].get('aan'):
        m = SITE['melding']
        mel = '<div class="melding"><div class="wrap"><span>%s</span><a class="knop" href="%s">%s</a></div></div>' % (m['tekst'], e(m['link']), e(m['knop']))
    boot = next((s for s in SPONSORS if s['naam'] == 'Bootsystems'), None)
    clubp = [p for p in PAGINAS if p['slug'] in ('organisatie', 'gedragscode', 'vertrouwenscontactpersoon')]
    voet = '''<footer class="voet"><div class="wrap">
<div class="voet-raster">
<div><div class="logo"><img src="/img/dvsa-logo.png" alt=""></div>{sportpark}<br>{adres}<br>{pc}</div>
<div><b>Contact</b><a href="mailto:{email}">{email}</a><a href="/contact/">Route en contact</a></div>
<div><b>Club</b><a href="/club/organisatie/">Organisatie</a><a href="/club/gedragscode/">Veilig sporten</a><a href="/vrijwilligers/">Vrijwilligers</a><a href="/club/club-van-100/">Club van 100</a><a href="/club/privacyverklaring/">Privacy</a></div>
<div><b>Volg ons</b><a href="{fb}">Facebook</a><a href="{ig}">Instagram</a><a href="{wa}">WhatsApp-kanaal</a></div>
</div>
<div class="voet-onder"><span style="opacity:.75">© DVSA · opgericht 1945 · Programma, uitslagen en standen via Sportlink</span>
<a class="host" href="https://www.bootsystems.nl/"><span style="opacity:.85">Website gehost door</span><span class="wit"><img src="{bootlogo}" alt="Bootsystems"></span></a></div>
</div></footer>'''.format(sportpark=e(SITE['sportpark']), adres=e(SITE['adres']), pc=e(SITE['postcode_plaats']), email=e(SITE['email']),
                           fb=e(SITE['facebook']), ig=e(SITE['instagram']), wa=e(SITE['whatsapp']), bootlogo=e(boot['logo'] if boot else ''))
    js = ''.join('<script src="/js/%s.js" defer></script>' % s for s in scripts)
    return '''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titel}</title>
<meta name="description" content="{besch}">
<meta property="og:title" content="{titel}">
<meta property="og:description" content="{besch}">
<meta property="og:image" content="/img/header-team.jpg">
<link rel="icon" href="/img/dvsa-logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<a class="sr" href="#inhoud">Naar de inhoud</a>
{mel}
<header class="kop"><div class="wrap">
<a class="merk" href="/"><span class="logo"><img src="/img/dvsa-logo.png" alt="DVSA logo"></span><span><b>DVSA</b><small>Door Vriendschap Sterk Amerongen</small></span></a>
<button class="menuknop" aria-label="Menu" aria-expanded="false" aria-controls="hoofdmenu"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
<nav class="nav" id="hoofdmenu" aria-label="Hoofdmenu">{nav}</nav>
</div></header>
<main id="inhoud">
{inhoud}
</main>
{voet}
{js}
</body>
</html>
'''.format(titel=e(titel), besch=e(beschrijving or 'Voetbalvereniging DVSA (Door Vriendschap Sterk Amerongen) op Sportpark De Burgwal in Amerongen.'),
           mel=mel, nav=nav, inhoud=inhoud, voet=voet, js=js)


def hero(titel, tekst, extra='', donker=False, terug=('/', '← Terug naar home')):
    return '''<section class="hero{d}"><div class="wrap"><div><a class="terug" href="{tu}">{tt}</a><h1>{t}</h1><p>{p}</p></div>{x}</div></section>'''.format(
        d=' donker' if donker else '', tu=terug[0], tt=terug[1], t=titel, p=tekst, x=extra)


def schrijf(pad, inhoud):
    vol = os.path.join(DIST, pad.strip('/'), 'index.html') if not pad.endswith('.html') else os.path.join(DIST, pad.strip('/'))
    os.makedirs(os.path.dirname(vol), exist_ok=True)
    open(vol, 'w', encoding='utf-8').write(inhoud)


def kantine_kaart():
    rijen = ''.join('<div class="kantine-rij"><span>%s</span><span class="%s" style="font-weight:600">%s</span></div>' % (d, 'dicht' if t == 'Gesloten' else '', t) for d, t in SITE['kantine'])
    return '<div class="kaart"><span class="label">Kantine</span><span class="groot" style="margin:6px 0 10px">Openingstijden</span>%s</div>' % rijen


def nieuws_kaart(n, h='h3'):
    cat = slugify(n.get('categorie', ''))
    foto = '<div class="nieuws-foto" style="background-image:url(%s)"></div>' % e(n['foto']) if n.get('foto') else '<div class="nieuws-foto"><img src="/img/dvsa-logo.png" alt=""></div>'
    return '''<a class="nieuws-kaart" href="{u}" data-cat="{c}">{f}<div class="nieuws-body"><div class="meta"><span class="cat {cs}">{c}</span><span>{d}</span></div><{h}>{t}</{h}><p>{i}</p></div></a>'''.format(
        u=n['url'], c=e(n.get('categorie', '')), cs=cat, f=foto, d=datum_nl(n['date']), t=e(n['titel']), i=e(n.get('intro', '')), h=h)


SL = '<span class="badge-sl">Automatisch uit Sportlink</span>'


# ---------------------------------------------------------------- pagina's
def home():
    sp = {s['naam']: s for s in SPONSORS}
    gb = sp['Goed-Bouw Bouwaannemers']
    collage_namen = ['Davelaar Sport', 'Bootsystems', 'Technivorm Moccamaster', 'Jumbo Amerongen', 'Plus Leersum', 'Volvo Reede', 'Schimmel Bouwbedrijf']
    collage = '<a class="hoofd" href="%s" target="_blank" rel="noopener" style="background:#161617"><span>Hoofdsponsor</span><img src="%s" alt="%s"></a>' % (e(gb['website']), e(gb['logo']), e(gb['naam']))
    collage += sponsor_tegel(sp['ING'], 'breed')
    for i, n in enumerate(collage_namen):
        collage += sponsor_tegel(sp[n], 'klein-weg' if i >= 4 else '')
    rest = [s for s in SPONSORS if s['naam'] not in collage_namen + ['Goed-Bouw Bouwaannemers', 'ING']]
    muur = ''.join(sponsor_tegel(s) for s in rest)
    m = SITE['melding']
    dias = '''<div class="dia actief"><img src="/img/header-team.jpg" alt="Jeugdspelers en trainers van DVSA met Football Makes It Happen"></div>
<div class="dia"><div class="collage">{collage}</div></div>
<div class="dia"><div class="logomuur"><div class="logomuur-kop"><b>Samen maken we DVSA mogelijk</b><a href="/sponsoren/" style="font-weight:700;color:var(--geel)">Alle sponsoren →</a></div><div class="logomuur-raster">{muur}</div></div></div>
<div class="dia"><div class="actie-dia"><div><span class="tag">Grote Clubactie</span><h2>Steun DVSA,<br>koop een lot</h2><p>85% van elk lot gaat rechtstreeks naar de club.</p><a class="btn btn-geel btn-groot" href="{link}">Koop een lot</a></div><img src="/img/clubactie.jpg" alt="Poster Grote Clubactie"></div></div>'''.format(collage=collage, muur=muur, link=e(m['link']))
    n_dia = 4
    stippen = ''.join('<button aria-label="Dia %d"><span></span></button>' % (i + 1) for i in range(n_dia))
    chips = ''.join(sponsor_tegel(s, 'chip') for s in SPONSORS) * 2
    nieuws = ''.join(nieuws_kaart(n) for n in NIEUWS[:4])
    mini = ''.join(sponsor_tegel(s) for s in SPONSORS if s['naam'] not in ('Goed-Bouw Bouwaannemers', 'ING'))
    ing = sp['ING']
    inhoud = '''
<section class="carrousel" aria-roledescription="carrousel" aria-label="Uitgelicht">
{dias}
<button class="car-knop vorige" aria-label="Vorige"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg></button>
<button class="car-knop volgende" aria-label="Volgende"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg></button>
<div class="stippen">{stippen}</div>
</section>

<section class="lint" aria-label="Onze sponsoren"><span class="lint-label">Onze sponsoren</span><div class="lint-baan"><div class="lint-rij">{chips}</div></div></section>

<section class="wedstrijd-band"><div class="wrap raster zij">
<div class="volgende" data-sl="volgende" data-team="{team}">
<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap"><span class="label" style="color:#fff;font-family:var(--cond);font-size:18px">Volgende wedstrijd · {team}</span><span class="badge-sl" style="background:rgba(255,255,255,.16);color:#fff">Automatisch uit Sportlink</span></div>
<div class="teams-vs">
<div class="team"><div class="embleem" data-veld="embleem-thuis"></div><b data-veld="thuis">{team}</b></div>
<div><div class="tijd" data-veld="tijd">··:··</div><div style="font-weight:600;font-size:18px;margin-top:6px" data-veld="dag">Laden…</div><div style="font-size:15px;opacity:.8" data-veld="plek"></div></div>
<div class="team"><div class="embleem" data-veld="embleem-uit"></div><b data-veld="uit">&nbsp;</b></div>
</div>
<div data-veld="foutplek"></div>
<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-wit" href="/wedstrijden/">Volledig programma</a><a class="btn btn-rand" href="/teams/">Alle teams</a></div>
</div>
<div class="stapel">
<div class="kaart"><span class="label">Laatste uitslag · {team}</span><div data-sl="laatste-uitslag" data-team="{team}" style="margin-top:12px;color:var(--tekst)"><p class="laden">Laden…</p></div></div>
<div class="kaart" style="color:var(--tekst)"><span class="label">Snel naar</span><div style="margin-top:6px">
<a class="lijst-link" href="/wedstrijden/"><span>Programma deze week</span><span>→</span></a>
<a class="lijst-link" href="/wedstrijden/#programma"><span>Afgelastingen</span><span>→</span></a>
<a class="lijst-link" href="/teams/"><span>Mijn team</span><span>→</span></a>
<a class="lijst-link" href="/contact/"><span>Route naar De Burgwal</span><span>→</span></a></div></div>
</div>
</div></section>

<section class="sectie"><div class="wrap">
<div class="sectie-kop"><div><h2>Onze jeugd</h2><p>De uitslagen van de jeugdteams van afgelopen week.</p></div><a class="link" href="/wedstrijden/#uitslagen">Alle uitslagen →</a></div>
<div class="raster zij">
<div class="kaart"><div data-sl="uitslagen" data-soort="jeugd" data-max="8"><p class="laden">Laden…</p></div></div>
<div class="navy-kaart" id="kabouters"><span class="label geel">Kabouters · 3 t/m 7 jaar</span><span class="groot" style="font-size:34px;margin:10px 0">Elke zaterdag 9:00 – 10:00 lekker ballen op De Burgwal</span><p style="opacity:.88;margin:0 0 18px">Vrijblijvend kennismaken met voetbal. Spelenderwijs dribbelen, passen en scoren, plezier staat voorop.</p><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn btn-geel" href="mailto:info@dvsa.nl?subject=Aanmelden%20kabouters">Aanmelden voor kabouters</a><a class="btn btn-rand" href="/lid-worden/">Lid worden</a></div></div>
</div></div></section>

<section class="sectie"><div class="wrap raster zij">
<div><div class="sectie-kop"><h2>Clubnieuws</h2><a class="link" href="/nieuws/">Alle berichten →</a></div><div class="raster r2">{nieuws}</div></div>
<div class="kaart"><div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px"><span class="groot">Stand {team}</span><span style="font-size:14px;color:var(--grijs)" data-veld="klasse"></span></div><div data-sl="stand" data-team="{team}"><p class="laden">Laden…</p></div></div>
</div></section>

<section class="sectie"><div class="wrap"><div class="kaart">
<div class="sectie-kop" style="margin-bottom:6px"><div><h2>Zaterdag op De Burgwal</h2><p>Alle thuiswedstrijden van deze week.</p></div>{sl}</div>
<div data-sl="programma" data-thuis="ja"><p class="laden">Laden…</p></div>
<a class="link" href="/wedstrijden/" style="display:inline-block;margin-top:14px">Ook de uitwedstrijden →</a>
</div></div></section>

<section class="sectie"><div class="wrap">
<div class="sectie-kop"><h2>Onze sponsoren</h2><div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap"><a class="link" href="/sponsoren/">Alle sponsoren →</a><a class="btn btn-geel" href="mailto:info@dvsa.nl?subject=Sponsor%20worden">Sponsor worden →</a></div></div>
<div class="raster" style="grid-template-columns:minmax(0,3fr) minmax(0,2fr)">
<a href="{gbu}" target="_blank" rel="noopener" style="height:220px;background:#161617;border-radius:var(--r);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border:2px solid var(--blauw);padding:20px"><span class="label" style="color:#BFC6D4">Hoofdsponsor</span><img src="{gbl}" alt="Goed-Bouw Bouwaannemers" style="width:min(460px,90%);height:120px;object-fit:contain"></a>
<a href="{ingu}" target="_blank" rel="noopener" style="height:220px;background:#fff;border-radius:var(--r);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border:2px solid var(--blauw);padding:20px"><span class="label blauw">Partner</span><img src="{ingl}" alt="ING" style="width:min(300px,90%);height:100px;object-fit:contain"></a>
</div>
<div class="sp-mini" style="margin-top:16px">{mini}</div>
</div></section>

<section class="sectie"><div class="wrap"><div class="kaart" style="display:flex;justify-content:space-between;align-items:center;gap:32px;flex-wrap:wrap;border:1px solid var(--lijn)">
<div style="max-width:640px"><span class="label blauw">WhatsApp-kanaal</span><h2 style="font-size:clamp(30px,4vw,44px);margin:8px 0">Volg DVSA op WhatsApp</h2><p class="tekst-2" style="margin:0 0 18px">Afgelastingen, uitslagen en clubnieuws direct op je telefoon. Scan de code of klik op de knop.</p><a class="btn btn-blauw" href="{wa}">Volg het kanaal</a></div>
<img src="/img/whatsapp-qr.png" alt="QR-code voor het WhatsApp-kanaal van DVSA" style="width:170px;height:170px;border-radius:12px;border:1px solid var(--lijn)">
</div></div></section>
'''.format(dias=dias, stippen=stippen, chips=chips, team=e(SITE['sportlink_eerste_elftal']), nieuws=nieuws, sl=SL, mini=mini,
           gbu=e(gb['website']), gbl=e(gb['logo']), ingu=e(ing['website']), ingl=e(ing['logo']), wa=e(SITE['whatsapp']))
    # grid op smalle schermen
    inhoud = inhoud.replace('grid-template-columns:minmax(0,3fr) minmax(0,2fr)', 'grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))')
    schrijf('/', layout('DVSA – Door Vriendschap Sterk Amerongen', inhoud, melding=True, scripts=('site', 'sportlink')))


def nieuws_paginas():
    cats = ['Alles', 'DVSA 1', 'Jeugd', 'DC DVSA', 'Club']
    knoppen = ''.join('<button role="tab" aria-selected="%s" data-filter="%s">%s</button>' % ('true' if c == 'Alles' else 'false', c, c) for c in cats)
    kaarten = ''.join(nieuws_kaart(n) for n in NIEUWS)
    inhoud = hero('Nieuws', 'Wedstrijdverslagen, jeugdnieuws en alles wat er rond De Burgwal gebeurt. Hier staan de berichten van de afgelopen vier maanden.')
    inhoud += '''<section class="sectie"><div class="wrap">
<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:28px"><div class="tabs" data-nieuwsfilter style="margin:0">{k}</div><span id="nieuws-teller" style="color:var(--grijs)">{n} berichten</span></div>
<div class="raster r3">{kaarten}</div>
<div id="nieuws-leeg" class="kaart" hidden style="text-align:center;border:1px dashed #C5CDDB"><span class="groot">Nog geen berichten in deze categorie</span><p class="tekst-2">Trainers en ouders: stuur een kort verslag of een leuke foto van jullie team in, dan zetten we het hier.</p><a class="btn btn-blauw" href="mailto:info@dvsa.nl?subject=Nieuwsbericht%20voor%20de%20website">Stuur een bericht in</a></div>
<p class="kaart" style="margin-top:32px;font-size:15px;color:var(--tekst-2);border:1px solid var(--lijn)">Berichten ouder dan vier maanden verdwijnen automatisch van deze pagina. Heb je zelf een verslag of nieuwtje? Mail het naar <a class="link" href="mailto:info@dvsa.nl">info@dvsa.nl</a>.</p>
</div></section>'''.format(k=knoppen, n=len(NIEUWS), kaarten=kaarten)
    schrijf('/nieuws/', layout('Nieuws – DVSA', inhoud, 'Nieuws'))
    for n in NIEUWS:
        score = ''
        if n.get('uitslag'):
            th, sc, ui = [x.strip() for x in n['uitslag'].split('|')]
            score = '<div class="scorebalk" style="margin-top:28px"><div style="text-align:right"><b>%s</b></div><span class="score">%s</span><div><b>%s</b><div style="font-size:14px;opacity:.85">%s</div></div></div>' % (e(th), e(sc), e(ui), e(n.get('doelpunten', '')))
        meer = ''.join(['<a href="%s" style="display:block;padding:12px 0;border-top:1px solid var(--lijn-2)"><span style="font-size:13px;color:var(--grijs);font-weight:600">%s · %s</span><br><b style="font-family:var(--cond);font-size:21px">%s</b></a>' % (x['url'], e(x['categorie']), datum_nl(x['date']), e(x['titel'])) for x in NIEUWS if x is not n][:3])
        foto = '<img src="%s" alt="" style="width:100%%;border-radius:20px;margin-bottom:24px">' % e(n['foto']) if n.get('foto') else ''
        concept = '<div class="concept">Dit bericht wordt nog overgezet van de oude site.</div>' if n['concept'] else ''
        inhoud = '''<section class="sectie" style="padding-top:40px"><div class="wrap">
<div class="meta" style="font-size:15px"><a class="link" href="/nieuws/">← Alle nieuws</a><span class="cat {cs}">{c}</span><span>{d}</span></div>
<h1 style="font-size:clamp(40px,6vw,72px);margin:14px 0 12px;line-height:.95">{t}</h1>
<p style="font-size:clamp(18px,2vw,22px);color:var(--tekst-2);max-width:900px;margin:0">{i}</p>
{score}
</div></section>
<section class="sectie" style="padding-top:36px"><div class="wrap raster zij">
<article class="kaart artikel">{concept}{foto}{body}
<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;border-top:1px solid var(--lijn);padding-top:22px;margin-top:10px;font-size:16px"><b>Deel dit bericht</b>
<a class="btn btn-rand" style="padding:8px 16px;text-decoration:none" href="https://wa.me/?text={wt}">WhatsApp</a>
<a class="btn btn-rand" style="padding:8px 16px;text-decoration:none" href="https://www.facebook.com/sharer/sharer.php?u=https://www.dvsa.nl{u}">Facebook</a></div>
</article>
<aside class="stapel">
<div class="kaart"><span class="groot" style="font-size:24px;margin-bottom:6px">Meer nieuws</span>{meer}<a class="link" href="/nieuws/" style="display:block;margin-top:10px">Alle nieuws →</a></div>
<a class="navy-kaart" href="{wa}"><span class="groot">Nooit meer een verslag missen?</span><p style="opacity:.88;margin:8px 0">Volg het WhatsApp-kanaal van DVSA.</p><b style="color:var(--geel)">Volg het kanaal →</b></a>
</aside>
</div></section>'''.format(cs=slugify(n['categorie']), c=e(n['categorie']), d=datum_nl(n['date']), t=e(n['titel']), i=e(n.get('intro', '')),
                            score=score, concept=concept, foto=foto, body=markdown(n['body']), wt=e(n['titel'] + ' https://www.dvsa.nl' + n['url']).replace(' ', '%20'),
                            u=n['url'], meer=meer, wa=e(SITE['whatsapp']))
        schrijf(n['url'], layout('%s – DVSA' % n['titel'], inhoud, 'Nieuws', n.get('intro', '')))


def wedstrijden():
    tabs = [('programma', 'Programma'), ('uitslagen', 'Uitslagen'), ('stand', 'Stand'), ('trainingen', 'Trainingen')]
    knoppen = ''.join('<button role="tab" id="tab-%s" data-naam="%s" aria-controls="paneel-%s" aria-selected="%s">%s</button>' % (k, k, k, 'true' if i == 0 else 'false', n) for i, (k, n) in enumerate(tabs))
    team = e(SITE['sportlink_eerste_elftal'])
    panelen = '''
<div role="tabpanel" id="paneel-programma" aria-labelledby="tab-programma"><div class="raster zij">
<div class="kaart"><div class="sectie-kop" style="margin-bottom:0"><h2 style="font-size:30px">Programma komende week</h2>{sl}</div><div data-sl="programma" data-dagen="7"><p class="laden">Laden…</p></div>
<p style="font-size:15px;color:var(--grijs);margin:14px 0 0">Verzameltijden en vertrektijden staan in de Voetbal.nl-app.</p></div>
<div class="stapel">
<div class="kaart" data-sl="afgelastingen" style="border-left:6px solid var(--groen)"><span class="label" style="color:inherit">Afgelastingen</span><span class="groot" data-veld="titel" style="margin:6px 0">Alles gaat door</span><div data-veld="lijst"></div><p class="tekst-2" style="font-size:15px;margin:8px 0">Afgelastingen verschijnen hier automatisch. Volg ook het WhatsApp-kanaal voor het laatste nieuws.</p><a class="link" href="{wa}">WhatsApp-kanaal →</a></div>
<div class="kaart"><span class="label">Kantine</span><span class="groot" style="margin:6px 0">Zaterdag open 08:00 – 20:00</span><p class="tekst-2" style="margin:0;font-size:15px">Kom gezellig langs voor een kop koffie langs de lijn.</p></div>
<a class="navy-kaart" href="/contact/"><span class="groot" style="font-size:24px">Route naar De Burgwal</span><p style="opacity:.85;margin:6px 0">{adres}, {pc}</p><b style="color:var(--geel)">Plan je route →</b></a>
</div></div></div>
<div role="tabpanel" id="paneel-uitslagen" aria-labelledby="tab-uitslagen" hidden><div class="kaart"><div class="sectie-kop" style="margin-bottom:0"><h2 style="font-size:30px">Uitslagen afgelopen week</h2>{sl}</div><div data-sl="uitslagen" data-soort="alles"><p class="laden">Laden…</p></div><p style="font-size:15px;color:var(--grijs);margin:14px 0 0">Scores vanuit DVSA gezien. Oudere uitslagen staan op de pagina van elk team.</p></div></div>
<div role="tabpanel" id="paneel-stand" aria-labelledby="tab-stand" hidden><div class="raster zij">
<div class="kaart"><div class="sectie-kop" style="margin-bottom:6px"><h2 style="font-size:30px">Stand {team}</h2><span data-veld="klasse" style="color:var(--grijs)"></span></div><div data-sl="stand" data-team="{team}"><p class="laden">Laden…</p></div></div>
<div class="kaart"><span class="label">Andere teams</span><p class="tekst-2">De stand van DVSA 2, de 45+ en alle jeugdteams staat op de pagina van elk team. Daar vind je ook de bekerstand.</p><a class="link" href="/teams/">Alle teams →</a></div>
</div></div>
<div role="tabpanel" id="paneel-trainingen" aria-labelledby="tab-trainingen" hidden><div class="kaart"><div class="sectie-kop" style="margin-bottom:8px"><h2 style="font-size:30px">Trainingsschema 2026/2027</h2><span class="badge-sl" style="background:#FFF4C7;color:#6B5300">Volgt binnenkort</span></div>
<p class="tekst-2" style="max-width:820px">Het nieuwe trainingsschema komt hier als tabel, zodat je het makkelijk op je telefoon kunt lezen. Tot die tijd hoor je de trainingstijden van je trainer of via de Voetbal.nl-app.</p></div></div>
'''.format(sl=SL, wa=e(SITE['whatsapp']), adres=e(SITE['adres']), pc=e(SITE['postcode_plaats']), team=team)
    inhoud = hero('Wedstrijden', 'Het programma, de uitslagen en de standen van alle DVSA-teams. Alles komt automatisch uit Sportlink, dus het klopt altijd.')
    inhoud += '<section class="sectie"><div class="wrap"><div class="tabs" role="tablist" aria-label="Wedstrijden">%s</div>%s</div></section>' % (knoppen, panelen)
    schrijf('/wedstrijden/', layout('Wedstrijden – DVSA', inhoud, 'Wedstrijden', scripts=('site', 'sportlink')))


def teams():
    inhoud = hero('Teams', 'Van kabouters tot de 45+: alle teams van DVSA op één plek. Klik op een team voor de staf, de selectie, het programma, de uitslagen en de stand.')
    inhoud += '''<div data-sl="teams">
<section class="sectie" style="padding-top:36px"><div class="wrap"><p class="kaart" style="margin:0;font-size:16px;color:var(--tekst-2);border:1px solid var(--lijn)">Deze lijst komt automatisch uit Sportlink. Begint er een nieuw team of verdwijnt er een, dan klopt deze pagina vanzelf.</p><div data-veld="foutplek"></div></div></section>
<section class="sectie"><div class="wrap"><div class="sectie-kop"><div><h2>Jeugd</h2><p data-veld="aantal"></p></div></div><div class="team-raster" data-veld="jeugd"><p class="laden">Laden…</p></div></div></section>
<section class="sectie"><div class="wrap"><div class="sectie-kop"><h2>Senioren</h2></div><div class="team-raster" data-veld="senioren"></div></div></section>
</div>
<section class="sectie"><div class="wrap"><div class="blok-blauw"><div><h2>Ook komen voetballen?</h2><p>Jongens en meiden van alle leeftijden zijn welkom. Je mag eerst drie keer gratis meetrainen om te kijken of het bevalt.</p></div><a class="btn btn-geel btn-groot" href="/lid-worden/">Lid worden</a></div></div></section>'''
    schrijf('/teams/', layout('Teams – DVSA', inhoud, 'Teams', scripts=('site', 'sportlink')))
    # teampagina (één pagina, gevuld via de adresbalk)
    inhoud = '''<section class="hero"><div class="wrap"><div><a class="terug" href="/teams/">← Alle teams</a><h1 data-veld="teamnaam">Team</h1><p>Staf, selectie, programma, uitslagen en stand. Alles komt automatisch uit Sportlink.</p></div></div></section>
<section class="sectie" data-sl="team"><div class="wrap raster zij">
<div class="stapel">
<div class="kaart"><div class="sectie-kop" style="margin-bottom:0"><h2 style="font-size:28px">Programma</h2>{sl}</div><div data-sl="programma" data-dagen="28" data-team-uit-url><p class="laden">Laden…</p></div></div>
<div class="kaart"><h2 style="font-size:28px;margin-bottom:6px">Uitslagen</h2><div data-sl="uitslagen" data-dagen="60" data-team-uit-url><p class="laden">Laden…</p></div></div>
<div class="kaart"><div style="display:flex;justify-content:space-between;align-items:baseline"><h2 style="font-size:28px">Stand</h2><span data-veld="klasse" style="color:var(--grijs);font-size:15px"></span></div><div data-sl="stand" data-team-uit-url><p class="laden">Laden…</p></div></div>
</div>
<div class="stapel">
<div class="kaart"><h2 style="font-size:28px;margin-bottom:6px">Staf</h2><div data-veld="staf"><p class="laden">Laden…</p></div></div>
<div class="kaart"><div style="display:flex;justify-content:space-between;align-items:baseline"><h2 style="font-size:28px">Selectie</h2><span data-veld="aantal" style="color:var(--grijs)"></span></div><div data-veld="selectie" style="margin-top:8px"><p class="laden">Laden…</p></div>
</div>
</div>
</div></section>'''.format(sl=SL)
    schrijf('/teams/team/', layout('Team – DVSA', inhoud, 'Teams', scripts=('site', 'sportlink')))


def dc_dvsa():
    bord = '<svg width="260" height="260" viewBox="0 0 100 100" aria-hidden="true" style="max-width:40vw;height:auto"><circle cx="50" cy="50" r="48" fill="#0E1A33" stroke="#FFD21F" stroke-width="2"/><circle cx="50" cy="50" r="38" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="6"/><circle cx="50" cy="50" r="26" fill="none" stroke="#FFD21F" stroke-width="3"/><circle cx="50" cy="50" r="15" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="5"/><circle cx="50" cy="50" r="5" fill="#FFD21F"/></svg>'
    dc = [n for n in NIEUWS if n.get('categorie') == 'DC DVSA'][:4]
    versl = ''.join('<a href="%s" style="display:block;padding:10px 0;border-top:1px solid var(--lijn-2)"><span style="font-size:13px;color:var(--grijs);font-weight:600">%s</span><br><b style="font-family:var(--cond);font-size:20px">%s</b></a>' % (n['url'], datum_nl(n['date']), e(n['titel'])) for n in dc) or '<p class="laden">Nog geen verslagen.</p>'
    inhoud = hero('DC DVSA', 'De dartsclub van DVSA. Sinds het seizoen 2023-2024 gooien we elke vrijdagavond in de kantine op De Burgwal, in competitie en gewoon voor de gezelligheid.', bord, donker=True)
    inhoud += '''<section class="sectie"><div class="wrap raster r3">
<div class="kaart"><span class="label blauw">Wanneer</span><span class="groot" style="font-size:32px;margin:6px 0">Vrijdagavond</span><p class="tekst-2" style="margin:0">Vanaf 19:00 is de kantine open en staan de borden klaar.</p></div>
<div class="kaart"><span class="label blauw">Waar</span><span class="groot" style="font-size:32px;margin:6px 0">Kantine DVSA</span><p class="tekst-2" style="margin:0">{sp}, {adres} in Amerongen. Gewoon binnenlopen.</p></div>
<div class="kaart"><span class="label blauw">Competitie</span><span class="groot" style="font-size:32px;margin:6px 0">Seizoen 2026/2027</span><p class="tekst-2" style="margin:0">DC DVSA speelt in de regionale competitie. De stand komt hier uit TeamBeheer.</p></div>
</div></section>
<section class="sectie"><div class="wrap raster zij">
<div class="kaart"><span class="groot">Verslagen</span>{versl}<a class="link" href="/nieuws/" style="display:block;margin-top:10px">Alle dartsverslagen →</a>
<div style="border-top:2px solid var(--lijn);margin-top:18px;padding-top:16px"><span class="groot" style="font-size:24px">Stand</span><p class="tekst-2" style="font-size:15px">De actuele stand van seizoen 2026/2027 komt hier, rechtstreeks uit TeamBeheer.</p></div></div>
<div class="geel-kaart"><span class="groot">Zin om mee te gooien?</span><p style="margin:10px 0 16px">Beginner of ervaren: iedereen is welkom. Kom gerust eens kijken op vrijdagavond.</p><a class="btn" style="background:var(--navy);color:#fff" href="mailto:info@dvsa.nl?subject=Meedoen%20met%20DC%20DVSA">Mail de club</a></div>
</div></section>'''.format(sp=e(SITE['sportpark']), adres=e(SITE['adres']), versl=versl)
    schrijf('/dc-dvsa/', layout('DC DVSA – dartsclub van DVSA', inhoud, 'DC DVSA'))


def club():
    feiten = [('1945', 'opgericht op 27 juli'), ('2', 'velden: hoofdveld kunstgras, tweede veld natuurgras'), ('18', 'teams, van kabouters tot 45+'), (str(len(SPONSORS)), 'sponsoren uit de regio')]
    groepen = {}
    for p in sorted(PAGINAS, key=lambda x: x['volgorde']):
        groepen.setdefault(p['groep'], []).append(p)
    extra = {'Meedoen': [{'titel': 'Lidmaatschap en contributie', 'intro': 'Wat het kost en hoe je opzegt.', 'url': '/lid-worden/'},
                         {'titel': 'Vrijwilligers', 'intro': '10 punten per jaar of afkopen voor €100.', 'url': '/vrijwilligers/'}]}

    def lijst(g):
        items = extra.get(g, []) + groepen.get(g, [])
        return '<div class="kaart" style="padding:8px 28px">' + ''.join(
            '<a href="%s" style="display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;%s"><span><b style="font-family:var(--cond);font-size:22px">%s</b><br><span style="font-size:15px;color:var(--grijs)">%s</span></span><span style="color:var(--blauw);font-size:20px">→</span></a>'
            % (p['url'], 'border-top:1px solid var(--lijn-2)' if i else '', e(p['titel']), e(p.get('intro', ''))) for i, p in enumerate(items)) + '</div>'
    feit = ''.join('<div style="padding:24px 28px"><div class="feit">%s</div><div class="tekst-2">%s</div></div>' % (a, b) for a, b in feiten)
    vs = ''.join('<div><span class="groot" style="font-size:24px">%s</span><p class="tekst-2" style="font-size:16px">%s</p><a class="link" href="%s">%s →</a></div>' % x for x in [
        ('Gedragscode', 'Hoe we met elkaar omgaan op en naast het veld, voor spelers, trainers, ouders en vrijwilligers.', '/club/gedragscode/', 'Lees de gedragscode'),
        ('Vrijwilligersbeleid', 'Werving, VOG, begeleiding en evaluatie van iedereen die met jeugd werkt.', '/club/vrijwilligersbeleid/', 'Lees het beleid'),
        ('Vertrouwens&shy;contactpersoon', 'Iets vervelends meegemaakt of gezien? Elsbeth Kuus luistert, in vertrouwen.', 'mailto:vcp@dvsa.nl', 'Mail vcp@dvsa.nl')])
    inhoud = hero('De club', 'Door Vriendschap Sterk Amerongen: een dorpsclub waar iedereen welkom is en die draait op vrijwilligers. Hier vind je alles over hoe de club werkt.')
    inhoud += '''<section class="wrap" style="margin-top:-28px"><div class="kaart raster r4" style="padding:0;gap:0;box-shadow:0 8px 24px rgba(14,26,51,.08)">{feit}</div></section>
<section class="sectie"><div class="wrap raster" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));align-items:start">
<div><div class="sectie-kop"><h2>Vereniging</h2></div>{v}</div>
<div><div class="sectie-kop"><h2>Meedoen</h2></div>{m}</div>
<div style="padding-top:64px">{kantine}</div>
</div></section>
<section class="sectie"><div class="wrap"><div class="kaart" style="padding:0;overflow:hidden;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));border:2px solid var(--blauw)">
<div style="background:var(--blauw);color:#fff;padding:36px 40px"><span class="label geel">Veilig sporten</span><h2 style="font-size:40px;margin:10px 0">Iedereen moet zich veilig voelen bij DVSA</h2><p style="opacity:.9;margin:0">Spelers, ouders, trainers en vrijwilligers houden zich aan dezelfde afspraken.</p></div>
<div style="padding:32px 40px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:24px">{vs}</div>
</div></div></section>
<section class="sectie"><div class="wrap"><div class="kaart"><span class="groot" style="font-size:24px">Overig</span>{o}</div></div></section>'''.format(
        feit=feit, v=lijst('Vereniging'), m=lijst('Meedoen'), kantine=kantine_kaart(), vs=vs,
        o=''.join('<a class="link" style="display:block;margin-top:8px" href="%s">%s →</a>' % (p['url'], e(p['titel'])) for p in groepen.get('Overig', [])))
    schrijf('/club/', layout('De club – DVSA', inhoud, 'Club'))

    # subpagina's
    menu_groepen = [('Vereniging', groepen.get('Vereniging', [])),
                    ('Meedoen', [{'titel': 'Lidmaatschap', 'url': '/lid-worden/'}, {'titel': 'Vrijwilligers', 'url': '/vrijwilligers/'}] + groepen.get('Meedoen', [])),
                    ('Veilig sporten', groepen.get('Veilig sporten', [])), ('Overig', groepen.get('Overig', []))]
    for p in PAGINAS:
        menu = '<nav class="zijmenu" aria-label="Club">' + ''.join(
            '<span class="groep">%s</span>' % g + ''.join('<a href="%s"%s>%s</a>' % (x['url'], ' aria-current="page"' if x.get('url') == p['url'] else '', e(x['titel'])) for x in items)
            for g, items in menu_groepen) + '</nav>'
        koppen = re.findall(r'^## (.+)$', p['body'], re.M)
        body = markdown(p['body'])
        for k in koppen:
            body = body.replace('<h2>%s</h2>' % inline(k), '<h2 id="%s">%s</h2>' % (slugify(k), inline(k)), 1)
        inhoudsopg = ('<div class="kaart" style="padding:22px 26px"><span class="label">Op deze pagina</span>' + ''.join('<a href="#%s" style="display:block;padding:7px 0;border-top:1px solid var(--lijn-2);font-weight:600;font-size:15px;color:var(--tekst-2)">%s</a>' % (slugify(k), e(k)) for k in koppen) + '</div>') if len(koppen) > 2 else ''
        concept = '<div class="concept">Deze pagina wordt nog gevuld met de tekst van de oude site.</div>' if p['concept'] else ''
        inhoud = '''<section class="hero"><div class="wrap"><div><div class="kruimel"><a href="/club/">Club</a><span>›</span><span>{g}</span><span>›</span><span>{t}</span></div><h1>{t}</h1><p>{i}</p></div></div></section>
<section class="sectie"><div class="wrap club-raster">{menu}<article class="kaart artikel">{c}{body}</article>
<aside class="stapel"><div class="navy-kaart"><span class="label geel">Iets gezien of meegemaakt?</span><span class="groot" style="margin:8px 0">Praat met de vertrouwens&shy;contactpersoon</span><p style="opacity:.88;font-size:15px;margin:0 0 14px">Elsbeth Kuus luistert, in vertrouwen.</p><a class="btn btn-geel" href="mailto:vcp@dvsa.nl">vcp@dvsa.nl</a></div>{ih}</aside>
</div></section>'''.format(g=e(p['groep']), t=e(p['titel']), i=e(p.get('intro', '')), menu=menu, c=concept, body=body, ih=inhoudsopg)
        schrijf(p['url'], layout('%s – DVSA' % p['titel'], inhoud, 'Club', p.get('intro', '')))


def sponsoren():
    def kaart(s):
        tegel = sponsor_tegel(s, 'sp-tegel')
        naam = '<a class="sp-naam" href="%s" target="_blank" rel="noopener">%s</a>' % (e(s['website']), e(s['naam'])) if s['website'] else '<span class="sp-naam">%s</span>' % e(s['naam'])
        return '<div class="sp-kaart">%s%s</div>' % (tegel, naam)

    def sectie(titel, sub, groep):
        items = [s for s in SPONSORS if s['groep'] == groep]
        return '<section class="sectie"><div class="wrap"><div class="sectie-kop"><div><h2>%s</h2><p>%s</p></div></div><div class="sp-raster">%s</div></div></section>' % (titel, sub, ''.join(kaart(s) for s in items))
    gb = next(s for s in SPONSORS if s['groep'] == 'hoofd')
    partners = ''
    for s in [s for s in SPONSORS if s['groep'] == 'partner']:
        naam = '<a class="sp-naam" style="font-size:19px" href="%s" target="_blank" rel="noopener">%s</a>' % (e(s['website']), e(s['naam'])) if s['website'] else '<span class="sp-naam" style="font-size:19px">%s</span>' % e(s['naam'])
        partners += '<div class="sp-kaart" style="border:2px solid var(--blauw);border-radius:20px;padding:14px 14px 20px">%s%s<span style="font-size:15px;color:var(--grijs);padding:0 4px">%s</span></div>' % (sponsor_tegel(s, 'sp-tegel', ' style="height:150px"').replace('style="background', 'style="height:150px;background').replace(' style="height:150px">', '>'), naam, e(s.get('rol', '')))
    inhoud = hero('Onze sponsoren', 'DVSA draait op vrijwilligers én op ondernemers uit Amerongen en omgeving. Dankzij hen kunnen honderden kinderen en volwassenen elke week voetballen op De Burgwal. Klik op een naam om hun website te bezoeken.',
                  '<a class="btn btn-geel btn-groot" href="mailto:info@dvsa.nl?subject=Sponsor%20worden">Sponsor worden</a>')
    inhoud += '''<section class="sectie"><div class="wrap"><div class="sectie-kop"><div><h2>Hoofdsponsor</h2><p>Al jaren de grootste steun van de club.</p></div></div>
<div class="kaart" style="padding:0;overflow:hidden;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));border:2px solid var(--blauw)">
<a href="{u}" target="_blank" rel="noopener" style="min-height:240px;background:#161617;display:flex;align-items:center;justify-content:center;padding:32px"><img src="{l}" alt="Logo {n}" style="width:min(500px,100%);height:160px;object-fit:contain"></a>
<div style="padding:40px 48px;display:flex;flex-direction:column;justify-content:center;gap:12px"><span class="label blauw">Hoofdsponsor</span><a href="{u}" target="_blank" rel="noopener" class="groot" style="font-size:clamp(26px,4vw,34px);color:var(--blauw);text-decoration:underline;overflow-wrap:anywhere">{n}</a><p class="tekst-2" style="margin:0;font-size:18px">{r} Samen met Skilton houtskeletbouw bouwen ze mee aan de club.</p></div>
</div></div></section>
<section class="sectie"><div class="wrap"><div class="sectie-kop"><div><h2>Partners</h2><p>Sponsoren met een bijzondere rol binnen de club.</p></div></div><div class="raster r4">{p}</div></div></section>
{bord}{bal}{over}
<section class="sectie"><div class="wrap"><div class="kaart" style="display:flex;gap:32px;align-items:center;flex-wrap:wrap;border:1px solid var(--lijn)"><span class="groot" style="font-size:26px">Ook dank aan</span><span class="tekst-2" style="font-size:18px">{dank}</span></div></div></section>
<section class="sectie"><div class="wrap"><div class="blok-navy"><div><h2>Ook zichtbaar worden langs het veld?</h2><p>Een bord langs het hoofdveld, een balsponsoring of een vermelding op de website: er is altijd een vorm die bij jouw bedrijf past.</p></div><a class="btn btn-geel btn-groot" href="mailto:info@dvsa.nl?subject=Sponsor%20worden">Mail de club</a></div></div></section>'''.format(
        u=e(gb['website']), l=e(gb['logo']), n=e(gb['naam']), r=e(gb.get('rol', '')), p=partners,
        bord=sectie('Bordsponsoren', 'Hun reclamebord staat langs de velden van sportpark De Burgwal.', 'bord'),
        bal=sectie('Balsponsoren', 'Zij zorgen dat er elke wedstrijd met een goede bal gespeeld wordt.', 'bal'),
        over=sectie('Overige sponsoren', 'Met een spandoek, korting, materiaal of een andere bijdrage.', 'overig'),
        dank=' · '.join(e(x) for x in SPONSORDATA.get('ook_dank_aan', [])))
    schrijf('/sponsoren/', layout('Sponsoren – DVSA', inhoud, 'Sponsoren'))


def contact():
    mails = ''.join('<a class="kaart" href="mailto:%s" style="border:1px solid var(--lijn);display:block"><span class="label blauw">%s</span><span class="groot" style="font-size:22px;margin:6px 0;word-break:break-word">%s</span><span class="tekst-2" style="font-size:15px">%s</span></a>' % (e(m['adres']), e(m['rol']), e(m['adres']), e(m['uitleg'])) for m in SITE['mailadressen'])
    mails += '<div class="kaart" style="background:var(--blauw);color:#fff"><span class="label geel">Langskomen</span><span class="groot" style="font-size:22px;margin:6px 0">Zaterdag in de kantine</span><span style="font-size:15px;opacity:.9">Kom gerust even langs. Op zaterdag is de kantine open van 08:00 tot 20:00.</span></div>'
    q = (SITE['adres'] + ' ' + SITE['postcode_plaats']).replace(' ', '+')
    inhoud = hero('Contact', 'Vragen over lid worden, een team, sponsoring of iets anders? Mail de juiste persoon of kom langs op zaterdag.')
    inhoud += '''<section class="sectie"><div class="wrap raster zij">
<div><div class="sectie-kop"><div><h2>Mail de club</h2><p>Elke mail komt bij de juiste persoon terecht.</p></div></div><div class="raster r2" style="gap:16px">{mails}</div></div>
<div class="stapel" style="padding-top:8px">
<div class="kaart"><span class="label">Bezoek- en postadres</span><span class="groot" style="margin:6px 0">{sp}</span><p class="tekst-2" style="margin:0 0 16px">{adres}<br>{pc}</p><a class="btn btn-blauw" href="https://www.google.com/maps/search/?api=1&amp;query={q}">Plan je route</a></div>
{kantine}
</div></div></section>
<section class="sectie"><div class="wrap"><div class="kaart" style="padding:0;overflow:hidden"><iframe title="Kaart Sportpark De Burgwal" src="https://www.google.com/maps?q={q}&amp;output=embed" style="width:100%;height:400px;border:0;display:block" loading="lazy"></iframe></div></div></section>
<section class="sectie"><div class="wrap"><div class="kaart" style="display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;border:1px solid var(--lijn)"><span class="groot">Volg DVSA</span><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn" style="background:var(--bg)" href="{fb}">Facebook</a><a class="btn" style="background:var(--bg)" href="{ig}">Instagram</a><a class="btn" style="background:var(--bg)" href="{wa}">WhatsApp-kanaal</a></div></div></div></section>'''.format(
        mails=mails, sp=e(SITE['sportpark']), adres=e(SITE['adres']), pc=e(SITE['postcode_plaats']), q=e(q), kantine=kantine_kaart(),
        fb=e(SITE['facebook']), ig=e(SITE['instagram']), wa=e(SITE['whatsapp']))
    schrijf('/contact/', layout('Contact – DVSA', inhoud, 'Contact'))


def lid_worden():
    cta = '<a class="btn btn-geel btn-groot" href="%s">Naar het aanmeldformulier</a>' % e(SITE['aanmeldformulier'])
    stappen = ''.join('<div class="kaart"><span class="stap">%s</span><span class="groot" style="margin:14px 0 8px">%s</span><p class="tekst-2" style="margin:0">%s</p></div>' % x for x in [
        ('1', 'Train 3 keer gratis mee', 'Eerst kijken of het bevalt? Je mag drie keer gratis meetrainen voordat je lid wordt. Mail info@dvsa.nl, dan zoeken we het juiste team.'),
        ('2', 'Vul het formulier in', 'Het aanmeldformulier gaat rechtstreeks naar onze ledenadministratie en de KNVB. Houd je IBAN bij de hand, en bij kinderen de gegevens van een ouder.'),
        ('3', 'Welkom bij de club', 'Je hoort van ons in welk team je speelt en wanneer je traint. De contributie betaal je via ClubCollect.')])
    contr = ''.join('<div class="rij" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr) 90px"><b>%s</b><span style="color:var(--grijs)">%s</span><span class="cijfer" style="text-align:right">%s</span></div>' % tuple(e(x) for x in r) for r in SITE['contributie'])
    inhoud = hero('Word lid van DVSA', 'Super dat je wilt komen voetballen! Jong of oud, beginner of ervaren: bij DVSA is iedereen welkom. Je mag eerst drie keer gratis meetrainen.', cta)
    inhoud += '''<section class="sectie"><div class="wrap raster r3">{stappen}</div></section>
<section class="sectie"><div class="wrap raster zij">
<div class="kaart"><div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px"><span class="groot" style="font-size:32px">Contributie</span><span style="color:var(--grijs);font-size:15px">Seizoen 2026/2027 · per jaar</span></div>{contr}
<p class="tekst-2" style="font-size:15px;margin:16px 0 0">Opzeggen kan tot 1 juni door een mail te sturen naar <a class="link" href="mailto:ledenadministratie@dvsa.nl">ledenadministratie@dvsa.nl</a>. Daarna loopt het lidmaatschap een jaar door.</p></div>
<div class="stapel">
<div class="navy-kaart" id="kabouters"><span class="label geel">Kabouters · 3 t/m 7 jaar</span><span class="groot" style="margin:10px 0">Elke zaterdag 9:00 – 10:00 lekker ballen</span><p style="opacity:.88;margin:0 0 16px">Vrijblijvend kennismaken met voetbal. Spelenderwijs dribbelen, passen en scoren, plezier staat voorop.</p><a class="btn btn-geel" href="mailto:info@dvsa.nl?subject=Aanmelden%20kabouters">Aanmelden voor kabouters</a></div>
<div class="kaart"><span class="label">Samen maken we de club</span><span class="groot" style="font-size:26px;margin:6px 0">Vrijwilligerstaken</span><p class="tekst-2" style="font-size:15px">Elk lid doet 10 punten per jaar; een punt staat voor een uur helpen. Je plant je taken zelf in via de Voetbal.nl-app. Afkopen kan ook, voor €100 per jaar.</p><a class="link" href="/vrijwilligers/">Hoe het werkt →</a></div>
</div></div></section>
<section class="sectie"><div class="wrap"><div class="blok-blauw"><div><h2>Klaar om te beginnen?</h2><p>Vragen over het aanmelden? Mail ledenadministratie@dvsa.nl.</p></div>{cta}</div></div></section>'''.format(stappen=stappen, contr=contr, cta=cta)
    schrijf('/lid-worden/', layout('Lid worden – DVSA', inhoud, 'Lid worden'))


def vrijwilligers():
    blokken = ''
    for n, t, d, hl in [('10', 'punten per jaar', 'Elk lid doet 10 punten per seizoen aan vrijwilligerstaken.', False),
                        ('1 uur', '= 1 punt', 'Elk uur dat je helpt, levert één punt op. Tien uur per jaar dus.', False),
                        ('€ 100', 'per jaar afkopen', 'Lukt het niet om te helpen? Dan kun je je punten afkopen voor €100 per jaar.', True)]:
        st = ' style="background:var(--blauw);color:#fff"' if hl else ''
        blokken += '<div class="kaart"%s><div class="feit"%s>%s</div><span class="groot" style="font-size:24px;text-transform:uppercase;margin:6px 0">%s</span><p style="margin:0;%s">%s</p></div>' % (st, ' style="color:#fff"' if hl else '', n, t, 'opacity:.9' if hl else 'color:var(--tekst-2)', d)
    stappen = ''.join('<div style="display:flex;gap:20px;align-items:flex-start;padding:20px 0;%s"><span class="stap">%s</span><span><span class="groot" style="font-size:26px">%s</span><span class="tekst-2">%s</span></span></div>' % ('border-top:1px solid var(--lijn-2)' if i else '', a, b, c) for i, (a, b, c) in enumerate([
        ('1', 'Open de Voetbal.nl-app', 'Alle vrijwilligerstaken van DVSA staan in de app, met datum, tijd en hoeveel punten ze opleveren.'),
        ('2', 'Kies een taak die past', 'Plan zelf in wanneer het jou uitkomt. Wie op tijd plant, heeft de meeste keus.'),
        ('3', 'Kom helpen en verdien je punten', 'Elk uur telt als één punt. Bij 10 punten zit je seizoen erop.')]))
    docs = ''.join('<div style="display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-top:1px solid var(--lijn-2);font-weight:600"><span>%s</span><span style="font-size:12px;background:var(--lichtblauw);color:var(--blauw);padding:3px 8px;border-radius:6px">PDF volgt</span></div>' % t for t in
                   ['Handleiding vrijwilligerstaken in de app', 'Beschrijving kantinedienst', 'Kleedkamers en toiletten schoonmaken', 'Gebruiksregels kunstgras'])
    inhoud = hero('Vrijwilligers', 'DVSA draait helemaal op vrijwilligers: achter de bar, langs de lijn en in de kleedkamers. Daarom helpt elk lid een paar uur per jaar mee.')
    inhoud += '''<section class="sectie"><div class="wrap raster r3">{blokken}</div></section>
<section class="sectie"><div class="wrap raster zij">
<div class="stapel"><div class="sectie-kop" style="margin:0"><div><h2>Zo plan je je taken in</h2><p>In drie stappen, helemaal via je telefoon.</p></div></div><div class="kaart" style="padding:8px 32px">{stappen}</div>
<div class="sectie-kop" style="margin:12px 0 0"><h2>Wat kun je doen?</h2></div>
<div class="raster r2"><div class="kaart"><span class="groot" style="font-size:26px">Kantinedienst</span><p class="tekst-2">Op zaterdag de kantine openen, achter de bar en de kassa staan en weer afsluiten.</p></div><div class="kaart"><span class="groot" style="font-size:26px">Kleedkamers schoonmaken</span><p class="tekst-2">De kleedkamers en toiletten netjes houden volgens de schoonmaakinstructie.</p></div></div>
<p class="tekst-2" style="margin:0">En meer: in de app zie je welke taken er openstaan.</p></div>
<div class="stapel"><div class="kaart"><span class="label">Handleidingen</span><span class="groot" style="margin:6px 0 8px">Downloads</span>{docs}</div>
<div class="geel-kaart"><span class="groot">Liever afkopen?</span><p style="margin:10px 0 16px">Voor €100 per jaar ben je klaar met je vrijwilligerspunten. Laat het weten aan de ledenadministratie.</p><a class="btn" style="background:var(--navy);color:#fff" href="mailto:ledenadministratie@dvsa.nl?subject=Vrijwilligerstaken%20afkopen">Mail de ledenadministratie</a></div></div>
</div></section>
<section class="sectie"><div class="wrap"><div class="blok-navy"><div><h2>Meer doen dan 10 uur?</h2><p>De club zoekt altijd mensen voor een vaste rol, zoals in een commissie of als leider van een team. Heb je zin om meer te betekenen, mail ons dan.</p></div><a class="btn btn-geel btn-groot" href="mailto:info@dvsa.nl?subject=Vaste%20vrijwilliger">Ik wil helpen</a></div></div></section>'''.format(blokken=blokken, stappen=stappen, docs=docs)
    schrijf('/vrijwilligers/', layout('Vrijwilligers – DVSA', inhoud, 'Club'))


def niet_gevonden():
    inhoud = hero('Pagina niet gevonden', 'Deze pagina bestaat niet (meer). Misschien stond hij op de oude website. Kijk in het menu of ga terug naar de homepage.', '<a class="btn btn-geel btn-groot" href="/">Naar de homepage</a>')
    schrijf('404.html', layout('Pagina niet gevonden – DVSA', inhoud))


def redirects():
    vast = [('/adres-route', '/contact/'), ('/club_aanmelden', '/lid-worden/'), ('/lidmaatschap-contributie', '/lid-worden/'),
            ('/programma', '/wedstrijden/'), ('/uitslagen', '/wedstrijden/#uitslagen'), ('/standen', '/nieuws/'),
            ('/vereniging', '/club/'), ('/accomodatie', '/club/'), ('/bestuursvergaderingen', '/club/'), ('/verantwoording-leden-maart-mei', '/club/'),
            ('/bestuursvergadering-9-04-2025', '/club/'), ('/samenwerking-rac-fc-utrecht', '/club/'), ('/demo-max', '/'), ('/test-pagina', '/nieuws/'),
            ('/verslagen-dvsa-1', '/nieuws/'), ('/verslagen-jo-13-1-jm', '/nieuws/'), ('/minis-kabouters-ve-zaterdag-gemengd', '/lid-worden/#kabouters')]
    for p in PAGINAS:
        if p.get('oud_adres'):
            vast.append((p['oud_adres'], p['url']))
    # nooit een regel die naar zichzelf wijst (voorkomt een doorverwijslus)
    vast = [(a, b) for a, b in vast if a.rstrip('/') != b.split('#')[0].rstrip('/')]
    for n in NIEUWS:
        if n.get('oud_adres'):
            vast.append((n['oud_adres'], n['url']))
    regels = ['# Oude adressen van de WordPress/Sportlink-site naar de nieuwe pagina\'s'] + ['%s %s 301' % (a, b) for a, b in vast]
    regels.append('/dvsa-* /teams/ 301')
    regels.append('/st-dvsa-* /teams/ 301')
    open(os.path.join(DIST, '_redirects'), 'w').write('\n'.join(regels) + '\n')


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(os.path.join(ROOT, 'static'), DIST)
    home(); nieuws_paginas(); wedstrijden(); teams(); dc_dvsa(); club(); sponsoren(); contact(); lid_worden(); vrijwilligers(); niet_gevonden(); redirects()
    n = sum(1 for _, _, fs in os.walk(DIST) for f in fs if f.endswith('.html'))
    print('Klaar: %d pagina\'s in dist/' % n)


if __name__ == '__main__':
    main()
