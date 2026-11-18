# Scriptorum 0.7.0 step 2 — Changes

Base: **0.7.0 step 1** (the internal API, on `build/0.7.0`, confirmed by the project manager on 18 November 2026). The second of five steps of 0.7.0 on the branch `build/0.7.0`: themes for every game system (issue #23), the Columns section (issue #20) and the preview following the editor (issue #21). Outcomes approved on 18 November 2026 and written into the design document (F8, F7.2, F7.4).

- **#23**: a theme is offered for every game system whose blocks it styles (template coverage). A theme that misses a template is shown greyed out with the reason. A theme can name the game system it was `made_for`, which only orders the list. The Vaesen theme no longer requires the Vaesen game system.
- **#20**: a new core layout element, Columns section, with a Columns field of 2 or 3, offered only on a one-column page.
- **#21**: the preview follows the block the editor is in, with a Follow switch in the zoom bar, remembered; it pauses for 2 seconds after the preview is scrolled by hand.
- found on the way: the Insert menu now lists Full-width section, Never split and Table of contents under Layout, as the + menu does.

The file formats, the API version (1.0), the installers and the release process are unchanged. Issues: Refs #20, #21, #23.

## Added

| File | Why |
|---|---|
| `scriptorum/bundled/scriptorum.core/elements/column-section.json` | The Columns section element (F7.4, #20) |
| `scriptorum/bundled/scriptorum.en/strings/theme.json` | The locked-theme reason and the names of the theme's own pages (#23) |
| `tests/test_step2.py` | T-LOOK-13, T-BUILD-33, T-UI-53, T-UI-54 |

## Changed

| File | Why |
|---|---|
| `scriptorum/core/modules.py` | `game_system_blocks`, `theme_missing`, `theme_offered_for` by coverage, `theme_made_for` (#23) |
| `scriptorum/core/session.py` | Game systems list their offered and locked themes; `kind_name`, `themes_locked`; the editor knows whether Columns section is offered; a locked version of the same theme can still be previewed (#20, #23) |
| `scriptorum/core/modmanager.py` | A theme without a generic frame is refused only if it is offered for no installed game system (#23) |
| `scriptorum/core/appsettings.py` | `preview_follow`, on by default (#21) |
| `scriptorum/bundled/scriptorum.vaesen/module.json` | `made_for` the Vaesen game system instead of requiring it (#23) |
| `scriptorum/bundled/scriptorum.core/labels/en.json` | The names "Columns section" and "Columns" (#20) |
| `scriptorum/bundled/scriptorum.core/typst/elements.typ` | The `column-section` template (#20) |
| `scriptorum/bundled/scriptorum.en/strings/settings.json` | The locked theme line; the old "general" hint removed (#23) |
| `scriptorum/bundled/scriptorum.en/strings/zoom.json` | Follow and its hint (#21) |
| `scriptorum/bundled/scriptorum.en/strings/guide-theme.json`, `guide-game-system.json` | Regenerated from the guides |
| `tools/guides/how-to-write-a-theme.md`, `how-to-write-a-game-system.md` | Which game systems a theme is offered for, and `made_for` (#23) |
| `ui-src/app.ts`, `editor.ts`, `model.ts` | Locked themes greyed out; Columns section only where offered and under Layout; following the editor (#20, #21, #23) |
| `scriptorum/ui/index.html`, `styles.css`, `dist/app.js` | The Follow switch, the mark, the rebuilt interface |
| `tests/scenarios/run_use_scenarios.py` | The Vaesen theme now stays with Plain (#23); the preview follows (#21) |
| `tests/test_ui_smoke.py`, `test_modules.py`, `test_m4.py`, `test_m5.py`, `test_m5e.py`, `test_m6e.py`, `test_ui_m4.py`, `test_ui_m5.py` | Corrected because the design changed: themes offered by coverage, a new always-on element, the Follow switch (see TEST-REPORT.md) |
| `CHANGELOG.md`, `CHANGES.md`, `TEST-REPORT.md` | Step 2 |

## Deleted

None.
