/* ============================================================
   Export the live itinerary (repo data + local additions)
   as a real .docx Word document. Uses vendor/docx/docx.iife.js.
   ============================================================ */
(function () {
  "use strict";

  var INK = "1C1914";
  var DIM = "6B6357";
  var ACCENT = "1C1914";

  function fmtDate(iso) {
    var p = iso.split("-");
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return d.toLocaleDateString("en-US", {
      weekday: "long", month: "long", day: "numeric", year: "numeric",
    });
  }

  function typeLabel(t) {
    var map = {
      flight: "Flight", transit: "Transit", lodging: "Lodging", food: "Food & drink",
      sight: "Sight", museum: "Museum", nature: "Nature", other: "Plan",
    };
    return map[t] || "Plan";
  }

  function cell(opts) {
    var D = window.docx;
    return new D.TableCell({
      width: { size: opts.width, type: D.WidthType.PERCENTAGE },
      margins: { top: 90, bottom: 90, left: 120, right: 120 },
      borders: {
        top: { style: D.BorderStyle.NONE },
        bottom: { style: D.BorderStyle.SINGLE, size: 4, color: "C9C2B2" },
        left: { style: D.BorderStyle.NONE },
        right: { style: D.BorderStyle.NONE },
      },
      children: opts.children,
    });
  }

  function para(runs, opts) {
    var D = window.docx;
    return new D.Paragraph(Object.assign({ children: runs }, opts || {}));
  }

  function run(text, opts) {
    var D = window.docx;
    return new D.TextRun(Object.assign({ text: text, font: "Georgia", size: 21, color: INK }, opts || {}));
  }

  function eventRow(ev) {
    var D = window.docx;
    var body = [
      para([run(ev.title || "Untitled", { bold: true, size: 22 })]),
    ];
    var subBits = [];
    if (ev.type) subBits.push(typeLabel(ev.type));
    if (ev.location && ev.location.name) subBits.push(ev.location.name);
    if (subBits.length) {
      body.push(para([run(subBits.join("  ·  "), { color: ACCENT, size: 18 })]));
    }
    if (ev.notes) body.push(para([run(ev.notes, { color: DIM, size: 19, italics: true })]));
    if (ev.link) body.push(para([run(ev.link, { color: "6B6357", size: 17 })]));

    return new D.TableRow({
      children: [
        cell({ width: 14, children: [para([run(ev.time || "—", { bold: true, color: DIM, size: 19 })])] }),
        cell({ width: 86, children: body }),
      ],
    });
  }

  function buildDoc(trip, days) {
    var D = window.docx;
    var kids = [];

    kids.push(new D.Paragraph({
      children: [new D.TextRun({ text: (trip.meta.title || "Trip").toUpperCase(), bold: true, size: 72, color: INK, font: "Georgia" })],
      spacing: { after: 60 },
    }));
    kids.push(para([run(trip.meta.subtitle || "", { color: ACCENT, size: 26, bold: true })], { spacing: { after: 40 } }));
    kids.push(para([run(fmtDate(trip.meta.startDate) + "  —  " + fmtDate(trip.meta.endDate), { color: DIM, size: 22 })]));
    if (trip.meta.origin && trip.meta.origin.name) {
      kids.push(para([run("Departing from " + trip.meta.origin.name, { color: DIM, size: 20, italics: true })], { spacing: { after: 300 } }));
    }

    days.forEach(function (day, i) {
      var heading = "Day " + (i + 1) + "  ·  " + fmtDate(day.date);
      kids.push(new D.Paragraph({
        children: [new D.TextRun({ text: heading, bold: true, size: 28, color: INK, font: "Georgia" })],
        spacing: { before: 320, after: 40 },
        border: { bottom: { style: D.BorderStyle.SINGLE, size: 8, color: ACCENT, space: 4 } },
      }));
      if (day.label) {
        kids.push(para([run(day.label, { italics: true, color: ACCENT, size: 21 })], { spacing: { after: 80 } }));
      }
      var evs = day.events || [];
      if (!evs.length) {
        kids.push(para([run("No plans yet.", { italics: true, color: DIM, size: 20 })], { spacing: { after: 120 } }));
      } else {
        kids.push(new D.Table({
          width: { size: 100, type: D.WidthType.PERCENTAGE },
          rows: evs.map(eventRow),
        }));
      }
    });

    if (trip.ideas && trip.ideas.length) {
      kids.push(new D.Paragraph({
        children: [new D.TextRun({ text: "Idea shelf", bold: true, size: 28, color: INK, font: "Georgia" })],
        spacing: { before: 400, after: 80 },
        border: { bottom: { style: D.BorderStyle.SINGLE, size: 8, color: ACCENT, space: 4 } },
      }));
      trip.ideas.forEach(function (idea) {
        var text = typeof idea === "string" ? idea : (idea.title || "");
        kids.push(new D.Paragraph({ children: [run(text, { size: 21 })], bullet: { level: 0 } }));
      });
    }

    return new D.Document({
      creator: "Scandinavia '27 itinerary",
      title: (trip.meta.title || "Trip") + " itinerary",
      sections: [{
        properties: {
          page: { margin: { top: 1100, bottom: 1100, left: 1200, right: 1200 } },
        },
        children: kids,
      }],
    });
  }

  window.exportTripDocx = function (trip, days) {
    var doc = buildDoc(trip, days);
    return window.docx.Packer.toBlob(doc).then(function (blob) {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "Scandinavia-Itinerary.docx";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        URL.revokeObjectURL(a.href);
        a.remove();
      }, 800);
    });
  };
})();
