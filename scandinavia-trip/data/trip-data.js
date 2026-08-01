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

   BASE SHAPE
   ----------
   {
     name: "Stockholm", country: "Sweden",
     lat: 59.3293, lng: 18.0686,
     arrive: "2027-03-27", depart: "2027-03-30",
     lodging: "Hotel name / Airbnb link",
     notes: ""
   }

   EXAMPLE (copy, uncomment, adapt):
   // days["2027-03-27"] gets:
   // { time: "10:15", title: "Land at Arlanda", type: "flight",
   //   location: { name: "Stockholm Arlanda (ARN)", lat: 59.6498, lng: 17.9238 },
   //   notes: "Arlanda Express into the city, ~18 min." }
   ========================================================================= */

window.TRIP = {
  meta: {
    title: "Scandinavia",
    subtitle: "Spring Break 2027",
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
  bases: [],

  /* One entry per day of the trip. Keep them in date order. */
  days: [
    { date: "2027-03-26", label: "", events: [] },
    { date: "2027-03-27", label: "", events: [] },
    { date: "2027-03-28", label: "", events: [] },
    { date: "2027-03-29", label: "", events: [] },
    { date: "2027-03-30", label: "", events: [] },
    { date: "2027-03-31", label: "", events: [] },
    { date: "2027-04-01", label: "", events: [] },
    { date: "2027-04-02", label: "", events: [] },
    { date: "2027-04-03", label: "", events: [] },
    { date: "2027-04-04", label: "", events: [] },
    { date: "2027-04-05", label: "", events: [] },
  ],

  /* Loose ideas that aren't scheduled yet. They show up in the "Ideas" shelf. */
  ideas: [],
};
