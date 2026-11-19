// 11.8 Check, in the open curl frame: a die, the printed word "Check", then
// the roll and the difficulty in small capitals, with the text below.

#import "_style.typ": accent, quiet, label, small-caps-label, caps-label, die, blank, empty-body, curl-frame, spacing, framed-text, gap, in-box, box-part

#let head(f, labels) = {
  die(face: none, size: 0.9em)
  h(0.4em)
  caps-label(label(labels, "print.check"), size: 9.2pt)
  h(0.5em)
  small-caps-label(if blank(f.difficulty) { f.roll } else [#f.roll · #f.difficulty], fill: quiet)
}

#let framed(f, body, labels) = curl-frame(
  title: none,
  seed: 23,
  {
    align(center, head(f, labels))
    if not empty-body(body) {
      block(above: gap(spacing.small), framed-text(body))
    }
  },
)

// 11.10 (0.7.7, issue #31): in a Box, the die, the word and the roll above
// the text, without the frame.
#let render(f, body, labels) = context if in-box() {
  box-part(head(f, labels), if not empty-body(body) { framed-text(body) })
} else { framed(f, body, labels) }
