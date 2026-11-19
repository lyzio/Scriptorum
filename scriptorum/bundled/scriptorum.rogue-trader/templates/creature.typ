// 11.5 Creature, in the open curl frame (F8): name in capitals, type below
// it, the stats in one row between two rules ("MIGHT 4" with the label in
// bold capitals), then each section under its label. The banishment section
// sits between rust rules. The head is never split; a long creature may
// break only between its sections.

#import "_style.typ": accent, quiet, rust, label, small-caps-label, caps-label, blank, curl-frame, fonts, framed-text, spacing, gap, stat-row

#let render(f, body, labels) = curl-frame(breakable: true, seed: 41, {
  // F8 (M6 part C): spaced like the person card: a small gap after the
  // name and between the parts of the head, a medium gap before each section.
  block(width: 100%, breakable: false, below: spacing.medium, {
    align(center, text(font: fonts.head, size: 12.5pt, weight: "bold", tracking: 0.08em, fill: accent, upper(f.name)))
    if not blank(f.type) {
      align(center, small-caps-label(f.type, fill: quiet))
    }
    // F8 (0.7.8): the stats are drawn by the theme's stat-row.
    if f.stats.len() > 0 { stat-row(f.stats) }
    if not blank(f.description) { block(above: gap(spacing.small), framed-text(f.description)) }
  })
  for section in f.sections {
    if section.id == "banishment" {
      block(
        width: 100%,
        breakable: false,
        stroke: (top: 1.4pt + rust, bottom: 0.7pt + rust),
        inset: (y: 6pt, x: 1pt),
        above: gap(spacing.medium),
        below: 0pt,
        {
          caps-label(section.label + ":", fill: rust, size: 8pt)
          h(0.3em)
          framed-text(section.body)
        },
      )
    } else {
      block(width: 100%, breakable: false, above: gap(spacing.medium), below: 0pt, {
        caps-label(section.label + ":", size: 8pt)
        h(0.3em)
        framed-text(section.body)
      })
    }
  }
})
