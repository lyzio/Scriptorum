# Scriptorum 0.7.5 (0.7.0 step 6) — Test Report

| | |
|---|---|
| Version | 0.7.5, step 6 of 0.7.0 (extension modules, F25: suggestions, pictures, the Extensions tab, How to write an extension; issue #27) |
| Platform | GitHub Actions, ubuntu-24.04, Python 3.13, headless (the full suite); Linux 6.18 (x86-64), headless, in the build session (the new and affected tests, and the scenarios) |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · keyring 25.7.0 |
| Date | 19 November 2026 |
| Result | **440 passed**, 0 failed, 1 skipped (T-DOC-05, which needs Zensical): GitHub's Tests run for commit 88cf050. In the build session, with Zensical, the full suite also passed (441) |

## This step

The Extensions tab in the lower left pane, suggestions for a whole block (a new text, or a new block after it) shown under the block, pictures with Use, Set as portrait, Regenerate and Cancel, and the third author guide, How to write an extension. The design document was not read again: this chat knew it in full up to revision 437 (see `claude/Build state`), and a check found no change since.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.4 | Pass | With the corrections below |
| T-EXT-17, T-EXT-18 | Pass | New, core and window. A new text for a paragraph and a read-aloud block and a new block after the paragraph; Accept splices only that block (every other character unchanged), one undo step named "Checker: Plainer words"; Reject changes nothing; a suggestion for a block edited since is refused. In the window each shows under its block with the changed words marked |
| T-EXT-19 | Pass | New. An extension that declares none may not suggest; one with suggests and a network host may; a block that does not exist, source that does not parse and a picture that is not PNG or JPEG are refused plainly |
| T-EXT-20 | Pass | New, core and window. Use inserts `#image("/assets/images/helper-p….png", alt: "The mill at dusk")` after the paragraph in one undo step; Set as portrait on a loose person card writes portrait and its description; on a codex card it sets them on the codex entry; Regenerate runs the item again; Cancel drops it |
| T-EXT-21 | Pass | New, window. The tab shows only while an extension is on; two extensions, two sections; the findings list, suggestions and pictures are there; a setting changed in the tab is stored; switched off, the tab and the suggestion cards go |
| T-EXT-22 | Pass | New, three tests. The guide is in the language module and covers F25's topics; Help opens it with no network request; the website has its page; its worked example, built from the guide's own code blocks, installs and runs |
| T-EXT-16 | Pending | On your computer (keychain), as in 0.7.4 |
| T-DOC-06 | Pending | After the merge into main |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-USE-01, T-USE-02 | Pass | 155 checks, all passed. New in T-USE-02: findings in the Extensions tab, a suggestion under its block accepted with a named undo, a picture used with its description, Help ▸ How to write an extension. The test extension's own "suggest" item stops with a message on the scenario's adventure, which has no read-aloud block; the app shows that plainly, as it should |

## Found while building

- **Set as portrait did not change a loose person card**: the card kept its original header. The header is now written again from the new fields.
- **A suggestion's notice carried the suggestion's own kind**, so the window did not redraw. The suggestion now travels inside the notice.

## Corrections to existing tests (the design changed)

- **T-EXT-09** (`tests/test_step5.py`): the findings list is in the Extensions tab, not a floating panel.
- **T-DOC-01, T-DOC-02, T-DOC-05** (`tests/test_step4.py`): the website's third guide page.
- **T-UI-23** (`tests/test_m5e.py`): Help lists How to write an extension after the other two guides.
- **T-API-01**: the stored surface of API 1.1 grew (1.1 is not released yet, so its number stays).

## Tests added

T-EXT-17 and 18 (one test), T-EXT-19, T-EXT-20, T-EXT-21 (window, also covering 17, 18 and 20), T-EXT-22 (3). All are in the Test Plan, saved before building.

## Hand checks for the project manager

- Run the guide's worked example (Help ▸ How to write an extension ▸ Worked example) on the example adventure.
- With `tests/extensions/heading-check` switched on, look at the Extensions tab at the bottom of the left pane.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69` (unchanged since 0.6.4; nothing in this step prints).
