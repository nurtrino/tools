/* ============================================================================
   SCANDINAVIA · SPRING BREAK 2027 — TRIP DATA
   ----------------------------------------------------------------------------
   This file is the single source of truth for the itinerary. Edit it by hand
   or ask Claude to edit it — the site renders everything from here.

   HOW TO ADD THINGS
   -----------------
   1. A city / home base  →  add an object to `bases`.
   2. A plan for a day    →  find the day in `days` and push into its `events`.
   3. Anything with a lat/lng automatically appears on the map.

   EVENT SHAPE (all fields optional except `title`)
   ------------------------------------------------
   {
     time:  "09:30",                          // 24h, or "" for all-day
     title: "Vasa Museum",
     type:  "sight",                          // flight | transit | lodging |
                                              // food | sight | museum |
                                              // nature | other
     location: { name: "Vasa Museum, Stockholm",
                 lat: 59.3280, lng: 18.0914 },
     notes: "Buy tickets ahead. ~2 hours.",
     link:  "https://www.vasamuseet.se"
   }
   ========================================================================= */

window.TRIP = {
  meta: {
    title: "Scandinavia",
    subtitle: "Spring Break 2027 · Copenhagen — Stockholm — Oslo — Bergen",
    startDate: "2027-03-26",
    endDate: "2027-04-05",
    origin: {
      name: "Chicago O'Hare (ORD)",
      lat: 41.9742,
      lng: -87.9073,
    },
    travelers: [],
  },

  /* Cities / home bases, in travel order. Drawn as the route on the map. */
  bases: [
    { name: "Copenhagen", country: "Denmark", lat: 55.6761, lng: 12.5683,
      arrive: "2027-03-27", depart: "2027-03-30",
      lodging: "TBD — aim for Indre By or Vesterbro" },
    { name: "Stockholm", country: "Sweden", lat: 59.3293, lng: 18.0686,
      arrive: "2027-03-30", depart: "2027-04-02",
      lodging: "TBD — Gamla Stan or Södermalm" },
    { name: "Oslo", country: "Norway", lat: 59.9139, lng: 10.7522,
      arrive: "2027-04-02", depart: "2027-04-04",
      lodging: "TBD — Sentrum, near the station" },
    { name: "Bergen", country: "Norway", lat: 60.3913, lng: 5.3221,
      arrive: "2027-04-04", depart: "2027-04-05",
      lodging: "TBD — Bryggen area" },
  ],

  /* One entry per day of the trip. Keep them in date order. */
  days: [
    { date: "2027-03-26", label: "Wheels up", events: [
      { time: "18:00", title: "Depart Chicago O'Hare", type: "flight",
        location: { name: "Chicago O'Hare (ORD)", lat: 41.9742, lng: -87.9073 },
        notes: "Overnight to Copenhagen. Watch SAS / Icelandair / LOT routings when fares open (~Oct 2026)." },
    ]},

    { date: "2027-03-27", label: "Landfall — Copenhagen", events: [
      { time: "09:30", title: "Land at Copenhagen Kastrup", type: "flight",
        location: { name: "Copenhagen Airport (CPH)", lat: 55.6180, lng: 12.6508 },
        notes: "Metro M2 straight into town, ~15 min." },
      { time: "14:00", title: "Check in, then Nyhavn & harbor walk", type: "sight",
        location: { name: "Nyhavn", lat: 55.6797, lng: 12.5912 },
        notes: "Stay outside and moving — jet lag dies in daylight." },
      { time: "18:30", title: "First smørrebrød", type: "food",
        location: { name: "Torvehallerne market", lat: 55.6837, lng: 12.5693 } },
    ]},

    { date: "2027-03-28", label: "Copenhagen on foot", events: [
      { time: "10:00", title: "Rosenborg Castle & King's Garden", type: "sight",
        location: { name: "Rosenborg Castle", lat: 55.6857, lng: 12.5773 },
        notes: "Crown jewels in the basement." },
      { time: "14:00", title: "Strøget + Round Tower climb", type: "sight",
        location: { name: "Rundetaarn", lat: 55.6813, lng: 12.5757 } },
      { time: "20:00", title: "Tivoli Gardens by night", type: "sight",
        location: { name: "Tivoli Gardens", lat: 55.6738, lng: 12.5681 },
        notes: "Season usually opens late March — confirm dates." },
    ]},

    { date: "2027-03-29", label: "Art up the coast", events: [
      { time: "10:30", title: "Louisiana Museum of Modern Art", type: "museum",
        location: { name: "Louisiana, Humlebæk", lat: 55.9691, lng: 12.5417 },
        notes: "35 min by coastal train. The Giacometti gallery over the sound is the whole point." },
      { time: "18:00", title: "Reffen street food (or harbor sauna, if brave)", type: "food",
        location: { name: "Reffen, Refshaleøen", lat: 55.6924, lng: 12.6114 } },
    ]},

    { date: "2027-03-30", label: "North by rail", events: [
      { time: "09:00", title: "Train Copenhagen → Stockholm", type: "transit",
        notes: "X2000 direct, ~5h15 across the Øresund Bridge. Book ~90 days out; sit left side leaving Copenhagen." },
      { time: "15:00", title: "Check in — Stockholm", type: "lodging",
        location: { name: "Stockholm", lat: 59.3293, lng: 18.0686 } },
      { time: "17:30", title: "Gamla Stan at golden hour", type: "sight",
        location: { name: "Stortorget, Gamla Stan", lat: 59.3251, lng: 18.0711 } },
    ]},

    { date: "2027-03-31", label: "Stockholm — the museum island", events: [
      { time: "10:00", title: "Vasa Museum", type: "museum",
        location: { name: "Vasa Museum", lat: 59.3280, lng: 18.0914 },
        notes: "A 1628 warship raised whole from the harbor. Be there at opening.",
        link: "https://www.vasamuseet.se" },
      { time: "13:30", title: "Skansen or ABBA — pick a lane", type: "museum",
        location: { name: "Djurgården", lat: 59.3269, lng: 18.1049 } },
      { time: "19:00", title: "Dinner in Södermalm", type: "food",
        location: { name: "Södermalm", lat: 59.3145, lng: 18.0716 } },
    ]},

    { date: "2027-04-01", label: "Out to the archipelago", events: [
      { time: "09:30", title: "Ferry to Vaxholm", type: "nature",
        location: { name: "Vaxholm", lat: 59.4028, lng: 18.3514 },
        notes: "Waxholmsbolaget boats from Strömkajen, ~1h each way through the islands." },
      { time: "16:30", title: "Fika deficit correction", type: "food",
        notes: "Cardamom buns are structurally mandatory." },
    ]},

    { date: "2027-04-02", label: "To Norway", events: [
      { time: "08:30", title: "Train Stockholm → Oslo", type: "transit",
        notes: "~5h30. The lazy alternative is a 1h flight — decide when fares are out." },
      { time: "15:00", title: "Check in — Oslo", type: "lodging",
        location: { name: "Oslo", lat: 59.9139, lng: 10.7522 } },
      { time: "16:30", title: "Opera House roof walk", type: "sight",
        location: { name: "Oslo Opera House", lat: 59.9075, lng: 10.7532 },
        notes: "You walk on the building. Fjord on three sides." },
    ]},

    { date: "2027-04-03", label: "Oslo — bronze & polar ships", events: [
      { time: "10:00", title: "Vigeland Sculpture Park", type: "sight",
        location: { name: "Vigelandsparken", lat: 59.9270, lng: 10.7008 } },
      { time: "13:30", title: "Munch Museum or the Fram polar ship", type: "museum",
        location: { name: "Munch, Bjørvika", lat: 59.9060, lng: 10.7599 } },
      { time: "18:00", title: "Aker Brygge waterfront dinner", type: "food",
        location: { name: "Aker Brygge", lat: 59.9106, lng: 10.7290 } },
    ]},

    { date: "2027-04-04", label: "The Bergen Line", events: [
      { time: "08:25", title: "Oslo → Bergen railway", type: "transit",
        notes: "~6h30 and one of the great train rides on earth — Hardangervidda plateau, Finse at 1,222 m, likely still under snow in April. Book ~90 days out." },
      { time: "16:00", title: "Check in — Bergen, walk Bryggen wharf", type: "lodging",
        location: { name: "Bryggen", lat: 60.3975, lng: 5.3241 } },
      { time: "19:00", title: "Fish market dinner", type: "food",
        location: { name: "Bergen Fisketorget", lat: 60.3945, lng: 5.3247 } },
    ]},

    { date: "2027-04-05", label: "Homeward", events: [
      { time: "08:00", title: "Fløibanen funicular — one last look", type: "sight",
        location: { name: "Mount Fløyen", lat: 60.3963, lng: 5.3283 },
        notes: "Only if the flight time allows. Seven minutes up, whole city below." },
      { time: "12:00", title: "Fly Bergen → Chicago", type: "flight",
        location: { name: "Bergen Airport (BGO)", lat: 60.2934, lng: 5.2181 },
        notes: "Connects via Oslo, Copenhagen, or Reykjavík." },
    ]},
  ],

  /* Loose ideas that aren't scheduled yet. They show up in the "Ideas" shelf. */
  ideas: [
    "Norway in a Nutshell add-on from Bergen — Flåm railway + Nærøyfjord cruise (needs a spare day)",
    "Malmö is 35 min over the bridge from Copenhagen — passport stamp, falafel, back by dinner",
    "Copenhagen by rented bike — the city is built for it",
    "Aurora odds in late March are slim this far south; check the Bergen forecast anyway",
    "Book X2000 and Bergen Line trains ~90 days out — cheap seats evaporate",
    "Icehotel is 1,200 km further north. A different trip. Probably.",
  ],
};
