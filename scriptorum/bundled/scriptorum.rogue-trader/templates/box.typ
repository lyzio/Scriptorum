// 11.10 Box: the open curl frame with an optional title in bold capitals;
// pen-nib bullets; bold text at the start of a line is a label (F8).

#import "_style.typ": curl-frame, inside-box, box-seen, labelize

// 11.10 (0.7.7, issue #31): the Box is the only frame for the elements in
// it; inside-box marks its text for them. Its labels are made first, since
// the frame finds them only at the start of plain text (T-LOOK-03).
#let render(f, body, labels) = curl-frame(title: f.title, {
  box-seen.update(false)
  inside-box(labelize(body))
  box-seen.update(false)
}, seed: 31)
