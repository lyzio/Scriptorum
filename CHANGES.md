# Scriptorum M6-0.6.10 — Changes

Base: **M6-0.6.9** (`main`, accepted and merged on 16 November 2026, with the project manager's README edit of 18 November). A fix build (design document section 10, "M6 fix build 0.6.10", decided 18 November 2026):

- **the update check asks for the right file** (issue #26, F21): `scriptorum-update.json`, as the release script writes and the release publishes
- **the logo** (F9, D16): in the About window, on the welcome screen, in the start-up window and at the top of the README; CC BY-SA 4.0, made with an AI image tool, no personal credit; listed in About ▸ Under the hood with its licence text; the file icons stay the drafts
- **where the map key goes** (issue #22, F5): beside an upright map only where the space is at least 12 cm wide, otherwise under it; under it in two real columns (first half left) only where it is that wide; the key's text left-aligned, never justified; in all four themes
- **the window's zoom** (issue #16, F9): Ctrl and the wheel, Ctrl + plus, minus and 0 outside the preview, in steps from 50 to 200 %; shown in the status bar when not 100 %, click to reset; remembered in the app settings
- **the + menu in groups** (issue #18, F9): Text, Structure, Boxes, People, Rules, Handouts, Layout and Other, side by side as columns
- **fewer release files** (issue #25, F10): the kit (1.0.4) writes only the installer; the attach job writes one `SHA256SUMS.txt` for every installer of the release and keeps the lines of earlier runs; the release description carries the Linux install notes; no source zip
- **issue #1:** a test shows that New entry ▸ Creature makes and opens a Creature entry in a Vaesen adventure and is not offered in a Plain one; nothing needed fixing
- **workflows** (section 10): every action at its Node 24 version and pinned to a commit; a dependency audit (pip-audit, npm audit) weekly and on pull requests; the tests on every pull request and push to a build branch

Issues fixed: #1 (checked, no change needed), #16, #18, #22, #25, #26. Issues opened: see the test report.

Every file not listed here is unchanged from M6-0.6.9.

## Added

| File | Why |
|---|---|
| `.github/workflows/tests.yml` | The automated tests on every pull request and every push to `build/**`, read-only (T-REL-15) |
| `.github/workflows/audit.yml` | pip-audit on the pinned Python packages and npm audit on the interface, weekly and on pull requests; three checked cryptography advisories are ignored with the reason written beside them (T-REL-15) |
| `docs/logo/scriptorum-logo.png`, `docs/logo/README.md` | The logo's original (1254 px) and what it is, where it is used and its licence |
| `scriptorum/ui/logo.png` | The 512-pixel copy the app shows |
| `scriptorum/licences/parts/logo.txt` | The logo's notice for About ▸ Under the hood |
| `scriptorum/licences/texts/CC-BY-SA-4.0.txt` | The full CC BY-SA 4.0 text for the Licences tab (from the SPDX licence list) |
| `tests/test_m6f.py` | T-WORLD-35, T-UI-49 to 52, T-REL-13 to 15 |

## Changed

| File | Why |
|---|---|
| `scriptorum/core/updates.py` | `UPDATE_URL` asks for `scriptorum-update.json` (#26) |
| `scriptorum/bundled/scriptorum.en/strings/update.json` | The example address in the refusal message uses the right name |
| `scriptorum/bundled/scriptorum.*/templates/map.typ` (four themes) | Key beside only from 12 cm; two real columns under it only that wide; left-aligned (#22) |
| `scriptorum/core/appsettings.py` | `app_zoom` with its steps (#16) |
| `scriptorum/app/main.py` | The window applies the stored zoom when the page has loaded (#16) |
| `scriptorum/app/bridge.py` | `appZoom`, `setAppZoom` (#16) |
| `scriptorum/app/startup_window.py` | The logo above the name and version, with rounded corners |
| `scriptorum/core/about.py` | The logo's row and the CC BY-SA 4.0 licence |
| `scriptorum/licences/README.txt` | Mentions logo.txt |
| `scriptorum/bundled/scriptorum.en/strings/app.json`, `about.json`, `menu.json`, `zoom.json` | The logo's description, its About row, the Text and Other groups, the zoom in the status bar |
| `scriptorum/ui/index.html`, `styles.css` | The logo on the welcome screen and in About; the zoom in the status bar; the + menu's columns |
| `ui-src/app.ts`, `ui-src/i18n.ts`, `ui-src/shell.ts` | The window's zoom; the grouped + menu; `data-i18n-alt` |
| `scriptorum/ui/dist/app.js`, `preview-window.js` | Built interface |
| `packaging/build.py`, `packaging/kit.json` | Kit 1.0.4: only the installer is written (#25) |
| `packaging/user-docs/INSTALL-*.txt` | The source is on GitHub, not in a source zip |
| `packaging/README.md`, `packaging/docs/RELEASE.md` | The release's files and the source for the GPL |
| `tools/release.py` | `release_description`: the changelog section followed by the Linux notes (#25) |
| `.github/workflows/installers.yml` | Pinned actions at Node 24 versions; one merged `SHA256SUMS.txt` (#25) |
| `.github/workflows/release.yml`, `codeql.yml` | Pinned actions at Node 24 versions |
| `README.md` | The logo at the top; its licence |
| `CHANGELOG.md` | The 0.6.10 section |
| `pyproject.toml` | Version 0.6.10; `ui/*.png` in the package data |
| `scriptorum/__init__.py`, `ui-src/package.json` | Version 0.6.10 |
| `tests/test_m6b.py` | T-UI-34 expects the logo's row and licence (design changed) |
| `tests/test_m6c3.py` | T-WORLD-27's placement test puts the map in a full-width section (design changed, #22) |
| `tests/test_m6c5.py` | The test addresses use the right file name (#26) |
| `tests/test_m6d.py` | T-REL-09 expects pinned actions and kit 1.0.4 (design changed) |
| `tests/scenarios/run_use_scenarios.py` | The 0.6.10 steps; the example address's file name |

## Deleted

| File | Why |
|---|---|
| `scriptorum/ui/logo.svg` | The draft logo, replaced by `logo.png` |
