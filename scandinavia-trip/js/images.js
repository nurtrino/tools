/* ============================================================
   Place photography resolver.
   Given a place name, returns a Promise<string[]> of photo URLs.

   Source order:
     1. Google Places photos — when a Maps API key is configured
        (window.__gmapsPromise is set by app.js at boot).
     2. Wikipedia / Wikimedia lead images — keyless fallback.

   Results are cached in memory + sessionStorage so a session
   only ever fetches each place once.
   ============================================================ */
(function () {
  "use strict";

  var memory = {};
  var placesSvc = null;

  function cacheKey(name) { return "scandi27.img." + name.toLowerCase(); }

  function fromSession(name) {
    try {
      var v = sessionStorage.getItem(cacheKey(name));
      return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
  }

  function store(name, urls) {
    memory[name] = urls;
    try { sessionStorage.setItem(cacheKey(name), JSON.stringify(urls)); } catch (e) { /* full/blocked */ }
  }

  function wikipedia(name) {
    var url = "https://en.wikipedia.org/w/api.php" +
      "?action=query&generator=search&gsrsearch=" + encodeURIComponent(name) +
      "&gsrlimit=4&prop=pageimages&piprop=thumbnail&pithumbsize=900&format=json&origin=*";
    return fetch(url).then(function (r) { return r.json(); }).then(function (data) {
      var pages = (data.query || {}).pages || {};
      return Object.keys(pages)
        .map(function (k) { return pages[k]; })
        .sort(function (a, b) { return a.index - b.index; })
        .map(function (p) { return p.thumbnail && p.thumbnail.source; })
        .filter(function (u) { return u && !/\.svg/i.test(u); });
    });
  }

  function googlePhotos(name) {
    return new Promise(function (resolve, reject) {
      if (!(window.google && google.maps && google.maps.places)) return reject(new Error("no places lib"));
      placesSvc = placesSvc || new google.maps.places.PlacesService(document.createElement("div"));
      placesSvc.textSearch({ query: name }, function (results, status) {
        if (status !== "OK" || !results || !results[0]) return reject(new Error(status));
        var photos = (results[0].photos || []).slice(0, 5).map(function (p) {
          return p.getUrl({ maxWidth: 900, maxHeight: 700 });
        });
        photos.length ? resolve(photos) : reject(new Error("no photos"));
      });
    });
  }

  function resolve(name) {
    if (window.__gmapsPromise) {
      return window.__gmapsPromise.then(function () {
        return googlePhotos(name).catch(function () { return wikipedia(name); });
      });
    }
    return wikipedia(name);
  }

  window.TripImages = {
    get: function (name) {
      if (!name) return Promise.resolve([]);
      if (memory[name]) return Promise.resolve(memory[name]);
      var cached = fromSession(name);
      if (cached) { memory[name] = cached; return Promise.resolve(cached); }
      return resolve(name)
        .then(function (urls) { store(name, urls || []); return urls || []; })
        .catch(function () { return []; });
    },
  };
})();
