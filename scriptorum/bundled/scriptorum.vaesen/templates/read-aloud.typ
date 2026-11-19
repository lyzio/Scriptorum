// 11.2 Read-aloud: the heading "Read aloud" (a printed word, D14) above the
// text, which is set in the theme's read-aloud face (F8).

#import "_style.typ": label, read-aloud-frame, in-box, box-part, small-caps-label, frame-par, fonts, sizes

// 11.10 (0.7.7, issue #31): in a Box, the heading and the text without the frame.
#let render(f, body, labels) = context if in-box() {
  box-part(small-caps-label(label(labels, "print.read-aloud")),
    frame-par(text(font: fonts.read, size: sizes.read, style: "italic", body)))
} else {
  read-aloud-frame(label(labels, "print.read-aloud"), body)
}
