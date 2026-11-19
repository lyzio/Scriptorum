// Shared look of the scriptorum.wh40krp theme, written by tools/make_general_themes.py from the Vaesen theme (F8; graphics and fonts decided 6 Nov 2026,
// built in M4, approved mockups 12.2 to 12.4).
//
// Every template of this theme draws through the functions here, so the
// three bundled themes share their templates and differ only in this file,
// their ornaments, fonts, papers and page setup (F8 general themes).
//
// Frames, curls, the scroll, the pen-nib bullet and the hourglass are the
// project's own vector drawings in ../ornaments/ (tools/make_ornaments.py).
// They are decoration: screen readers skip them (F17.4).

// --- colours -------------------------------------------------------------------
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

// --- spacing (F8, decided 12 November 2026, built in M6 part C) --------------------
// The theme's spacing, set once here. Every template uses these values, so
// cards, boxes, read-aloud text and lists are spaced alike, and a theme
// changes its spacing in this one place (How to write a theme, "Spacing").
//   small, medium, large: the spacing scale, gaps between the parts of a card
//   leading:   line spacing in running text, and inside cards and boxes too
//   paragraph: space between paragraphs in running text
//   in-frame:  space between paragraphs inside cards and boxes
//   label:     the tighter line spacing of one-line labels such as "PUBLIC"
#let spacing = (small: 3pt, medium: 6pt, large: 10pt, leading: 0.8em, paragraph: 1.2em, in-frame: 10pt, label: 0.5em)

// F4, F7.7 (M6 part C): Sub-heading 1, 2 and 3 inside a scene are heading
// levels 3, 4 and 5, drawn smaller than a scene's title in the theme's own
// fonts and colours. _page.typ keeps each with what follows it, so none is
// left alone at the foot of a page or column, and none starts a page.
#let sub-heading-style(level, body) = {
  if level == 3 {
    text(font: fonts.head, size: 12pt, weight: "bold", fill: accent, body)
  } else if level == 4 {
    text(font: fonts.head, size: 10.5pt, weight: "bold", style: "italic", fill: accent, body)
  } else {
    text(font: fonts.label, size: 8.6pt, weight: "regular", tracking: 0.08em, fill: accent, upper(body))
  }
}
#let sub-heading-space = ((above: 1.8em, below: 1em), (above: 1.6em, below: 0.9em), (above: 1.5em, below: 0.85em))

// A gap between two parts of a card: one line's spacing plus the step from
// the scale, so a "small gap" is always a little more than between lines.
#let gap(step) = spacing.leading + step

// Text inside cards, boxes and other framed elements: the same line spacing
// as running text, and left-aligned, so no wide gaps open between words in
// a narrow frame. Running text on the page stays justified (_page.typ).
#let frame-par(body) = {
  set par(justify: false, leading: spacing.leading, spacing: spacing.in-frame)
  body
}

// 11.4 (M6 part C): a person's portrait, in the theme's thin frame, at about
// a third of the card's width. Its height follows the picture; it is never
// cropped. A theme may change the width, but never leave the picture out.
#let portrait-width = 33%
#let portrait-frame(picture) = block(width: 100%, stroke: 0.5pt + accent, inset: 1.5pt, picture)

// --- small helpers -----------------------------------------------------------
// The Quote's scrap tint and the ink of a handwritten quote (11.11). They live
// here so a theme can change them (the Plain theme prints them in grey, F8).
#let quote-tint = rgb("#F4ECD9")
#let hand-ink = rgb("#2A2520")
#let label(labels, key) = labels.at(key, default: key)
#let blank(value) = value == none or value == "" or value == []

// True when content holds nothing to print: only spaces and paragraph breaks,
// such as the empty body of a person card, [ ] (11.4: "What they know" is
// printed only when something is under it).
#let empty-body(c) = {
  if c == none or c == "" or c == [] { return true }
  if type(c) == str { return c.trim() == "" }
  if type(c) != content { return false }
  let f = c.func()
  if f == [ ].func() or f == parbreak or f == linebreak { return true }
  if f == [].func() { return c.children.all(empty-body) }
  if f == text { return c.text.trim() == "" }
  false
}

// Labels such as "MIGHT" or "MAIN ATTRIBUTE:" and box titles: bold capitals in Acme.
#let small-caps-label(body, fill: accent) = text(
  font: fonts.label, size: sizes.label, tracking: 0.1em, fill: fill, upper(body),
)
#let caps-label(body, fill: accent, size: 8.6pt) = text(font: fonts.label, size: size, tracking: 0.06em, fill: fill, upper(body))
// Widely spaced small capitals for the secret box title and the scene number.
#let spaced-caps(body, fill: accent, size: 8.4pt, tracking: 0.26em) = text(
  font: fonts.head, size: size, tracking: tracking, fill: fill, weight: "regular", upper(body),
)

#let ornament(name, ..args) = pdf.artifact(image("../ornaments/" + name, ..args))

// A deterministic number in [0, 1) from two integers (F7.8: same every build).
#let _noise(seed, i) = {
  let x = calc.sin(seed * 12.9898 + i * 78.233) * 43758.5453
  x - calc.floor(x)
}

// A slightly uneven pen rule from (x0, y0) to (x1, y1).
#let rough(x0, y0, x1, y1, seed: 1, amp: 0.45pt, stroke: 1pt + accent) = {
  let n = 9
  let horizontal = calc.abs((y1 - y0) / 1pt) < calc.abs((x1 - x0) / 1pt)
  let pts = range(n + 1).map(i => {
    let t = i / n
    let j = (_noise(seed, i) - 0.5) * 2 * amp
    if i == 0 or i == n { j = 0pt }
    (x0 + (x1 - x0) * t + (if horizontal { 0pt } else { j }), y0 + (y1 - y0) * t + (if horizontal { j } else { 0pt }))
  })
  curve(stroke: (paint: stroke.paint, thickness: stroke.thickness, cap: "round", join: "round"),
    curve.move(pts.first()), ..pts.slice(1).map(p => curve.line(p)))
}

// 11.10, T-LOOK-03: bold text at the start of a line or list item prints as
// a label in bold capitals, with the value in normal text.
#let label-style(it) = text(font: fonts.label, tracking: 0.04em, fill: accent, upper(it))
#let labelize(c) = {
  if c == none { return none }
  let seq = [].func()
  if c.func() == strong { return label-style(c.body) }
  if c.func() == list.item { return list.item(labelize(c.body)) }
  if c.func() == enum.item { return enum.item(c.number, labelize(c.body)) }
  if c.func() == list { return list(..c.children.map(labelize)) }
  if c.func() == enum { return enum(..c.children.map(labelize)) }
  if c.func() != seq { return c }
  let start = true
  let out = ()
  for ch in c.children {
    let f = ch.func()
    if f == [ ].func() { out.push(ch); continue }
    if start and f == strong { out.push(label-style(ch.body)); start = false; continue }
    if f == parbreak or f == linebreak { out.push(ch); start = true; continue }
    if f in (list.item, enum.item, list, enum) { out.push(labelize(ch)); start = true; continue }
    out.push(ch)
    start = false
  }
  out.join()
}

// Inside frames: pen-nib bullets (F8), left-aligned (M6 part C).
#let framed-text(body) = frame-par({
  set list(marker: bullet, body-indent: 0.5em)
  labelize(body)
})

// --- frames ----------------------------------------------------------------------
// The open curl frame (F8): hand-drawn brown rules along the top and bottom; a
// side line runs down from the top-left corner part of the way and another
// rises to the bottom-right corner, with a spiral curl on those two corners.
// The title is centred in bold capitals. Used for Hint and Public Information,
// the check, the creature stat block and the Box (11.10).
#let curl-frame(title: none, body, seed: 3, above: 1.1em, below: 1.1em, breakable: false) = {
  let draw(w, h) = pdf.artifact({
    let s = 1.05pt + accent
    place(top + left, rough(9pt, 0pt, w, 0pt, seed: seed, stroke: s))
    place(top + left, rough(0pt, h, w - 9pt, h, seed: seed + 1, stroke: s))
    place(top + left, rough(0pt, 10pt, 0pt, calc.max(16pt, h * 0.42), seed: seed + 2, amp: 0.3pt, stroke: 0.9pt + accent))
    place(top + left, rough(w, calc.min(h - 16pt, h * 0.58), w, h - 10pt, seed: seed + 3, amp: 0.3pt, stroke: 0.9pt + accent))
    place(top + left, dx: -8.6pt, dy: -4.3pt, image("../ornaments/curl.svg", width: 17pt))
    place(top + left, dx: w - 8.4pt, dy: h - 12.7pt, rotate(180deg, image("../ornaments/curl.svg", width: 17pt)))
  })
  // A creature taller than a column may break between its sections (11.5):
  // then the rules are the block's own top and bottom edges.
  if breakable {
    return block(width: 100%, breakable: true, above: above, below: below,
      stroke: (top: 1.05pt + accent, bottom: 1.05pt + accent), inset: (x: 9pt, top: 10.5pt, bottom: 9.5pt), {
        place(top + left, dx: -17.6pt, dy: -14.8pt, ornament("curl.svg", width: 17pt))
        if title != none { align(center, caps-label(title, size: 9.2pt)); v(0.25em) }
        framed-text(body)
        place(bottom + right, dx: 17.6pt, dy: 14.6pt, pdf.artifact(rotate(180deg, image("../ornaments/curl.svg", width: 17pt))))
      })
  }
  block(width: 100%, breakable: false, above: above, below: below, inset: (x: 3pt), layout(size => {
    let w = size.width
    let inner = block(width: w - 18pt, {
      if title != none {
        align(center, caps-label(title, size: 9.2pt))
        v(0.25em)
      }
      framed-text(body)
    })
    let h = measure(inner).height + 20pt
    box(width: w, height: h, {
      draw(w, h)
      place(top + left, dx: 9pt, dy: 10.5pt, inner)
    })
  }))
}

// The secret box (F8): a double frame, a heavy dark-brown outer line and a thin
// inner line, both slightly worn; a small red scroll centred at the top; the
// title in widely spaced small capitals; a pale grey or pale beige fill
// (the adventure's choice, F7.3). Also the Framed look of the Quote (11.11).
// M4-0.4.2: the scroll sits inside the box, just under the inner top line;
// both lines run whole, and nothing is drawn above the frame.
#let secret-frame(title: none, body, fill: "grey", seed: 5, above: 1.3em, below: 1.1em, labels: (:), stamp: true) = {
  let paint = fills.at(if fill == "beige" { "beige" } else { "grey" })
  let scroll-w = 46pt                 // the scroll drawing, 100 × 24 units
  let scroll-h = scroll-w * 24 / 100
  let d = 3.6pt                       // the inner line, this far inside the outer one
  let scroll-top = d + 2.4pt          // a small gap under the inner line
  block(width: 100%, breakable: false, above: above, below: below, layout(size => {
    let w = size.width
    let inner = block(width: w - 26pt, {
      if title != none {
        align(center, spaced-caps(title))
        v(0.5em)
      }
      framed-text(body)
    })
    // The text starts below the scroll, with as much room again under it.
    let top-room = scroll-top + scroll-h + 6pt
    let h = measure(inner).height + top-room + 12pt
    box(width: w, height: h, {
      pdf.artifact({
        place(top + left, rect(width: w, height: h, fill: paint, stroke: none))
        let heavy = 2.1pt + accent
        place(top + left, rough(0pt, 0pt, w, 0pt, seed: seed, amp: 0.35pt, stroke: heavy))
        place(top + left, rough(w, 0pt, w, h, seed: seed + 1, amp: 0.35pt, stroke: heavy))
        place(top + left, rough(w, h, 0pt, h, seed: seed + 2, amp: 0.35pt, stroke: heavy))
        place(top + left, rough(0pt, h, 0pt, 0pt, seed: seed + 3, amp: 0.35pt, stroke: heavy))
        let thin = 0.55pt + accent
        place(top + left, rough(d, d, w - d, d, seed: seed + 4, amp: 0.25pt, stroke: thin))
        place(top + left, rough(w - d, d, w - d, h - d, seed: seed + 5, amp: 0.25pt, stroke: thin))
        place(top + left, rough(w - d, h - d, d, h - d, seed: seed + 6, amp: 0.25pt, stroke: thin))
        place(top + left, rough(d, h - d, d, d, seed: seed + 7, amp: 0.25pt, stroke: thin))
        place(top + left, dx: w / 2 - scroll-w / 2, dy: scroll-top, image("../ornaments/scroll.svg", width: scroll-w))
      })
      place(top + left, dx: 13pt, dy: top-room, inner)
    })
  }))
}

// 11.2 Read-aloud: rules on the left and right only, the heading above.
#let read-aloud-frame(heading, body) = block(
  width: 100%,
  breakable: false,
  stroke: (left: 1.1pt + accent, right: 1.1pt + accent),
  inset: (x: 11pt, y: 6pt),
  above: 1.1em,
  below: 1.1em,
  {
    small-caps-label(heading)
    v(spacing.small)
    frame-par(text(font: fonts.read, size: sizes.read, style: "italic", body))
  },
)

// 11.12 Pacing note: a small hourglass on the left, a thin brown border (not
// bold) and a faint warm-grey tint.
#let pacing-frame(body) = block(
  width: 100%,
  breakable: false,
  fill: pacing-tint,
  stroke: 0.5pt + accent,
  inset: (x: 8pt, y: 7pt),
  above: 1em,
  below: 1em,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt),
    frame-par(text(size: 0.95em, body))),
)

// The act heading, centred over both columns (F7.4); the title page uses the
// same display face, so an act heading never looks like a scene (F8).
#let act-heading(body) = {
  set text(font: fonts.display, size: sizes.act, weight: "regular", fill: accent, hyphenate: false)
  set par(justify: false, leading: 0.4em)
  align(center, block(width: 100%, below: 0.2em, body))
  align(center, box(width: 40%, line(length: 100%, stroke: 0.7pt + accent)))
}

// The scene head (11.1): "SCENE 2 · CLIMAX" in spaced small capitals, then the
// title in Playfair Display.
#let scene-number(text-body) = spaced-caps(text-body, fill: quiet, size: 7.8pt, tracking: 0.22em)
#let scene-title(body) = text(font: fonts.head, size: sizes.scene, weight: "bold", fill: accent, hyphenate: false, body)

// Tables (F8): headings in bold capitals, rows in alternating pale beige bands,
// thin brown rules.
#let table-style(doc) = {
  set table(
    stroke: (x, y) => (bottom: if y == 0 { 0.9pt + accent } else { 0.4pt + rule-tint }),
    fill: (x, y) => if y > 0 and calc.even(y) { band } else { none },
    inset: (x: 5pt, y: 4pt),
  )
  show table.cell.where(y: 0): it => text(font: fonts.label, size: 0.88em, tracking: 0.05em, fill: accent, upper(it))
  // M6 part C: cells are narrow, so their text is left-aligned like text in
  // frames, and no wide gaps open between words (F8 spacing).
  show table.cell: set par(justify: false)
  doc
}

// Vector icons for the Information variants (F7.5).
#let icon(variant, color) = box(baseline: 0.12em, {
  if variant == "secret" {
    rotate(45deg, rect(width: 0.48em, height: 0.48em, fill: color))
  } else if variant == "public" {
    circle(radius: 0.28em, fill: color)
  } else {
    polygon(fill: color, (0em, 0.56em), (0.32em, 0em), (0.64em, 0.56em))
  }
})

// F3 (M6 part C4): the small clue mark, a magnifying glass drawn as
// vectors, beside the clue's name on an Information item. Decoration, so
// screen readers skip it; the clue's name is read instead.
#let clue-mark(color) = box(baseline: 0.1em, pdf.artifact(box(width: 0.62em, height: 0.62em, {
  place(dx: 0em, dy: 0em, circle(radius: 0.21em, stroke: 0.85pt + color))
  place(dx: 0.36em, dy: 0.36em, line(start: (0em, 0em), end: (0.24em, 0.24em), stroke: (paint: color, thickness: 1.3pt, cap: "round")))
})))

// A six-sided die drawn as vectors (F7.5). With no face it shows a blank
// die; a success face is filled.
#let die(face: none, size: 0.95em, success: false) = box(baseline: 0.15em, {
  let s = size
  let pips = (
    "1": ((0.5, 0.5),),
    "2": ((0.27, 0.27), (0.73, 0.73)),
    "3": ((0.25, 0.25), (0.5, 0.5), (0.75, 0.75)),
    "4": ((0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)),
    "5": ((0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)),
    "6": ((0.28, 0.22), (0.72, 0.22), (0.28, 0.5), (0.72, 0.5), (0.28, 0.78), (0.72, 0.78)),
  )
  let fill = if success { accent } else { white }
  let dot = if success { white } else { accent }
  box(width: s, height: s, {
    place(rect(width: s, height: s, radius: 0.18 * s, stroke: 0.8pt + accent, fill: fill))
    if face != none and str(face) in pips {
      for (x, y) in pips.at(str(face)) {
        place(dx: x * s - 0.07 * s, dy: y * s - 0.07 * s, circle(radius: 0.07 * s, fill: dot))
      }
    }
  })
})


// Shared state: true while a person card is being laid out, so Information
// lines inside it are drawn as short lines rather than boxes (11.3).
#let in-card = state("scriptorum-in-person", false)


// 11.10 (0.7.7, issue #31): inside a Box the Box is the only frame.
// Information, read-aloud, check, dice and pacing notes standing in a Box
// drop their own frame and are drawn as parts of the Box: each keeps its
// label, icon and colours (a fill such as the secret box's included), and a
// thin line in the rule colour separates it from the part before it. No
// line goes above the first part or below the last. Person and creature
// cards keep their frames. The Box marks its text with inside-box, which
// in-box() reads (in context). The mark is a style, not a state, so it holds
// at once, also while the Box measures its text: a state would need several
// layout passes and could run out of them. It rides on the gap of a math
// cases formula, which adventures never use. box-seen starts each Box off.
#let box-mark = 0.4321em
#let inside-box(body) = { set math.cases(gap: box-mark); body }
#let in-box() = math.cases.gap == box-mark
#let box-seen = state("scriptorum-box-seen", false)
#let box-part(head, body, fill: none) = {
  // The line's room is kept above every part, drawn or not: while the Box
  // measures its text, a part cannot see the parts before it, so the
  // measured height must not depend on them. At the top of the Box the
  // room collapses into the Box's own space above its text.
  context block(above: gap(spacing.small), below: 0pt, height: 0.5pt, width: 100%,
    if box-seen.get() { line(length: 100%, stroke: 0.5pt + rule-tint) })
  block(width: 100%, breakable: false, above: gap(spacing.small), below: gap(spacing.small),
    fill: fill, inset: if fill == none { 0pt } else { (x: 5pt, y: 5pt) }, {
      if head != none { head; v(spacing.small) }
      body
    })
  box-seen.update(true)
}
// The pacing note's look without its border: the tint and its mark.
#let box-pacing(body) = box-part(none, fill: pacing-tint,
  grid(columns: (14pt, 1fr), column-gutter: 8pt, align: (center + horizon, left),
    ornament("hourglass.svg", width: 11pt), frame-par(text(size: 0.95em, body))))


// F8 (0.7.8): two style hooks a theme may redefine after this point.
// page-background is drawn behind every page (none draws nothing);
// stat-row draws a creature's stats: here in one row between two rules
// ("MIGHT 4" with the label in bold capitals).
#let page-background = none
#let stat-row(stats) = block(
  width: 100%,
  stroke: (top: 0.7pt + accent, bottom: 0.7pt + accent),
  inset: (y: 5pt),
  above: gap(spacing.small),
  align(center, stats.map(s => box[
    #caps-label(s.label, size: 7pt)
    #h(0.2em)
    #text(size: 10.5pt, weight: "bold", fill: accent, if s.value == none { [–] } else { str(s.value) })
  ]).join(h(0.9em))),
)

#let seed-of(c) = if type(c) == str { c.len() } else { 3 }

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
