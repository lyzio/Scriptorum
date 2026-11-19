"""Write the four general themes of 0.7.8 (F8, decided 19 November 2026,
approved mockups in design document 12.11): WHFRP, The One Ring, WH40KRP and
Rogue Trader.

Like tools/make_general_themes.py, each theme copies the Vaesen templates and
gets its own _style.typ: the Vaesen file with the theme's colours and fonts,
then the theme's frames appended (Typst exports the last definition of a
name, so the frames and the two style hooks page-background and stat-row
replace the Vaesen ones). This tool also writes each theme's ornaments (the
project's own drawings), handout papers, labels, page setup, manifest and
licence file. The fonts are kept in each theme's fonts/ folder and are not
written here.

Run it again after changing a shared template:  python tools/make_more_themes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_general_themes import BUNDLED, write_theme  # noqa: E402

UNOFFICIAL = ("An unofficial, fan-made look, not affiliated with or endorsed by the owners "
              "of the work or game it is named after.")

# Shared Typst helpers for the four themes: a torn edge, as on the WHFRP
# panels, and a hand-made hourglass colour per theme (11.12).
TORN = r'''
// A panel with torn top and bottom edges (deterministic: F7.8).
#let torn-points(w, h, seed, depth: 2.6pt) = {
  let n = calc.max(8, int(w / 9pt))
  let top = range(n + 1).map(i => (w * i / n, depth * _noise(seed, i)))
  let bottom = range(n + 1).rev().map(i => (w * i / n, h - depth * _noise(seed + 9, i)))
  (..top, ..bottom)
}
#let torn-panel(paint, w, h, seed) = polygon(fill: paint, stroke: none, ..torn-points(w, h, seed))
'''

# --- WHFRP -------------------------------------------------------------------------
WHFRP_HEAD = r'''// --- colours -------------------------------------------------------------------
// WHFRP (approved mockup 12.11, option B): grim fantasy after the look of the
// 4th-edition books: dark grey-brown ink, grey panels with torn edges, a
// plum chapter tab and a muted green medallion.
#let ink = rgb("#1F1C18")
#let accent = rgb("#3A352E")    // dark grey-brown: rules, frames, headings
#let quiet = rgb("#5B5246")
#let rust = rgb("#7A2E26")
#let ochre = rgb("#6E5A33")
#let wine = rgb("#5E3B5C")      // the plum chapter tab
#let green = rgb("#3F5A3C")     // the medallion's green
#let band = rgb("#EFEDE9")
#let rule-tint = rgb("#B7B1A7")
#let fills = (grey: rgb("#DEDBD5"), beige: rgb("#EEE3CC"))
#let panel = rgb("#E2E0DC")     // grey panels with torn edges
#let panel-dark = rgb("#C9C5BD") // the section bars of a stat block
#let tan = rgb("#EEE3CC")       // the read-aloud strip
#let pacing-tint = rgb("#F0EEEA")
#let box-fill = fills.grey
#let table-tint = band

#let variant-styles = (
  secret: (color: accent, tint: fills.grey),
  public: (color: green, tint: rgb("#E8ECE4")),
  hint: (color: rgb("#5B5246"), tint: rgb("#EEEBE6")),
)

// --- fonts (SIL OFL, static weights) ----------------------------------------------
#let fonts = (
  body: "Crimson Text",
  read: "Crimson Text",
  head: "Libre Caslon Display",
  label: "Crimson Text",
  display: ("Libre Caslon Display",),
  quote: "Crimson Text",
  easy: "Crimson Text",
)
#let sizes = (body: 10.5pt, read: 11.5pt, label: 8pt, act: 24pt, scene: 15pt, title: 34pt)
#let secret-text(body) = text(font: fonts.body, size: 10.5pt, body)
'''

WHFRP_FRAMES = TORN + r'''
// --- WHFRP frames (approved mockup 12.11) ---------------------------------------------
#let quote-tint = tan
#let hand-ink = rgb("#2A3550")
#let bullet = box(baseline: -0.02em, pdf.artifact(circle(radius: 0.16em, fill: ink)))
#let framed-text(body) = frame-par({
  set list(marker: bullet, body-indent: 0.5em)
  labelize(body)
})
#let panel-title(title) = align(center, text(font: fonts.head, size: 10.5pt, tracking: 0.12em, fill: ink, upper(title)))

// Frames are grey panels with torn top and bottom edges, the title in spaced
// capitals. A panel taller than a column breaks as a plain grey panel.
#let curl-frame(title: none, body, seed: 3, above: 1.1em, below: 1.1em, breakable: false) = {
  if breakable {
    return block(width: 100%, breakable: true, above: above, below: below, fill: panel,
      inset: (x: 10pt, top: 9pt, bottom: 9pt), {
        if title != none { panel-title(title); v(0.3em) }
        framed-text(body)
      })
  }
  block(width: 100%, breakable: false, above: above, below: below, layout(size => {
    let w = size.width
    let inner = block(width: w - 20pt, {
      if title != none { panel-title(title); v(0.3em) }
      framed-text(body)
    })
    let h = measure(inner).height + 22pt
    box(width: w, height: h, {
      pdf.artifact(place(top + left, torn-panel(panel, w, h, seed)))
      place(top + left, dx: 10pt, dy: 11pt, inner)
    })
  }))
}

// The secret: a grey panel with torn edges and a round medallion on top.
#let secret-frame(title: none, body, fill: "grey", seed: 5, above: 1.3em, below: 1.1em, labels: (:), stamp: true) = {
  let paint = fills.at(if fill == "beige" { "beige" } else { "grey" })
  block(width: 100%, breakable: false, above: above + 12pt, below: below, layout(size => {
    let w = size.width
    let inner = block(width: w - 24pt, {
      if title != none { align(center, text(font: fonts.head, size: 11.5pt, tracking: 0.14em, fill: ink, upper(title))); v(0.35em) }
      framed-text(body)
    })
    let h = measure(inner).height + 36pt
    box(width: w, height: h, {
      pdf.artifact({
        place(top + left, torn-panel(paint, w, h, seed))
        place(top + left, dx: w / 2 - 14pt, dy: -14pt, image("../ornaments/medallion.svg", width: 28pt))
      })
      place(top + left, dx: 12pt, dy: 24pt, inner)
    })
  }))
}

// Read-aloud on a pale tan strip with torn edges.
#let read-aloud-frame(heading, body) = block(width: 100%, breakable: false, above: 1.1em, below: 1.1em, layout(size => {
  let w = size.width
  let inner = block(width: w - 24pt, {
    small-caps-label(heading, fill: quiet)
    v(spacing.small)
    frame-par(text(font: fonts.read, size: sizes.read, style: "italic", body))
  })
  let h = measure(inner).height + 20pt
  box(width: w, height: h, {
    pdf.artifact(place(top + left, torn-panel(tan, w, h, seed-of(heading) + 11)))
    place(top + left, dx: 12pt, dy: 10pt, inner)
  })
}))

// Pacing note: a thin grey-brown border, a faint grey tint and an hourglass.
#let pacing-frame(body) = block(
  width: 100%, breakable: false, fill: pacing-tint, stroke: 0.5pt + accent,
  inset: (x: 8pt, y: 7pt), above: 1em, below: 1em,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt), frame-par(text(size: 0.95em, body))))

// Act headings: "• TITLE •" in spaced capitals over a round medallion.
#let act-heading(body) = {
  set text(font: fonts.display, size: sizes.act, weight: "regular", fill: ink, tracking: 0.08em, hyphenate: false)
  set par(justify: false, leading: 0.4em)
  align(center, block(width: 100%, below: 0.35em, [• #upper(body) •]))
  align(center, ornament("medallion.svg", width: 36pt))
}

// Scene titles in capitals over a black rule.
#let scene-title(body) = block(width: 100%, stroke: (bottom: 1.1pt + ink), inset: (bottom: 2.5pt),
  text(font: fonts.head, size: sizes.scene, fill: ink, tracking: 0.04em, hyphenate: false, upper(body)))

// The page number in a small oval on the foot band.
#let page-number(n) = box(fill: white, stroke: 0.8pt + accent, radius: 6pt, inset: (x: 7pt, y: 2.5pt),
  text(font: fonts.body, size: 9pt, fill: ink, n))

// A running band of scrollwork across the top and foot of every page, and
// a plum chapter tab on the outer edge (odd pages right, even pages left).
#let page-background = context {
  let right-page = calc.odd(here().page())
  place(top + left, dy: 9mm, image("../ornaments/band.svg", width: 100%))
  place(bottom + left, dy: -10mm, image("../ornaments/band.svg", width: 100%))
  place(top + (if right-page { right } else { left }), dx: if right-page { -8mm } else { 8mm }, dy: 4mm,
    image("../ornaments/tab.svg", width: 9mm))
}

// Creature stats in a framed table: grey heads, the values under them.
#let stat-row(stats) = block(width: 100%, above: gap(spacing.small), breakable: false, {
  set par(justify: false)
  grid(
    columns: stats.len() * (1fr,), stroke: 0.6pt + accent, inset: (x: 2pt, y: 3pt), align: center + horizon,
    fill: (x, y) => if y == 0 { panel-dark } else { white },
    ..stats.map(s => text(font: fonts.label, size: 7.6pt, weight: "bold", fill: ink, s.label)),
    ..stats.map(s => text(size: 10pt, fill: ink, if s.value == none { [–] } else { str(s.value) })),
  )
})
'''

# --- The One Ring --------------------------------------------------------------------
TOR_HEAD = r'''// --- colours -------------------------------------------------------------------
// The One Ring (approved mockup 12.11): warm brown ink with brick red, after
// a homebrew template used as a mood reference only.
#let ink = rgb("#2B2622")
#let accent = rgb("#A3262A")    // brick red: rules, frames, headings, labels
#let quiet = rgb("#6B5A4A")
#let rust = rgb("#A3262A")
#let ochre = rgb("#7E6330")
#let wine = rgb("#A3262A")
#let brown = rgb("#8A7A6A")     // the brackets and the brush flourishes
#let band = rgb("#F7F1E4")
#let rule-tint = rgb("#C9B28F")
#let fills = (grey: rgb("#F1EEE8"), beige: rgb("#F7F1E4"))
#let pacing-tint = rgb("#FAF6EE")
#let box-fill = fills.grey
#let table-tint = band

#let variant-styles = (
  secret: (color: accent, tint: fills.grey),
  public: (color: rgb("#6B5A4A"), tint: rgb("#F3EFE7")),
  hint: (color: rgb("#7E6330"), tint: rgb("#F6F0E2")),
)

// --- fonts (SIL OFL, static weights) ----------------------------------------------
#let fonts = (
  body: "EB Garamond",
  read: "EB Garamond",
  head: "Uncial Antiqua",
  label: "Josefin Sans",
  display: ("Uncial Antiqua",),
  quote: "EB Garamond",
  easy: "EB Garamond",
)
#let sizes = (body: 10.5pt, read: 11.5pt, label: 7.2pt, act: 28pt, scene: 15pt, title: 36pt)
#let secret-text(body) = text(font: fonts.body, size: 10.5pt, fill: rgb("#4A423B"), body)
'''

TOR_FRAMES = r'''
// --- The One Ring frames (approved mockup 12.11) --------------------------------------
#let quote-tint = band
#let hand-ink = rgb("#2A3550")
#let bullet = box(baseline: 0.02em, pdf.artifact(rotate(45deg, rect(width: 0.34em, height: 0.34em, fill: accent))))
#let framed-text(body) = frame-par({
  set list(marker: bullet, body-indent: 0.5em)
  labelize(body)
})

// Frames: thin red rules on three sides, open at the foot, with leafy vine
// corners at the top.
#let curl-frame(title: none, body, seed: 3, above: 1.1em, below: 1.1em, breakable: false) = block(
  width: 100%, breakable: breakable, above: above + 5pt, below: below,
  stroke: (top: 0.8pt + accent, left: 0.8pt + accent, right: 0.8pt + accent),
  inset: (x: 10pt, top: 12pt, bottom: 8pt), {
    place(top + left, dx: -16pt, dy: -18pt, ornament("vine.svg", width: 22pt))
    place(top + right, dx: 16pt, dy: -18pt, pdf.artifact(scale(x: -100%, image("../ornaments/vine.svg", width: 22pt))))
    if title != none { align(center, caps-label(title, size: 8.4pt)); v(0.25em) }
    framed-text(body)
  })

// The secret: a focus block with brackets on both sides, on the adventure's
// pale fill (F7.3).
#let secret-frame(title: none, body, fill: "grey", seed: 5, above: 1.3em, below: 1.1em, labels: (:), stamp: true) = {
  let paint = fills.at(if fill == "beige" { "beige" } else { "grey" })
  block(width: 100%, breakable: false, above: above, below: below, layout(size => {
    let w = size.width
    let inner = block(width: w - 26pt, {
      if title != none { caps-label(title, size: 8.4pt); v(0.3em) }
      framed-text(body)
    })
    let h = measure(inner).height + 16pt
    box(width: w, height: h, {
      pdf.artifact({
        place(top + left, dx: 3pt, rect(width: w - 6pt, height: h, fill: paint, stroke: none))
        let s = (paint: brown, thickness: 1.4pt, cap: "square")
        place(top + left, curve(stroke: s, curve.move((8pt, 0pt)), curve.line((0pt, 0pt)), curve.line((0pt, h)), curve.line((8pt, h))))
        place(top + left, curve(stroke: s, curve.move((0pt, h / 2)), curve.line((5pt, h / 2))))
        place(top + left, curve(stroke: s, curve.move((w - 8pt, 0pt)), curve.line((w, 0pt)), curve.line((w, h)), curve.line((w - 8pt, h))))
        place(top + left, curve(stroke: s, curve.move((w, h / 2)), curve.line((w - 5pt, h / 2))))
      })
      place(top + left, dx: 13pt, dy: 8pt, inner)
    })
  }))
}

// Read-aloud in red italics under a quiet label.
#let read-aloud-frame(heading, body) = block(width: 100%, breakable: false, above: 1.1em, below: 1.1em, inset: (x: 4pt), {
  small-caps-label(heading, fill: quiet)
  v(spacing.small)
  frame-par(text(font: fonts.read, size: sizes.read, style: "italic", fill: accent, body))
})

// Pacing note: a thin red border, a faint cream tint and an hourglass.
#let pacing-frame(body) = block(
  width: 100%, breakable: false, fill: pacing-tint, stroke: 0.5pt + accent,
  inset: (x: 8pt, y: 7pt), above: 1em, below: 1em,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt), frame-par(text(size: 0.95em, body))))

// Act headings in Uncial Antiqua over tapered brush flourishes and a diamond.
#let act-heading(body) = {
  set text(font: fonts.display, size: sizes.act, weight: "regular", fill: ink, hyphenate: false)
  set par(justify: false, leading: 0.4em)
  align(center, block(width: 100%, below: 0.3em, body))
  align(center, grid(columns: 3, column-gutter: 6pt, align: horizon,
    ornament("brush.svg", width: 48pt), ornament("lozenge.svg", width: 9pt),
    pdf.artifact(scale(x: -100%, image("../ornaments/brush.svg", width: 48pt)))))
}

#let scene-title(body) = text(font: fonts.head, size: sizes.scene, weight: "regular", fill: accent, hyphenate: false, body)

// The page number in the foot band's centre diamond.
#let page-number(n) = box(fill: white, inset: (x: 6pt, y: 2pt), text(font: fonts.body, size: 9.5pt, fill: ink, n))

// An even band of small red diamonds and scrolls between double red rules
// at the top and foot of every page.
#let page-background = {
  place(top + left, dy: 9mm, image("../ornaments/band.svg", width: 100%))
  place(bottom + left, dy: -10.6mm, image("../ornaments/band.svg", width: 100%))
}

// Creature stats in red diamonds on a pale band.
#let stat-row(stats) = block(width: 100%, above: gap(spacing.small), breakable: false, fill: band, inset: (x: 4pt, y: 6pt),
  grid(columns: stats.len() * (1fr,), row-gutter: 4pt, align: center + horizon,
    ..stats.map(s => text(font: fonts.label, size: 6.8pt, weight: "bold", fill: accent, s.label)),
    ..stats.map(s => box(width: 24pt, height: 24pt, {
      pdf.artifact(place(polygon(fill: white, stroke: 1.2pt + accent, (12pt, 0pt), (24pt, 12pt), (12pt, 24pt), (0pt, 12pt))))
      place(center + horizon, dy: 1pt, text(font: fonts.label, size: 9.5pt, weight: "bold", fill: accent,
        if s.value == none { [–] } else { str(s.value) }))
    }))))
'''

# --- WH40KRP ---------------------------------------------------------------------------
WH40K_HEAD = r'''// --- colours -------------------------------------------------------------------
// WH40KRP (approved mockup 12.11): grimdark gothic, near-black and bone with
// dark bronze and a deep red.
#let ink = rgb("#161412")
#let accent = rgb("#1E1B18")    // near-black: rules, frames, headings
#let quiet = rgb("#4A4038")
#let bronze = rgb("#7B5E34")
#let rust = rgb("#7A1F1F")
#let ochre = bronze
#let wine = rgb("#7A1F1F")      // the deep red of the Clearance stamp
#let band = rgb("#E9E3D8")
#let rule-tint = rgb("#9A8F84")
#let fills = (grey: rgb("#EAE7E2"), beige: rgb("#EFE7D6"))
#let pacing-tint = rgb("#F1EEE9")
#let box-fill = fills.grey
#let table-tint = band

#let variant-styles = (
  secret: (color: wine, tint: fills.grey),
  public: (color: bronze, tint: rgb("#F0EBE2")),
  hint: (color: quiet, tint: rgb("#EEEBE7")),
)

// --- fonts (SIL OFL, static weights) ----------------------------------------------
#let fonts = (
  body: "Spectral",
  read: "Share Tech Mono",
  head: "Grenze Gotisch",
  label: "Share Tech Mono",
  display: ("Grenze Gotisch",),
  quote: "Spectral",
  easy: "Spectral",
)
#let sizes = (body: 9.5pt, read: 9.5pt, label: 7.4pt, act: 32pt, scene: 17pt, title: 42pt)
#let secret-text(body) = text(font: fonts.body, size: 9.5pt, body)
'''

WH40K_FRAMES = r'''
// --- WH40KRP frames (approved mockup 12.11) -------------------------------------------
#let quote-tint = band
#let hand-ink = rgb("#222222")
#let bullet = box(baseline: 0.02em, pdf.artifact(rect(width: 0.32em, height: 0.32em, fill: bronze)))
#let framed-text(body) = frame-par({
  set list(marker: bullet, body-indent: 0.5em)
  labelize(body)
})

// Frames: bronze rules with a pointed arch at the top.
#let curl-frame(title: none, body, seed: 3, above: 1.1em, below: 1.1em, breakable: false) = {
  let head = if title != none { align(center, caps-label(title, fill: bronze, size: 8.2pt)); v(0.25em) }
  if breakable {
    return block(width: 100%, breakable: true, above: above, below: below, stroke: 0.9pt + bronze,
      inset: (x: 10pt, y: 9pt), { head; framed-text(body) })
  }
  block(width: 100%, breakable: false, above: above, below: below, layout(size => {
    let w = size.width
    let a = 11pt
    let inner = block(width: w - 20pt, { head; framed-text(body) })
    let h = measure(inner).height + a + 14pt
    box(width: w, height: h, {
      pdf.artifact(place(top + left, curve(stroke: (paint: bronze, thickness: 0.9pt, join: "miter"),
        curve.move((0pt, h)), curve.line((0pt, a)), curve.line((w / 2 - 30pt, a)),
        curve.quad((w / 2 - 8pt, a), (w / 2, 0pt)), curve.quad((w / 2 + 8pt, a), (w / 2 + 30pt, a)),
        curve.line((w, a)), curve.line((w, h)), curve.close())))
      place(top + left, dx: 10pt, dy: a + 6pt, inner)
    })
  }))
}

// The secret: a dossier in a heavy double frame, its title over the top
// line, with a red Clearance stamp (a printed word).
#let secret-frame(title: none, body, fill: "grey", seed: 5, above: 1.3em, below: 1.1em, labels: (:), stamp: true) = {
  let paint = fills.at(if fill == "beige" { "beige" } else { "grey" })
  block(width: 100%, breakable: false, above: above + 6pt, below: below, layout(size => {
    let w = size.width
    let inner = block(width: w - 26pt, framed-text(body))
    let h = measure(inner).height + 32pt
    box(width: w, height: h, {
      pdf.artifact({
        place(top + left, rect(width: w, height: h, fill: paint, stroke: 1.8pt + accent))
        place(top + left, dx: 3.5pt, dy: 3.5pt, rect(width: w - 7pt, height: h - 7pt, stroke: 0.6pt + accent))
        if stamp { place(top + right, dx: -10pt, dy: -7pt, rotate(-6deg, box(fill: white, stroke: 1.2pt + wine, inset: (x: 5pt, y: 2.5pt),
          text(font: fonts.label, size: 8pt, tracking: 0.18em, fill: wine, upper(labels.at("print.clearance", default: "Clearance")))))) }
      })
      if title != none { place(top + left, dx: 12pt, dy: -5pt, box(fill: white, inset: (x: 5pt, y: 1pt),
        text(font: fonts.label, size: 8.4pt, tracking: 0.22em, fill: ink, upper(title)))) }
      place(top + left, dx: 13pt, dy: 20pt, inner)
    })
  }))
}

// Read-aloud as a data-slate transcript between "+++" lines.
#let read-aloud-frame(heading, body) = block(width: 100%, breakable: false, above: 1.1em, below: 1.1em, {
  text(font: fonts.label, size: 8pt, tracking: 0.12em, fill: bronze, [+++ #upper(heading) +++])
  v(spacing.small)
  frame-par(text(font: fonts.read, size: sizes.read, fill: ink, body))
  v(spacing.small)
  text(font: fonts.label, size: 8pt, tracking: 0.12em, fill: bronze, [+++])
})

// Pacing note: a thin dashed bronze border, a faint tint and an hourglass.
#let pacing-frame(body) = block(
  width: 100%, breakable: false, fill: pacing-tint, stroke: (paint: bronze, thickness: 0.6pt, dash: "dashed"),
  inset: (x: 8pt, y: 7pt), above: 1em, below: 1em,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt), frame-par(text(size: 0.95em, body))))

// Act headings under a shield holding a skull over laurels, with a heavy rule.
#let act-heading(body) = {
  set text(font: fonts.display, size: sizes.act, weight: "bold", fill: ink, hyphenate: false)
  set par(justify: false, leading: 0.4em)
  align(center, ornament("skull.svg", width: 30pt))
  align(center, block(width: 100%, above: 0.25em, below: 0.25em, body))
  align(center, box(width: 50%, height: 3.2pt, stroke: (top: 1.6pt + ink, bottom: 0.5pt + bronze)))
}

#let scene-title(body) = block(width: 100%, stroke: (bottom: 1.6pt + ink), inset: (bottom: 2pt),
  text(font: fonts.head, size: sizes.scene, weight: "medium", fill: ink, hyphenate: false, body))

// The page number in a small shield.
#let page-number(n) = box(width: 16pt, height: 19pt, {
  ornament("shield.svg", width: 16pt)
  place(top + center, dy: 4pt, text(font: fonts.label, size: 8pt, fill: ink, n))
})

// A black band with bronze rules across the top of every page, and a
// double rule at the foot.
#let page-background = {
  place(top + left, dy: 8mm, image("../ornaments/band.svg", width: 100%))
  place(bottom + center, dy: -12mm, box(width: 100% - 34mm, height: 2.6pt, stroke: (top: 1.4pt + ink, bottom: 0.5pt + bronze)))
}

// Creature stats in a bordered grid: bone heads, the values under them.
#let stat-row(stats) = block(width: 100%, above: gap(spacing.small), breakable: false, {
  set par(justify: false)
  grid(
    columns: stats.len() * (1fr,), stroke: 0.7pt + accent, inset: (x: 2pt, y: 3pt), align: center + horizon,
    fill: (x, y) => if y == 0 { band } else { white },
    ..stats.map(s => text(font: fonts.label, size: 7.2pt, fill: ink, upper(s.label))),
    ..stats.map(s => text(font: fonts.label, size: 10pt, fill: ink, if s.value == none { [–] } else { str(s.value) })),
  )
})
'''

# --- Rogue Trader ------------------------------------------------------------------------
RT_HEAD = r'''// --- colours -------------------------------------------------------------------
// Rogue Trader (approved mockup 12.11): baroque explorers and merchant
// princes, in deep navy ink with brass brown and a teal accent.
#let ink = rgb("#1E2A44")
#let accent = rgb("#1E2A44")    // navy: rules, frames, headings
#let quiet = rgb("#4E5A70")
#let brass = rgb("#8A6A2E")
#let teal = rgb("#2B6B6E")
#let rust = rgb("#7A3A22")
#let ochre = brass
#let wine = teal
#let band = rgb("#EEF1F4")
#let rule-tint = rgb("#B9A88A")
#let fills = (grey: rgb("#EDEFF2"), beige: rgb("#F4EEE0"))
#let pacing-tint = rgb("#F2F4F6")
#let box-fill = fills.grey
#let table-tint = band

#let variant-styles = (
  secret: (color: teal, tint: fills.grey),
  public: (color: brass, tint: rgb("#F5F0E6")),
  hint: (color: quiet, tint: rgb("#EEF0F3")),
)

// --- fonts (SIL OFL, static weights) ----------------------------------------------
#let fonts = (
  body: "Cormorant Garamond",
  read: "Cormorant Garamond",
  head: "Cinzel",
  label: "Cinzel",
  display: ("Cinzel Decorative",),
  quote: "Cormorant Garamond",
  easy: "Cormorant Garamond",
)
#let sizes = (body: 11pt, read: 12.5pt, label: 7pt, act: 24pt, scene: 13.5pt, title: 32pt)
#let secret-text(body) = text(font: fonts.body, size: 11.5pt, weight: "medium", body)
'''

RT_FRAMES = r'''
// --- Rogue Trader frames (approved mockup 12.11) --------------------------------------
#let quote-tint = band
#let hand-ink = ink
#let bullet = box(baseline: 0.05em, ornament("star.svg", height: 0.62em))
#let framed-text(body) = frame-par({
  set list(marker: bullet, body-indent: 0.5em)
  labelize(body)
})

// Frames: a thin brass rule with baroque corner scrolls at two corners.
#let curl-frame(title: none, body, seed: 3, above: 1.1em, below: 1.1em, breakable: false) = block(
  width: 100%, breakable: breakable, above: above + 3pt, below: below,
  stroke: 0.7pt + brass, inset: (x: 11pt, top: 11pt, bottom: 10pt), {
    place(top + left, dx: -14pt, dy: -14pt, ornament("corner.svg", width: 20pt))
    place(bottom + right, dx: 14pt, dy: 13pt, pdf.artifact(rotate(180deg, image("../ornaments/corner.svg", width: 20pt))))
    if title != none { align(center, caps-label(title, fill: brass, size: 8.2pt)); v(0.25em) }
    framed-text(body)
  })

// The secret: a sealed charter, a navy frame with a brass inner line and a
// teal seal hanging from its foot.
#let secret-frame(title: none, body, fill: "grey", seed: 5, above: 1.3em, below: 1.1em, labels: (:), stamp: true) = {
  let paint = fills.at(if fill == "beige" { "beige" } else { "grey" })
  block(width: 100%, breakable: false, above: above, below: below + 10pt, layout(size => {
    let w = size.width
    let inner = block(width: w - 28pt, {
      if title != none { align(center, spaced-caps(title, fill: ink, size: 8.4pt)); v(0.4em) }
      framed-text(body)
    })
    let h = measure(inner).height + 30pt
    box(width: w, height: h, {
      pdf.artifact({
        place(top + left, rect(width: w, height: h, fill: paint, stroke: 1.2pt + accent))
        place(top + left, dx: 4pt, dy: 4pt, rect(width: w - 8pt, height: h - 8pt, stroke: 0.5pt + brass))
        place(top + left, dx: w - 34pt, dy: h - 11pt, image("../ornaments/seal.svg", width: 22pt))
      })
      place(top + left, dx: 14pt, dy: 12pt, inner)
    })
  }))
}

// Read-aloud as a captain's log entry: the label in a narrow column at the
// left, the text in italics beside it.
#let read-aloud-frame(heading, body) = block(width: 100%, breakable: false, above: 1.1em, below: 1.1em,
  grid(columns: (38pt, 1fr), column-gutter: 9pt, stroke: (x, y) => if x == 0 { (right: 0.7pt + brass) },
    inset: (x, y) => if x == 0 { (right: 6pt, y: 2pt) } else { (y: 2pt) },
    text(font: fonts.label, size: 6.8pt, tracking: 0.08em, fill: brass, upper(heading)),
    frame-par(text(font: fonts.read, size: sizes.read, style: "italic", body))))

// Pacing note: a thin brass border, a faint tint and an hourglass.
#let pacing-frame(body) = block(
  width: 100%, breakable: false, fill: pacing-tint, stroke: 0.5pt + brass,
  inset: (x: 8pt, y: 7pt), above: 1em, below: 1em,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt), frame-par(text(size: 0.95em, body))))

// Act headings: a compass rose between double brass rules, then the title.
#let act-heading(body) = {
  set text(font: fonts.display, size: sizes.act, weight: "bold", fill: ink, hyphenate: false)
  set par(justify: false, leading: 0.4em)
  let rules = box(width: 100%, height: 3pt, stroke: (top: 0.9pt + brass, bottom: 0.4pt + brass))
  align(center, grid(columns: (1fr, auto, 1fr), column-gutter: 8pt, align: horizon,
    pdf.artifact(rules), ornament("compass.svg", width: 34pt), pdf.artifact(rules)))
  align(center, block(width: 100%, above: 0.3em, body))
}

#let scene-title(body) = block(width: 100%, stroke: (bottom: 0.8pt + brass), inset: (bottom: 2.5pt),
  text(font: fonts.head, size: sizes.scene, weight: "bold", fill: ink, hyphenate: false, body))

// The page number between two stars.
#let page-number(n) = box({
  box(baseline: 0.1em, ornament("star.svg", height: 0.75em))
  h(5pt)
  text(font: fonts.head, size: 8.5pt, fill: ink, n)
  h(5pt)
  box(baseline: 0.1em, ornament("star.svg", height: 0.75em))
})

// Creature stats in a banded table between brass rules.
#let stat-row(stats) = block(width: 100%, above: gap(spacing.small), breakable: false,
  stroke: (top: 0.8pt + brass, bottom: 0.8pt + brass), {
    set par(justify: false)
    grid(columns: stats.len() * (1fr,), inset: (x: 2pt, y: 3pt), align: center + horizon,
      fill: (x, y) => if y == 0 { band } else { none },
      ..stats.map(s => text(font: fonts.label, size: 6.8pt, weight: "bold", fill: ink, upper(s.label))),
      ..stats.map(s => text(font: fonts.body, size: 11pt, weight: "bold", fill: ink, if s.value == none { [–] } else { str(s.value) })),
    )
  })
'''


# --- ornaments: the project's own drawings ------------------------------------------------
def svg(view: str, body: str) -> str:
    w, h = view.split()[2:]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" width="{w}" height="{h}">{body}</svg>\n'


def hourglass(frame: str, sand: str) -> str:
    return svg("0 0 24 32",
               f'<path d="M3,2 H21 M3,30 H21" stroke="{frame}" stroke-width="2" stroke-linecap="round"/>'
               f'<path d="M6,3 C6,11 11,13 11,16 C11,19 6,21 6,29 M18,3 C18,11 13,13 13,16 C13,19 18,21 18,29" fill="none" stroke="{frame}" stroke-width="1.3"/>'
               f'<path d="M8.2,8 C9,11.5 11.3,13.3 12,14.4 C12.7,13.3 15,11.5 15.8,8 Z" fill="{sand}"/>'
               f'<path d="M12,16 L12,22" stroke="{sand}" stroke-width="0.8"/>'
               f'<path d="M7.4,28 C8.5,24 10.5,22.6 12,22.4 C13.5,22.6 15.5,24 16.6,28 Z" fill="{sand}"/>')


def scroll_band(w: int, h: int, col: str) -> str:
    # A running scroll of vines and leaves between double rules (WHFRP).
    cy = h / 2
    d, leaves = [], []
    x, up = 0, True
    while x < w:
        s = -1 if up else 1
        d.append(f"M{x} {cy} q10 {s * 9} 20 0")
        leaves.append(f"M{x + 10} {cy + s * 4.5} q3 {s * 4} 7 {s * 1} q-4 {-s * 1} -7 {-s * 1}z")
        x += 20
        up = not up
    return svg(f"0 0 {w} {h}",
               f'<rect x="0" y="0" width="{w}" height="{h}" fill="#FFFFFF"/>'
               f'<path d="M0 2 H{w} M0 {h - 2} H{w}" stroke="{col}" stroke-width="1.6"/>'
               f'<path d="M0 5 H{w} M0 {h - 5} H{w}" stroke="{col}" stroke-width="0.5"/>'
               f'<path d="{" ".join(d)}" fill="none" stroke="{col}" stroke-width="1"/>'
               f'<path d="{" ".join(leaves)}" fill="{col}"/>')


def tor_band(w: int, h: int, col: str) -> str:
    # An even band of small diamonds and scrolls between double rules, with a
    # larger diamond in the middle (The One Ring).
    cy = h / 2
    dia, scr = [], []
    x = 12
    while x < w - 10:
        if abs(x - w / 2) > 34:
            dia.append(f"M{x - 4} {cy} l4 -3.5 l4 3.5 l-4 3.5z")
            scr.append(f"M{x + 5} {cy} q4 -5 8 0 q-4 5 -8 0")
        x += 22
    c = w / 2
    return svg(f"0 0 {w} {h}",
               f'<path d="M0 3 H{w} M0 {h - 3} H{w}" stroke="{col}" stroke-width="1.4"/>'
               f'<path d="M0 6 H{w} M0 {h - 6} H{w}" stroke="{col}" stroke-width="0.5"/>'
               f'<path d="{" ".join(dia)}" fill="{col}"/>'
               f'<path d="{" ".join(scr)}" fill="none" stroke="{col}" stroke-width="0.9"/>'
               f'<path d="M{c - 30} {cy} L{c} {cy - 13} L{c + 30} {cy} L{c} {cy + 13}Z" fill="#FFFFFF" stroke="{col}" stroke-width="1.3"/>'
               f'<path d="M{c - 24} {cy} L{c} {cy - 9.5} L{c + 24} {cy} L{c} {cy + 9.5}Z" fill="none" stroke="{col}" stroke-width="0.6"/>')


SKULL = ('<path d="M-12 40 Q-19 30 -16 18 M12 40 Q19 30 16 18" fill="none" stroke="#7B5E34" stroke-width="1.3"/>'
         '<path d="M-16 34 q-5 -1 -6 -5 q5 0 6 5z M-17 28 q-5 -2 -5 -6 q5 1 5 6z M-16 22 q-4 -3 -3 -7 q4 2 3 7z '
         'M16 34 q5 -1 6 -5 q-5 0 -6 5z M17 28 q5 -2 5 -6 q-5 1 -5 6z M16 22 q4 -3 3 -7 q-4 2 -3 7z" fill="#7B5E34"/>'
         '<path d="M0 10 C -9 10 -13 16 -13 22 C -13 27 -10 29 -8 30 L -8 35 L 8 35 L 8 30 C 10 29 13 27 13 22 C 13 16 9 10 0 10 Z" fill="#FFFFFF" stroke="#161412" stroke-width="1.6"/>'
         '<path d="M-8.5 20 q4 -2.5 6 1 q-1 4 -4.5 4 q-3 -1 -1.5 -5z M8.5 20 q-4 -2.5 -6 1 q1 4 4.5 4 q3 -1 1.5 -5z" fill="#161412"/>'
         '<path d="M0 25 l-1.8 3.5 h3.6z" fill="#161412"/>'
         '<path d="M-5 31 V35 M-1.7 31 V35 M1.7 31 V35 M5 31 V35" stroke="#161412" stroke-width="1"/>')
SHIELD = '<path d="M-30 2 H30 V30 Q30 44 0 51 Q-30 44 -30 30Z" fill="#FFFFFF" stroke="#161412" stroke-width="2"/><path d="M-26 6 H26 V30 Q26 41 0 47 Q-26 41 -26 30Z" fill="none" stroke="#7B5E34" stroke-width="0.9"/>'


def wh40k_band(w: int) -> str:
    rivets = "".join(f'<circle cx="{x}" cy="19" r="1.6" fill="#7B5E34"/>' for x in (8, w - 8))
    c = w / 2
    return svg(f"0 0 {w} 52",
               f'<rect x="0" y="8" width="{w}" height="22" fill="#161412"/>'
               f'<path d="M0 11 H{w} M0 27 H{w}" stroke="#7B5E34" stroke-width="0.8"/>'
               f'<path d="M0 33 H{w}" stroke="#161412" stroke-width="1.2"/>' + rivets +
               f'<g transform="translate({c} 0)">{SHIELD}{SKULL}</g>')


ORNAMENTS = {
    "scriptorum.whfrp": {
        "band.svg": scroll_band(794, 26, "#4A443C"),
        "medallion.svg": svg("0 0 84 84",
            '<circle cx="42" cy="42" r="40" fill="#4A443C"/>'
            '<circle cx="42" cy="42" r="36" fill="#DFE5D8" stroke="#FFFFFF" stroke-width="1"/>'
            '<circle cx="42" cy="42" r="31" fill="none" stroke="#4A443C" stroke-width="0.8"/>'
            '<path d="M22 50 q2 -14 20 -26 q18 12 20 26" fill="none" stroke="#3F5A3C" stroke-width="1.6"/>'
            '<path d="M24 46 q-6 -3 -4 -9 q6 2 4 9z M27 39 q-5 -4 -1 -9 q5 3 1 9z M32 33 q-3 -6 3 -8 q2 5 -3 8z '
            'M60 46 q6 -3 4 -9 q-6 2 -4 9z M57 39 q5 -4 1 -9 q-5 3 -1 9z M52 33 q3 -6 -3 -8 q-2 5 3 8z" fill="#3F5A3C"/>'
            '<path d="M30 56 q12 8 24 0" fill="none" stroke="#3F5A3C" stroke-width="1.6"/>'
            '<circle cx="42" cy="42" r="6" fill="#3F5A3C"/>'),
        "tab.svg": svg("0 0 34 92",
            '<path d="M1 0 H33 V80 L17 91 L1 80Z" fill="#5E3B5C"/>'
            '<path d="M4 0 V78 L17 87 L30 78 V0" fill="none" stroke="#D9C9D8" stroke-width="0.7"/>'
            '<circle cx="17" cy="62" r="5" fill="none" stroke="#FFFFFF" stroke-width="1.2"/>'),
        "hourglass.svg": hourglass("#1F1C18", "#3F5A3C"),
    },
    "scriptorum.the-one-ring": {
        "band.svg": tor_band(694, 26, "#A3262A"),
        "vine.svg": svg("0 0 30 30",
            '<path d="M4 26 q0 -22 22 -22" fill="none" stroke="#A3262A" stroke-width="1.3"/>'
            '<path d="M8 18 q4 -6 10 -2 q-4 4 -10 2z M18 8 q6 -4 8 2 q-4 2 -8 -2z M5 24 q-3 -4 1 -6 q1 3 -1 6z" fill="#A3262A"/>'),
        "brush.svg": svg("0 0 70 20",
            '<path d="M68 9 C 52 5, 34 4, 18 10 C 12 12, 6 13, 2 11 C 7 14, 14 15, 20 13 C 34 8, 50 8, 68 9 Z" fill="#8A7A6A"/>'
            '<path d="M10 9 q-6 -6 -2 -8" fill="none" stroke="#8A7A6A" stroke-width="1.2"/>'),
        "lozenge.svg": svg("0 0 16 16", '<path d="M8 1 L15 8 L8 15 L1 8Z" fill="#A3262A"/>'),
        "hourglass.svg": hourglass("#5A4632", "#A3262A"),
    },
    "scriptorum.wh40krp": {
        "band.svg": wh40k_band(794),
        "skull.svg": svg("-32 0 64 54", SHIELD + SKULL),
        "shield.svg": svg("0 0 30 34", '<path d="M2 2 H28 V18 Q28 28 15 32 Q2 28 2 18Z" fill="#FFFFFF" stroke="#161412" stroke-width="1.6"/>'),
        "hourglass.svg": hourglass("#161412", "#7A1F1F"),
    },
    "scriptorum.rogue-trader": {
        "compass.svg": svg("-32 -32 64 64",
            '<circle r="28" fill="#FFFFFF" stroke="#1E2A44" stroke-width="1.2"/>'
            '<circle r="22" fill="none" stroke="#8A6A2E" stroke-width="0.7" stroke-dasharray="1.5 2.5"/>'
            '<path d="M0 -31 L5 -5 L31 0 L5 5 L0 31 L-5 5 L-31 0 L-5 -5Z" fill="#1E2A44"/>'
            '<path d="M0 -31 L5 -5 L0 0Z M31 0 L5 5 L0 0Z M0 31 L-5 5 L0 0Z M-31 0 L-5 -5 L0 0Z" fill="#FFFFFF"/>'
            '<path d="M14 -14 L3 -1 L-14 14 L-3 1Z M-14 -14 L-1 -3 L14 14 L1 3Z" fill="#2B6B6E"/>'
            '<circle r="2.5" fill="#8A6A2E"/>'),
        "star.svg": svg("0 0 16 16", '<path d="M8 0 L10 6 L16 8 L10 10 L8 16 L6 10 L0 8 L6 6Z" fill="#8A6A2E"/>'),
        "corner.svg": svg("0 0 24 24",
            '<path d="M2 22 V8 Q2 2 8 2 H22 M6 18 q0 -10 8 -10 q-4 4 -2 6 q2 2 4 -2" fill="none" stroke="#8A6A2E" stroke-width="1.3"/>'
            '<circle cx="2" cy="22" r="1.6" fill="#8A6A2E"/><circle cx="22" cy="2" r="1.6" fill="#8A6A2E"/>'),
        "seal.svg": svg("0 0 60 56",
            '<path d="M22 4 V30 M38 4 V30" stroke="#2B6B6E" stroke-width="3"/>'
            '<path d="M30 22 q-4 -2 -8 0 q-4 2 -6 8 q-4 6 2 12 q2 6 8 8 q6 2 10 -2 q6 -2 8 -8 q2 -8 -4 -12 q-4 -6 -10 -6z" fill="#FFFFFF" stroke="#2B6B6E" stroke-width="2"/>'
            '<path d="M30 28 l2.4 5 l5.6 .8 l-4 3.9 l1 5.5 l-5 -2.6 l-5 2.6 l1 -5.5 l-4 -3.9 l5.6 -.8z" fill="#2B6B6E"/>'),
        "hourglass.svg": hourglass("#1E2A44", "#2B6B6E"),
    },
}


# --- handout papers (F6.5: never filled; marks pale) -----------------------------------------
def paper(pid, outline, inner, ink, edge_mm=1.0, corner="none", folds=(0, 1), marks=None, **extra):
    p = {"id": pid, "label": f"paper.{pid}", "outline": outline, "inner": inner, "edge_mm": edge_mm,
         "corner": corner, "folds": list(folds)}
    p.update(extra)
    m = {"colour": inner, "opacity": 0.14, "spots": [0, 2], "stains": [0, 1], "tears": [0, 0]}
    m.update(marks or {})
    p["marks"] = m
    p["ink"] = ink
    return p


RULES = ("F6.5: the paper is never filled with a colour; outline, inner line, folds, marks and ink "
         "may be coloured; stains stay pale (opacity at most 0.2).")

THEMES = [
    {
        "id": "scriptorum.whfrp", "name": "WHFRP", "head": WHFRP_HEAD, "frames": WHFRP_FRAMES,
        "description": ("A general theme for any game system: grim fantasy after the look of the "
                        "4th-edition WFRP books, in dark grey-brown ink with grey panels with torn edges, "
                        "a plum chapter tab, a green medallion, Libre Caslon Display headings and Crimson "
                        "Text. " + UNOFFICIAL),
        "page": {"font": "Crimson Text", "font_size_pt": 10.5},
        "papers": [
            paper("notice", "#3A352E", "#B7B1A7", "#1F1C18", edge_mm=1.4, corner="none", folds=(0, 1),
                  marks={"colour": "#8A8378", "spots": [4, 4], "spot_mm": 1.4, "opacity": 0.18, "stains": [0, 1], "tears": [1, 2]}),
            paper("tavern-bill", "#5B5246", "#C9C1B2", "#2A2520", edge_mm=0.8, corner="curl", folds=(1, 2),
                  ruled={"colour": "#D8D2C8", "gap_mm": 7}, marks={"colour": "#9A8E7A", "rings": [0, 1], "opacity": 0.12}),
        ],
        "labels": {"paper.notice": "Nailed-up notice", "paper.tavern-bill": "Tavern bill", "print.page": "Page"},
        "fonts_note": "Libre Caslon Display and Crimson Text (SIL OFL 1.1), from Google Fonts.",
    },
    {
        "id": "scriptorum.the-one-ring", "name": "The One Ring", "head": TOR_HEAD, "frames": TOR_FRAMES,
        "description": ("A general theme for any game system: warm brown ink with brick red, Uncial "
                        "Antiqua headings, EB Garamond text and Josefin Sans labels, bands of red diamonds, "
                        "leafy vine corners and stats in red diamonds. " + UNOFFICIAL +
                        " The One Ring is a game by Free League Publishing."),
        "page": {"font": "EB Garamond", "font_size_pt": 10.5},
        "papers": [
            paper("vellum", "#8A6E4E", "#C9B28F", "#2A3550", edge_mm=0.6, corner="round", folds=(1, 2),
                  edge="soft", marks={"colour": "#A3262A", "spots": [0, 1], "stains": [0, 0], "opacity": 0.1}),
            paper("journey-log", "#6B5A4A", "#D6C7AD", "#2B2622", edge_mm=1.1, corner="fold", folds=(0, 1),
                  ruled={"colour": "#E2D6C2", "gap_mm": 7.5}, marks={"colour": "#A99878", "stains": [0, 1], "opacity": 0.12}),
        ],
        "labels": {"paper.vellum": "Vellum letter", "paper.journey-log": "Journey log", "print.page": "Page"},
        "fonts_note": ("Uncial Antiqua (SIL OFL 1.1) from Google Fonts; EB Garamond (SIL OFL 1.1), the same files "
                       "as in the Call of Cthulhu theme; Josefin Sans (SIL OFL 1.1), static weights from its own "
                       "project (github.com/ThomasJockin/JosefinSansFont-master)."),
    },
    {
        "id": "scriptorum.wh40krp", "name": "WH40KRP", "head": WH40K_HEAD, "frames": WH40K_FRAMES,
        "description": ("A general theme for any game system: grimdark gothic, near-black and bone with "
                        "dark bronze and a deep red, Grenze Gotisch headings, Spectral text and Share Tech "
                        "Mono labels, a black band, a skull over laurels, pointed arches and a dossier with a "
                        "Clearance stamp. " + UNOFFICIAL),
        "page": {"font": "Spectral", "font_size_pt": 9.5},
        "papers": [
            paper("printout", "#4A4038", "#9A8F84", "#222222", edge_mm=0.15, corner="none", folds=(1, 2),
                  marks={"colour": "#9A8F84", "spots": [0, 1], "opacity": 0.1}),
            paper("writ", "#1E1B18", "#7B5E34", "#161412", edge_mm=0.5, corner="none", folds=(1, 2),
                  marks={"colour": "#7A1F1F", "spots": [0, 1], "stains": [0, 0], "opacity": 0.12}),
        ],
        "labels": {"paper.printout": "Punched printout", "paper.writ": "Official writ",
                   "print.clearance": "Clearance", "print.page": "Page"},
        "fonts_note": ("Spectral and Share Tech Mono (SIL OFL 1.1) from Google Fonts; Grenze Gotisch (SIL OFL "
                       "1.1), static weights from its own project (github.com/Omnibus-Type/Grenze-Gotisch)."),
    },
    {
        "id": "scriptorum.rogue-trader", "name": "Rogue Trader", "head": RT_HEAD, "frames": RT_FRAMES,
        "description": ("A general theme for any game system: baroque explorers and merchant princes in "
                        "deep navy ink with brass brown and a teal accent, Cinzel Decorative and Cinzel "
                        "headings, Cormorant Garamond text, a compass rose, star bullets and a sealed charter. "
                        + UNOFFICIAL),
        "page": {"font": "Cormorant Garamond", "font_size_pt": 11},
        "papers": [
            paper("star-chart", "#1E2A44", "#B9C6D6", "#1E2A44", edge_mm=0.6, corner="round", folds=(1, 2),
                  edge="soft", ruled={"colour": "#DCE3EB", "gap_mm": 9}, marks={"colour": "#8FA3B8", "spots": [2, 5], "spot_mm": 0.8, "opacity": 0.18}),
            paper("manifest", "#8A6A2E", "#D4C3A0", "#1E2A44", edge_mm=0.4, corner="none", folds=(0, 1),
                  ruled={"colour": "#E4DAC6", "gap_mm": 7}, marks={"colour": "#A99878", "stains": [0, 1], "opacity": 0.1}),
        ],
        "labels": {"paper.star-chart": "Star chart", "paper.manifest": "Ship's manifest", "print.page": "Page"},
        "fonts_note": ("Cinzel Decorative (SIL OFL 1.1) from Google Fonts; Cinzel (SIL OFL 1.1), static weights "
                       "from its own project (github.com/NDISCOVER/Cinzel); Cormorant Garamond (SIL OFL 1.1), the "
                       "same files as in the Vaesen theme."),
    },
]

PAGE = {"paper": "a4", "columns": 2, "column_gap_mm": 7, "margin_mm": {"top": 22, "bottom": 24, "x": 17},
        "page_numbers": True}


def write_extras(t: dict) -> None:
    target = BUNDLED / t["id"]
    orn = target / "ornaments"
    orn.mkdir(parents=True, exist_ok=True)
    for old in orn.glob("*.svg"):
        old.unlink()
    for name, text in ORNAMENTS[t["id"]].items():
        (orn / name).write_text(text, "utf-8")
    (target / "labels").mkdir(exist_ok=True)
    (target / "labels" / "en.json").write_text(json.dumps(t["labels"], ensure_ascii=False, indent=2) + "\n", "utf-8")
    page = dict(PAGE)
    page.update(t["page"])
    (target / "page.json").write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", "utf-8")
    (target / "settings.json").write_text(json.dumps({"settings": []}, indent=2) + "\n", "utf-8")
    (target / "handouts.json").write_text(json.dumps({"papers": t["papers"], "rules": RULES}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    manifest = {"id": t["id"], "kind": "theme", "name": t["name"], "version": "1.0.0", "format": 1, "app": "1.0.0",
                "licence": "GPL-3.0-or-later", "authors": ["Scriptorum project"], "description": t["description"],
                "requires": [{"id": "scriptorum.core", "version": "1.x"}]}
    (target / "module.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    (target / "LICENSE.txt").write_text(
        f"{t['name']} — a general theme for Scriptorum\n\n"
        "Copyright (C) 2026 Scriptorum project. Licensed under the GNU General Public\n"
        "License, version 3 or later (GPL-3.0-or-later); see COPYING in Scriptorum.\n\n"
        f"{UNOFFICIAL}\n"
        "It uses no text, artwork or logos from any publisher. Its frames and\n"
        "ornaments are the project's own drawings (tools/make_more_themes.py).\n\n"
        f"Fonts in fonts/ keep their own licences, each in the licence file beside the font:\n{t['fonts_note']}\n\n"
        "The relationship chart uses fletcher 0.5.8 (MIT), CeTZ 0.3.4\n"
        "(LGPL-3.0-or-later) and oxifmt 0.2.1 (MIT-0) in vendor/, each with its licence file.\n", "utf-8")


def main() -> None:
    for t in THEMES:
        write_theme(t["id"], t["head"], t["frames"])
        write_extras(t)


if __name__ == "__main__":
    main()
