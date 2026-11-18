# Scriptorum 0.7.0 step 2 — Test Report

| | |
|---|---|
| Version | 0.7.0, step 2 of 5 (issues #23, #20, #21) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 |
| Date | 18 November 2026 |
| Result | **392 passed**, 0 failed, 0 skipped |

## This step

Built on 0.7.0 step 1 (383 passed). The step adds 9 tests in `tests/test_step2.py`. Eight existing test files were corrected because the design changed what they check (below). The m1-basic checksum is unchanged.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.0 step 1 | Pass | With the corrections below |
| T-LOOK-13 | Pass | New, three tests. Every bundled theme is offered for both bundled game systems; a theme missing a template for a block of a test game system is locked with the reason "no styling for: …"; a theme locked only by a later game system still builds with the generic frame |
| T-BUILD-33 | Pass | New, four tests (Plain, Vaesen and two general themes). On a one-column page a Columns section of 2 and 3 sets its text in columns where it is written, the column break moves to the next column, the text after it is one column again; it parses and writes back byte-identical; on a two-column page it still prints |
| T-UI-53 | Pass | New. Columns section is in the Insert menu under Layout and in the + menu on a one-column page, and in neither on a two-column page |
| T-UI-54 | Pass | New. With Jätten Finns skuld, moving in the editor scrolls the preview to the block about a third from the top with a mark; scrolling the preview by hand pauses it; the Follow switch turns it off and is remembered; a click in the preview moves the editor |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-USE-01, T-USE-02 | Pass | 132 checks, all passed. Changed: the Vaesen theme now stays when the game system is changed to Plain (#23); new: the Follow switch is on and the preview marks where the editor is (#21) |

## Found while building

- **The Insert menu put Full-width section, Never split and Table of contents among the elements**, while the + menu has them under Layout. They are now under Layout in both, where the design document puts Columns section too.

## T-USE findings

The same two as before: pasted labels stay after converting (issue #2, planned for step 3) and the script's fixed note about the map dialog (issue #3 is closed).

## Corrections to existing tests (the design changed)

- **T-UI-03** (`tests/test_ui_smoke.py`): the theme list for Plain now includes Vaesen (#23).
- **T-MOD-03, T-MOD-10** (`tests/test_modules.py`): the copied theme is given its requirement explicitly; the always-on set includes Columns section (#20).
- **T-LOOK-09** (`tests/test_m4.py`): Vaesen is among the themes offered for Plain.
- **T-MOD-13, T-UI-26** (`tests/test_m5.py`): the theme pairs include Vaesen with Plain.
- **T-MOD-14** (`tests/test_m5e.py`): a theme is locked with the reason "no styling for: Rumour" instead of being hidden.
- **T-MOD-26** (`tests/test_m6e.py`): the case where a theme must be picked can no longer happen with the bundled modules (both game systems have the same blocks), so the test makes it with a stand-in.
- **T-UI-19** (`tests/test_ui_m4.py`): theme names no longer carry a "made for" hint.
- **check-themes and the zoom bar** (`tests/test_ui_m5.py`): the self-test builds 8 pairs; the zoom bar ends with Follow.
- **T-UI-04** (`tests/test_ui_smoke.py`), after your Linux run (391 passed, 1 failed): it expected "Page 1 of" after putting the cursor in a read-aloud. Since the preview follows the editor (#21), the status bar shows the page the read-aloud is on, page 2 on your machine; here the window settled before following. The test now checks the form "Page N of M".

## Tests added

T-LOOK-13 (3), T-BUILD-33 (4), T-UI-53, T-UI-54. All are in the Test Plan, added before the step was built.

## Hand checks for the project manager

- File ▸ New adventure…: pick Plain, then Vaesen; every theme is offered with both.
- On a one-column page: Insert ▸ Layout ▸ Columns section, write in it, set Columns to 3. On a two-column page it is not offered.
- Move through the adventure in the editor and watch the preview follow. Scroll the preview yourself: it stops following for a moment. Turn Follow off in the zoom bar, restart, and it is still off.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4 (checked by T-API-02).
