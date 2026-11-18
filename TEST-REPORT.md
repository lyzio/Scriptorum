# Scriptorum 0.7.2 (0.7.0 step 3) — Test Report

| | |
|---|---|
| Version | 0.7.2, step 3 of 0.7.0 (issues #5, #4, #17, #2) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 |
| Date | 18 November 2026 |
| Result | **404 passed**, 0 failed, 0 skipped |

## This step

Built on 0.7.1 (step 2), which passed on the project manager's Linux machine (392). The step adds 12 tests in `tests/test_step3.py`. Seven existing tests were corrected because the design changed what they check (below). The m1-basic checksum is unchanged (checked by T-API-02).

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.1 | Pass | With the corrections below |
| T-SRC-21 | Pass | New, seven tests. Bulleted and numbered lists of three levels with bold, italic and a die parse as lists and write back byte-identical; an edited list is written `+ item` / `- item` with two spaces per level; a second line inside an item, mixed markers, `1.` numbering and a table in an item stay locked and unchanged |
| T-UI-55 | Pass | New. In `m5-print` the sample's list shows as a list; Insert ▸ List, Enter, Tab (never skipping a level), Shift+Tab, Backspace on an empty item, Enter on an empty item ending the list with a paragraph; numbered from right-click, bulleted from Format; one undo takes back the switch |
| T-UI-56 | Pass | New. In `m5-print`: Enter saves a footnote with a bold word, a click outside saves, Esc changes nothing, one undo per save; the exported PDF prints "The log was kept badly from 1871." |
| T-UI-57 | Pass | New, two tests. The T-USE-01 lines: "PERSON:" becomes a person with Mood, Description and Linked to from the next lines; one undo brings the lines back; "SECRET:" and "* [Publikt]" become a secret and public Information; "Remember: …" stays; "Scene 1:" becomes the scene "The harbour" with Location and People present. In `m6-clues`, Swedish labels: "SLP:", "Humör:", "Kopplad till: Ulrika och Anders Lind" (linked to both entries) and "Ledtråd:" (a hint) |
| T-WORLD-36 | Pass | New. In `m6-clues`, a link from Ulrika to Anders Lind shows on Anders's entry, is stored only on Ulrika's, prints on both cards; stored on both sides it shows once on each and the chart draws one line; opening changes no file |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-REL-10 | Windows part passed with 0.6.9 | The project manager reported on 18 November 2026 that the Windows installer of 0.6.9 installs and works; 0.7 has not been tried on Windows |
| T-USE-01, T-USE-02 | Pass | 141 checks, all passed. New: T-USE-01 checks that the typed labels went when converting (the scene "The harbour" with its Location, the person "Lovisa Berg" with Mood, no "SECRET:" or "HINT:"); T-USE-02 writes a list with a sub-item and changes a footnote in place |

## Found while building

- **A list section and the box that holds blocks shared a class name** (`blk-list`). A list block's section is `blk-listing`.
- **A plain-text footnote with quotation marks** would have printed curly quotes once its text became markup. Footnotes keep straight quotes, so a plain-text footnote prints exactly as before.

## T-USE findings

- **New, issue #33 (friction, later):** the pasted lines "She knows (public): …" stay as paragraphs after the person is converted.
- The script's fixed note about the map dialog (issue #3 is closed).
- Issue #2's finding (pasted labels stay) is fixed in this step.

## Corrections to existing tests (the design changed)

- **T-SRC-03** (`tests/test_source.py`): the plain list of `m1-locked` is a list block now, not a locked block (#5); it still writes back unchanged.
- **T-UI-38** (`tests/test_m6c2.py`): the list moved into and out of the Box is a list block; the keys are pressed in its item.
- **T-SRC-13, T-SRC-14, T-UI-12** (`tests/test_ui_m2.py`): converting "Scene 1: The harbour" to a scene now titles it "The harbour" (#2).
- **T-UI-50** (`tests/test_m6f.py`): the + menu's Text group holds List (#5).
- **T-REL-11** (`tests/test_m6d.py`): the README and the 0.7 changelog say the Windows installer was tested with 0.6.9, no longer "Not yet tested".

## Tests added

T-SRC-21 (7), T-UI-55, T-UI-56, T-UI-57 (2), T-WORLD-36. All are in the Test Plan, added before the step was built.

## Hand checks for the project manager

- Open the example adventure: its lists ("Lösningar i scenen", "Möjliga vägar ut") are lists you can type in. Try Enter, Tab and Shift+Tab, and right-click ▸ Numbered list.
- Click a footnote's chip (sample m5-print, or insert one with Insert ▸ Footnote), change it, press Enter; try Esc too.
- In the codex, put another person in Ulrika's Linked to, then open that person: Ulrika is there, marked "set on that entry".
- Paste a few lines such as "PERSON: Agnes", "Mood: Wary", "SECRET: …" into a paragraph and convert them.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4.
