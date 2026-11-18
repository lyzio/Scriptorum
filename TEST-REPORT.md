# Scriptorum M6-0.6.10 — Test Report

| | |
|---|---|
| Version | 0.6.10 (Milestone 6, fix build: issues #1, #16, #18, #22, #25, #26, the logo, the workflows) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 |
| Date | 18 November 2026 |
| Result | **375 passed**, 0 failed, 0 skipped |

## This build

Built on M6-0.6.9 (accepted, `main` at 6ed9b30 with the README edit of 18 November). Before any change the 0.6.9 suite ran here: 359 passed. The build adds 16 tests in `tests/test_m6f.py`; four tests of earlier builds were corrected because the design changed (below). The m1-basic checksum is unchanged.

## Results

| ID | Result | Notes |
|---|---|---|
| T-FILE, T-SRC, T-BUILD (but 03), T-MOD, T-UI, T-WORLD, T-FONT, T-LOOK (but 07) | Pass | As in 0.6.9, with the corrections below |
| T-REL-13 | Pass | New (issue #26). UPDATE_URL ends in `scriptorum-update.json`, the only name `tools/release.py` writes; no file of the app, its tests, tools, kit or workflows names the old spelling |
| T-REL-14 | Pass | New, three tests (issue #25). The kit's finish step writes only the installer (kit 1.0.4); the attach job's checksum merge, run here on test files, replaces the line of a rebuilt installer, keeps the line of one attached earlier and sorts them; the release description is the changelog section followed by the Linux notes with the version filled in |
| T-REL-15 | Pass | New, two tests. Every `uses:` line in the five workflows is pinned to a 40-character commit with its version (checkout 7.0.1, setup-python 7.1.0, upload-artifact 7.0.2, download-artifact 8.0.2, setup-node 7.1.0, codeql-action 4.39.3), all Node 24 versions; the audit and tests workflows are read-only. Run here: `npm audit` found nothing; `pip-audit` found three advisories for cryptography 48.0.1 (below) |
| T-WORLD-35 | Pass | New, five tests (four themes and the template check). An upright map with five pins: in a column of a two-column A4 page the key is under it in one column; in a full-width section and on a landscape page it is beside it; a landscape map in a full-width section has its key under it in two columns; the key text is left-aligned in every theme. Looked at in a rendered page against 0.6.9 (the squeezed, hyphenated key of the report is gone) |
| T-UI-49 | Pass | New (issue #16). Ctrl + plus, =, minus and 0 and the wheel step through 50 … 200 % and stop at the ends; the status bar shows "Zoom 110 %" only when not 100 %; clicking it resets; in the preview only the preview zooms; the stored zoom is applied at start; a value outside the steps is ignored; the adventure's files are unchanged |
| T-UI-50 | Pass | New (issue #18). In Vaesen and in Plain the + menu shows Text (Paragraph, Table, Image, Footnote), Structure, Boxes, People, Rules, Handouts and Layout (Table of contents, Full-width section, Never split) as columns; inside a person card only Boxes (Secret, Public information, Hint, Clue); Box inserted after a block in one undo step; the Insert menu is still one list |
| T-UI-51 | Pass | New, two tests. The logo on the welcome screen, in About (light and dark) and in the start-up window, with rounded corners and "Scriptorum logo" for screen readers; Under the hood lists it with CC BY-SA 4.0; the Licences tab holds the full text; the README starts with it; no theme or build file uses it |
| T-UI-52 | Pass | New (issue #1). In m6-clues (Vaesen) Codex ▸ New entry ▸ Creature makes "The well-wight", a Creature entry, in one undo step and opens it; in m5-plain no Creature is offered. Nothing needed fixing |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-REL-01, T-REL-03, T-REL-10 | Pending | Per platform, with the installers from GitHub |
| T-USE-01, T-USE-02 | Pass | 129 checks, all passed. New steps: the window's zoom and its reset from the status bar, the + menu's columns, the logo in About |

## Found while building

- **The dependency audit's first run** found three advisories for cryptography 48.0.1 (GHSA-m2h6-j472-rp4c and GHSA-jwv3-5hgf-82ww about X.509 certificates, GHSA-g6cj-pr64-35w5 about PKCS#7 decryption; fixed in 49.0.0 and 50.0.0). Scriptorum uses cryptography only for Ed25519 signatures on updates, so none of them reaches it. 48.0.1 stays pinned because it is the newest version with builds for Intel Macs on macOS 12 (D2). The three are ignored in `audit.yml`, with this reason written beside them; any other finding fails the run. A decision for the project manager (see the final message).
- **Issue #30** (new, bug): on a two-column page, a full-width section that lands on the same page as a map in a column is drawn over it. The same happens in 0.6.9.

## T-USE findings

| Finding | Kind | Milestone |
|---|---|---|
| Labels typed in pasted text stay after converting it | friction | later, with import (L3); issue #2 |
| A new map always goes through a file dialog | friction | the script's fixed note; issue #3 is closed |

## Corrections to existing tests

- **T-WORLD-27** (`tests/test_m6c3.py`): its placement check put an upright map in a column of a two-column page and expected the key beside it. From 0.6.10 the key goes beside only where the space is at least 12 cm wide (issue #22), so the check puts the map in a full-width section, where it still sits beside. The design changed.
- **T-UI-34** (`tests/test_m6b.py`): Under the hood now also lists the logo, and the Licences tab ends with CC BY-SA 4.0. The design changed.
- **T-REL-09** (`tests/test_m6d.py`): it checked `actions/upload-artifact@v4` and kit 1.0.3; the actions are now pinned to commits (T-REL-15) and the kit is 1.0.4 (T-REL-14). The design changed.
- **T-UI-44 and T-UI-45** (`tests/test_m6c5.py`) and the scenario script: their example addresses used the old file name (issue #26).

## Tests added

T-WORLD-35 (5), T-UI-49, T-UI-50, T-UI-51 (2), T-UI-52, T-REL-13, T-REL-14 (3), T-REL-15 (2). All are in the Test Plan, added before the build.

## Hand checks for the project manager

1. **The logo:** the welcome screen, Help ▸ About Scriptorum (light and dark mode) and the start-up window.
2. **Issue #16:** press Ctrl and plus (⌘ and plus on the Mac) with the cursor in the text, look at the status bar, click "Zoom 110 %". Then zoom inside the preview: only the preview changes.
3. **Issue #18:** hover a block, press +, and read the columns.
4. **Issue #22:** your adventure *Oroligt i Widtsköfle*, Handout #4 "Widtsköfle med omnejd": the key now stands under the map, left-aligned.
5. **Issue #1:** in a Vaesen adventure, Codex ▸ New entry, pick Creature.
6. **Issue #25 and the workflows,** on GitHub after merging and tagging: the release has the four installers, one SHA256SUMS.txt and the two update files, and its description ends with "Installing on Linux". The Tests and Dependency audit workflows run on the pull request.
7. **Settings you switch on yourself** (Settings ▸ Code security, and Settings ▸ Branches): secret scanning with push protection, Dependabot security alerts, and branch protection for main requiring the Tests check.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4.
