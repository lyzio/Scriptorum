// 11.7 Dice: vector dice in frame brown; the success face is marked. Inline
// in a sentence, or as a block with the die on its left and the text beside.

#import "_style.typ": accent, die, frame-par, in-box, box-part

#let _dice(f) = {
  if f.face != none {
    die(face: f.face, success: f.face in f.success)
  } else {
    [#die(face: none)#h(0.15em)#text(weight: "bold", fill: accent, f.notation)]
  }
}

#let render(f, body, labels) = {
  if f.inline {
    box(_dice(f))
  } else {
    let row = grid(columns: (auto, 1fr), column-gutter: 0.55em, _dice(f), frame-par(body))
    // 11.10 (0.7.7, issue #31): in a Box, a part of the Box with its line.
    context if in-box() { box-part(none, row) } else {
      block(width: 100%, breakable: false, above: 0.9em, below: 0.9em, row)
    }
  }
}
