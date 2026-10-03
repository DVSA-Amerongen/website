// Cloudflare Pages Function: doorgeefluik naar Sportlink Club.Dataservice.
// De website vraagt /api/sportlink/programma?... op; deze functie voegt de client ID toe,
// haalt de gegevens bij Sportlink op en bewaart ze 5 minuten in de cache.
// De client ID kan in Cloudflare worden ingesteld als omgevingsvariabele SPORTLINK_CLIENT_ID.

const TOEGESTAAN = new Set([
  'programma', 'uitslagen', 'teams', 'team-indeling', 'team-poulelijst', 'poulestand',
  'pouleprogramma', 'poule-uitslagen', 'afgelastingen', 'commissies', 'commissie-leden', 'wedstrijd-informatie'
]);

export async function onRequest({ request, params, env }) {
  const pad = (params.path || []).join('/');
  if (!TOEGESTAAN.has(pad)) {
    return json({ fout: 'Onbekend onderdeel' }, 404);
  }
  const binnen = new URL(request.url);
  const doel = new URL('https://data.sportlink.com/' + pad);
  for (const [k, v] of binnen.searchParams) {
    if (k !== 'client_id') doel.searchParams.set(k, v);
  }
  doel.searchParams.set('client_id', env.SPORTLINK_CLIENT_ID || 'HdwP2nwft4');

  try {
    const antwoord = await fetch(doel.toString(), {
      headers: { Accept: 'application/json' },
      cf: { cacheTtl: 300, cacheEverything: true }
    });
    const tekst = await antwoord.text();
    return new Response(tekst, {
      status: antwoord.status,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'public, max-age=300'
      }
    });
  } catch (e) {
    return json({ fout: 'Sportlink is even niet bereikbaar' }, 502);
  }
}

function json(data, status) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' }
  });
}
