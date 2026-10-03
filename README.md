# DVSA website

De website van voetbalvereniging DVSA (Door Vriendschap Sterk Amerongen).
Hij draait op Cloudflare Pages. Elke wijziging die hier op GitHub wordt opgeslagen,
staat binnen een paar minuten vanzelf online.

## Iets aanpassen

Alles wat je normaal wilt veranderen staat in de map `content/`. Je kunt de bestanden
gewoon op github.com openen, op het potloodje klikken, aanpassen en onderaan op
**Commit changes** klikken.

| Wat | Waar |
|---|---|
| Nieuwsbericht plaatsen | Nieuw bestand in `content/nieuws/` (zie `_VOORBEELD.md.txt`) |
| Melding bovenaan (bijv. Grote Clubactie) aan/uit | `content/site.json` → `melding` → `"aan": true` of `false` |
| Mailadressen, adres, kantinetijden, contributie | `content/site.json` |
| Sponsor toevoegen of verwijderen | `content/sponsors.json`, logo in `static/img/sponsors/` |
| Club-pagina's (gedragscode, geschiedenis, ...) | `content/paginas/` |
| Foto's bij nieuws | `static/img/nieuws/` |

Programma, uitslagen, standen, teams, staf en selecties komen automatisch uit Sportlink.
Die hoef je hier nooit bij te werken.

Nieuwsberichten ouder dan 4 maanden verdwijnen vanzelf van de site.

## Hoe het in elkaar zit (voor wie het wil weten)

- `build.py` maakt van alles in `content/` en `static/` een complete website in `dist/`.
  Alleen standaard Python, geen extra pakketten.
- `functions/api/sportlink/` is een kleine Cloudflare-functie die de gegevens bij
  Sportlink Club.Dataservice ophaalt. De client ID kan in Cloudflare worden ingesteld als
  omgevingsvariabele `SPORTLINK_CLIENT_ID`.
- `static/js/sportlink.js` zet die gegevens op de pagina's.
- In `dist/_redirects` staan de doorverwijzingen van de oude adressen (WordPress-site)
  naar de nieuwe pagina's.

### Cloudflare Pages instellingen

- Build command: `python3 build.py`
- Build output directory: `dist`
- Root directory: (leeg)

### Lokaal bekijken

```
python3 build.py
cd dist && python3 -m http.server 8000
```

Open daarna http://localhost:8000. De Sportlink-gegevens werken alleen online op Cloudflare.

## Website gehost door

[Bootsystems](https://www.bootsystems.nl/)
