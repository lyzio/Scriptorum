# Scriptorum 0.7.8 — Changes

Base: **0.7.7** (on `build/0.7.0`, commit a971dc0). Four general themes and two style hooks, outcome approved on 19 November 2026 (design document F8, approved mockups in 12.11). No issue: the work comes from the project manager's request in the build chat.

- **Four more general themes**: WHFRP (grim fantasy after the look of the 4th-edition books), The One Ring (brick red, after a homebrew template used as a mood reference only), WH40KRP (grimdark gothic) and Rogue Trader (baroque navy and brass). Each draws every block of the core element kit, so it is offered for Vaesen, Plain and every other game system; each has two handout papers, its own ornaments (the project's drawings) and SIL OFL fonts with their licence files. The unofficial notice is in every description and licence file; no file says Warhammer.
- **Two style hooks** in `_style.typ`: `page-background`, drawn behind every page (bands, a chapter tab), and `stat-row`, which draws a creature's stats. The defaults draw what the templates drew before, so Vaesen, Plain, Legends and Lattes and Call of Cthulhu print byte-identically (the m1-basic checksum is unchanged).
- **How to write a theme** describes the hooks and the four themes as examples.

## Added

| File | Why |
|---|---|
| `scriptorum/bundled/scriptorum.whfrp/`, `scriptorum.the-one-ring/`, `scriptorum.wh40krp/`, `scriptorum.rogue-trader/` | The four themes: manifest, licence, page setup, papers, labels, templates, ornaments, fonts, the vendored chart packages |
| `tools/make_more_themes.py` | Writes the four themes from the Vaesen templates, as `make_general_themes.py` does for the earlier ones |
| `tests/test_0_7_8.py` | T-LOOK-15 |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.8 |
| `scriptorum/bundled/scriptorum.<theme>/templates/_page.typ` (four earlier themes) | Draws the theme's `page-background` behind every page, as decoration |
| `scriptorum/bundled/scriptorum.<theme>/templates/creature.typ` (four earlier themes) | The stats are drawn by `stat-row` |
| `scriptorum/bundled/scriptorum.<theme>/templates/_style.typ` (four earlier themes) | The default `page-background` (none) and `stat-row` (the earlier look) |
| `tools/guides/how-to-write-a-theme.md`, `scriptorum/bundled/scriptorum.en/strings/guide-theme.json` | The new section Bands, chapter tabs and stat blocks; eight bundled themes; the four themes as examples |
| `tests/test_modules.py`, `tests/test_step2.py`, `tests/test_step7.py` | The four themes in the lists of bundled modules and themes (T-MOD-01, T-LOOK-13, T-LOOK-14) |
| `tests/test_m4.py` | T-LOOK-09's offered themes include the four (corrected for 0.7.8) |
| `README.md`, `CHANGELOG.md`, `TEST-REPORT.md`, `CHANGES.md` | This build |

## Deleted

None.
