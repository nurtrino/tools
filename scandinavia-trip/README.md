# Scandinavia · Spring Break 2027 — living itinerary

A self-contained static site (no build step, no external CDNs) for planning the
Chicago → Scandinavia trip, **March 26 – April 5, 2027**.

- **Itinerary** — animated day-by-day timeline
- **Calendar** — March + April grids with plan-density dots; click a day for details
- **Map** — dark Leaflet map; anything with a `lat`/`lng` gets a pulsing pin, bases are joined by an animated route line
- **Export** — one click produces a real `.docx` Word document of the whole trip
- **＋ Add** — quick-add plans from the browser (saved to `localStorage`), then fold them into the repo with **Sync local changes**

## Where the data lives

Everything renders from one file: [`data/trip-data.js`](data/trip-data.js).
The schema is documented at the top of that file. Short version:

```js
days: [
  { date: "2027-03-27", label: "Stockholm, day one", events: [
    { time: "10:15", title: "Land at Arlanda", type: "flight",
      location: { name: "Stockholm Arlanda (ARN)", lat: 59.6498, lng: 17.9238 },
      notes: "Arlanda Express into the city." },
  ]},
],
bases: [
  { name: "Stockholm", country: "Sweden", lat: 59.3293, lng: 18.0686,
    arrive: "2027-03-27", depart: "2027-03-30", lodging: "TBD" },
],
ideas: [ "Icehotel day trip?", "Smørrebrød crawl in Copenhagen" ],
```

Event `type` controls the pin/dot color: `flight`, `transit`, `lodging`,
`food`, `sight`, `museum`, `nature`, `other`.

## Three ways to add plans

1. **Ask Claude.** "Add a food tour in Copenhagen on April 2nd" — Claude edits
   `data/trip-data.js` and pushes; Render redeploys automatically.
2. **Edit the file yourself.** Same file, same schema, commit and push.
3. **In the browser.** Hit **＋ Add**. That saves to your browser only — when
   you're happy, open **Sync local changes** (footer), copy the generated file
   over `data/trip-data.js`, commit, then hit **Clear local additions**.

## Deploying on Render

The repo root has a `render.yaml` blueprint — **New → Blueprint** in Render and
point it at this repo. Or create it manually:

- **New → Static Site**, connect this repo
- **Root directory:** `scandinavia-trip`
- **Build command:** *(leave empty)*
- **Publish directory:** `.`

Every push to the deployed branch goes live automatically — that's what makes
it a living itinerary.

## Local preview

```sh
cd scandinavia-trip
python3 -m http.server 8000
# open http://localhost:8000
```

## Vendored dependencies

- [Leaflet 1.9.4](https://leafletjs.com) — `vendor/leaflet/`
- [docx 9.5.1](https://docx.js.org) — `vendor/docx/`
- Space Grotesk + Inter — `fonts/` (self-hosted woff2)

Map tiles stream from CARTO/OpenStreetMap at view time; everything else is
served from this folder.
