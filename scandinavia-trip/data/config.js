/* ============================================================================
   SITE CONFIG
   ----------------------------------------------------------------------------
   googleMapsApiKey — unlocks the Google map and Google place photography.

   To get one (free tier is far more than this site will ever use):
     1. console.cloud.google.com → create a project
     2. Enable "Maps JavaScript API" and "Places API"
     3. Credentials → Create API key
     4. Restrict the key: Application restrictions → Websites →
        add your Render URL (and localhost for previewing)
   A referrer-restricted browser key is public by design — it is safe to
   commit here.

   Leave it "" and the site still works: OpenStreetMap-based map plate and
   Wikipedia/Wikimedia place photography instead.
   ========================================================================= */

window.TRIP_CONFIG = {
  googleMapsApiKey: "",
};
