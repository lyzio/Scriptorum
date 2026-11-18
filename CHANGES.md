# Scriptorum 0.7.3 (0.7.0 step 4) — Changes

Base: **0.7.2** (0.7.0 step 3, on `build/0.7.0`). The fourth of five steps of 0.7.0 on the branch `build/0.7.0`: the documentation website (F24, issue #34) and the new line-art logo (F9). Both outcomes were approved on 18 November 2026 and are written into the design document. Extension modules (issue #27), which the design document also places in steps 4 and 5, are not in this step: their outcome is not written into the design document yet, so they wait for the project manager's approval.

- **#34, the documentation website.** `tools/build_site.py` makes the site's pages from text already in the repository: the two author guides from the interface-language module (the text Help shows), `docs/API.md`, `CHANGELOG.md`, a home page and a Status page from the open issues. The colours come from the Claret & Ink palette, light and dark, and the logo sits in the header. `.github/workflows/docs.yml` builds it with Zensical 0.1.2 and publishes it with GitHub Pages from main: on every merge into main, whenever an issue is opened, closed, reopened or relabelled, nightly and from Run workflow. Zensical runs only on GitHub; nothing is added to the app or its dependencies.
- **The new logo.** Line art on a transparent background replaces the logo on parchment: the 832-pixel original under `docs/logo/`, the app's 512-pixel copy, and no card, border, rounded corners or shadow in About, on the welcome screen or in the start-up window.

The file format, the API version (1.0), the installers and the release process are unchanged. Issues: Refs #34.

## Added

| File | Why |
|---|---|
| `docs/site/zensical.toml` | The website's configuration: pages, light and dark following the reader's system, search, sidebar, logo (F24) |
| `docs/site/index.md` | The website's home page |
| `tools/build_site.py` | Makes the website's pages, colours and Status page into `build/site/` (F24) |
| `.github/workflows/docs.yml` | Builds and publishes the website; every action pinned to a commit (F24, T-REL-15) |
| `tests/test_step4.py` | T-UI-58 (2), T-DOC-01, T-DOC-02, T-DOC-03 (2), T-DOC-04, T-DOC-05 |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.3 |
| `docs/logo/scriptorum-logo.png` | The line-art original, 832 × 832, transparent (F9) |
| `scriptorum/ui/logo.png` | The app's 512-pixel copy of the new logo |
| `docs/logo/README.md`, `scriptorum/licences/parts/logo.txt` | Describe the new logo; its licence is unchanged |
| `scriptorum/ui/index.html`, `scriptorum/ui/styles.css` | The logo without its card (F9) |
| `scriptorum/app/startup_window.py` | The start-up window's logo without rounded corners (F9) |
| `tests/test_m6f.py` | T-UI-51 no longer expects the card; T-REL-15 knows the two Pages actions |
| `CHANGELOG.md` | The 0.7.3 section |
| `README.md` | Points to the website |
| `docs/DEVELOPING.md` | How the website is made and how to build it locally |
| `TEST-REPORT.md`, `CHANGES.md` | This step |

## Deleted

Nothing.
