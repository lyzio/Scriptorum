# Scriptorum 0.7.7 — Test Report

| | |
|---|---|
| Version | 0.7.7, on `build/0.7.0` (issues #30, #33, #31) |
| Platform | GitHub Actions, ubuntu-24.04, Python 3.13, headless (the full suite); Linux (x86-64), headless, in the build session (the full suite with Zensical, and the scenarios) |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · keyring 25.7.0 |
| Date | 19 November 2026 |
| Result | **453 passed**, 0 failed, 1 skipped (T-DOC-05, which needs Zensical): GitHub's Tests run 44515406725 for commit 51c26fa |

## This build

A full-width section never covers what stands in a column (#30), pasted "She knows" lines become Information in the person card (#33), and the Box is the only frame for the elements in it (#31). The design document was read as its changes since revision 440 (none), with F7.4, 11.10 and F4's new paragraph in full.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.6 | Pass | GitHub's run; in the build session T-LOOK-03 failed once before the fix below |
| T-BUILD-34 | Pass | New, every theme: a map in a column, then a full-width section holding a map, then text, then a tall framed Box beside a full-width map; no text of the column element lies within the full-width section's height. Without the fix the test fails in Vaesen and Plain. A second test checks that the core sets every unbreakable element as one measured box |
| T-LOOK-14 | Pass | New, every theme: in a Box the parts keep their labels (PUBLIC, SECRET, HINT, READ ALOUD, CHECK), sit in the order written and closer together than the framed elements outside; the person card keeps its frame; the accessible PDF is made with the parts' text. A second test checks the templates of every theme |
| T-UI-59 | Pass | New, window, two tests: "She knows (public)", "Hon vet (hemlig)", "Knows", "He knows (secret)", "Han vet (publik)", "Vet" and a list marker; Mood fills its field; "Remember: …" and "Vetenskap: …" stay; one undo brings every line back |
| T-LOOK-07 | Pending | Look at a Box with Information inside, on screen and on paper |
| T-DOC-06, T-EXT-16, T-BUILD-03, T-REL-02 | Pending | As in 0.7.6 |
| T-USE-01, T-USE-02 | Pass | 157 checks, all passed. T-USE-01 now checks that the two "She knows" lines became public and secret Information in Lovisa Berg's card (#33) instead of noting them as friction. The old note about adding maps through a file dialog (M5) is unchanged |

## Looked at

Pages of the #30 case in all four themes before and after (the column map now moves whole to the next page, with its label); a Box holding every kind in all four themes (frameless parts, lines between them, the secret's fill, the person card framed); the window after converting the pasted person.

## Found while building

- **The Box's frame was too short** when its parts had lines between them: while the Box measures its text, a part cannot see the parts before it. Every part now keeps a line's room above it, drawn only after an earlier part.
- **Only the first lines appeared in a long Box**: "inside a Box" as a state needed more layout passes than Typst allows. It is now a style, which holds at once.
- **A Box's bold labels stopped printing in capitals** (T-LOOK-03): the Box's mark hid the start of its text from the label rule. The Box now makes its labels before marking its text.

## Corrections to existing tests

None.

## Tests added

T-BUILD-34 (2), T-LOOK-14 (2), T-UI-59 (2) in `tests/test_step7.py`, in the Test Plan before building.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69` (unchanged since 0.6.4: the elements look the same as before).
