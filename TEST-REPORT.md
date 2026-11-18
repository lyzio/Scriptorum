# Scriptorum 0.7.3 (0.7.0 step 4) — Test Report

| | |
|---|---|
| Version | 0.7.3, step 4 of 0.7.0 (issue #34 and the new logo) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · for the website only: Zensical 0.1.2 |
| Date | 18 November 2026 |
| Result | **412 passed**, 0 failed, 0 skipped (on a machine without Zensical: 411 passed, 1 skipped, T-DOC-05) |

## This step

The documentation website (design document F24, issue #34) and the new line-art logo (F9). The previous build's 404 tests passed before anything was changed.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.2 | Pass | With the corrections below |
| T-UI-58 | Pass | New, two tests. `docs/logo/scriptorum-logo.png` is 832 × 832 with the recorded SHA-256 and an alpha channel; the 512-pixel copy has transparent corners; the welcome screen and About (light and dark) show it with no rounding, border, shadow or background; the start-up window's picture is see-through around the drawing; no `logo-card` left |
| T-DOC-01 | Pass | New. Exactly the six pages; lyzio.github.io/Scriptorum; light and dark by the reader's system; search and sidebar; the logo in the header; the palette's colours in both modes; the API reference and changelog are the repository's files |
| T-DOC-02 | Pass | New. Both guide pages hold the guide's title, every section in order and every line of its text; `file:` code blocks get their file name as title; nothing generated is tracked by git |
| T-DOC-03 | Pass | New, two tests. Three lists by label; "to test" only under Waiting to be tested with its version or step; unlabelled, closed issues and pull requests left out; Markdown characters escaped; empty and missing lists; the workflow's paged file gives the same page |
| T-DOC-04 | Pass | New. Triggers (push to main, issues opened, closed, reopened, labelled and unlabelled, nightly, by hand); Zensical pinned; every action pinned to a commit; Pages from main only; only the deploy job writes, only to Pages; Zensical not in the app's dependencies |
| T-DOC-05 | Pass | New. The site builds with `zensical build --strict`: every page, a search index, the logo and the stylesheet. Skipped where Zensical is not installed |
| T-DOC-06 | Pending | The live site, once 0.7 is merged into main and Pages is switched on |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-USE-01, T-USE-02 | Pass | 141 checks, all passed. Nothing in this step is used in the scenarios except the logo in About, which the script already checks |

## Looked at

- The website, built locally and served on this machine: the home page and a guide in light mode, the home and Status pages in dark mode. The header has the app window's parchment (light) and ink (dark) colours, links are claret, and the logo reads on both.
- The app: the welcome screen in light and dark mode, About and the start-up window. The logo is drawn straight on the background with no card.

## Found while building

- **The Status page cut "Planned for 0.7.3 …" at the first dot**, so issue #34 would have shown "0". The older "Planned for" form is now read up to its comma.
- **The light header** was nearly white in Zensical's own style. It now takes the app window's colour, like the app's menu bar.

## T-USE findings

- Unchanged from 0.7.2: issue #33 (friction, later), and the script's fixed note about the map dialog (issue #3 is closed).

## Corrections to existing tests (the design changed)

- **T-UI-51** (`tests/test_m6f.py`): no longer expects a card with rounded corners or an original above 1 MB; the new original is 557,619 bytes. T-UI-58 checks how the logo is drawn.
- **T-REL-15** (`tests/test_m6f.py`): knows the Node 24 versions of `actions/upload-pages-artifact` (5) and `actions/deploy-pages` (5), which the website's workflow uses.

## Tests added

T-UI-58 (2), T-DOC-01, T-DOC-02, T-DOC-03 (2), T-DOC-04, T-DOC-05, and T-DOC-06 by hand. All are in the Test Plan, which was saved before the step was built.

## Hand checks for the project manager

- Start the app in light and dark mode: the new logo on the welcome screen, in Help ▸ About Scriptorum and in the start-up window, with no card around it.
- Build the website yourself if you like (`docs/DEVELOPING.md`, "The documentation website").
- After 0.7 is merged into main: Settings ▸ Pages ▸ Source → GitHub Actions, then T-DOC-06.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4.
