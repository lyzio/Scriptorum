// 11.12 Pacing note: a small hourglass on the left, a thin border and a faint
// tint, then the free text with its bold kept.

#import "_style.typ": pacing-frame, in-box, box-pacing

// 11.10 (0.7.7, issue #31): in a Box, the tint and the mark without the border.
#let render(f, body, labels) = context if in-box() { box-pacing(body) } else { pacing-frame(body) }
