# Scriptorum 0.7.5 (0.7.0 step 6) — Changes

Base: **0.7.4** (0.7.0 step 5, on `build/0.7.0`, commit 0af087f). The last of six steps of 0.7.0: the rest of extension modules (design document F25, issue #27), outcomes approved on 19 November 2026: the Extensions tab in the left pane, suggestions and pictures, How to write an extension. No chat panel; it waits for an AI extension, if one is ever built.

- **The Extensions tab** beside In this scene, while an extension is switched on: a foldable section per extension, the most recently active open, with its findings, pictures, open suggestions and settings. The floating findings panel of 0.7.4 is gone.
- **Suggestions** for a whole block: a new source for it, or a new block after it. Shown under the block in the editor with the changed words marked and listed in the tab; Accept splices only that block's source, as one undo step; a block changed since is refused.
- **Pictures** (PNG or JPEG): Use stores the picture in the adventure's images and inserts an image block with its description after its block; Set as portrait on a loose person card or on its codex entry; Regenerate runs the item again; Cancel drops it.
- **How to write an extension** in Help, on the website and in the project, with a worked example the tests build from the guide's own code blocks.
- The extension calls `adventure.blocks`, `suggest.replace`, `suggest.add` and `picture.show`; the API stays 1.1 (not released yet) with a larger surface.

Issues: Refs #27.

## Added

| File | Why |
|---|---|
| `tools/guides/how-to-write-an-extension.md`, `scriptorum/bundled/scriptorum.en/strings/guide-extension.json` | The third author guide (F25.19); the strings are made by tools/make_guides.py |
| `tests/test_step6.py` | T-EXT-17 to T-EXT-22 |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.5 |
| `scriptorum/api/extensions.py` | Blocks for extensions, suggestions, pictures, the Extensions tab's contents |
| `scriptorum/core/exthost.py` | `ext.blocks`, `ext.suggest_replace`, `ext.suggest_add`, `ext.picture` |
| `scriptorum/app/bridge.py` | Slots for the tab, suggestions and pictures |
| `scriptorum/ui/index.html`, `scriptorum/ui/styles.css` | The lower-pane tabs and the Extensions tab; suggestion cards; the floating findings panel removed |
| `ui-src/app.ts`, `ui-src/guide.ts`, `scriptorum/ui/dist/app.js` | The tab, suggestion cards under their blocks, pictures, the guide in Help |
| `scriptorum/bundled/scriptorum.en/strings/error.json`, `ext.json`, `menu.json` | The new texts |
| `tools/make_guides.py`, `tools/build_site.py`, `docs/site/zensical.toml`, `docs/site/index.md` | The third guide in the app and on the website |
| `scriptorum/api/surface.json`, `docs/API.md` | The new operations and extension calls |
| `CHANGELOG.md`, `TEST-REPORT.md`, `CHANGES.md` | This step |
| `tests/test_step4.py`, `tests/test_step5.py`, `tests/test_m5e.py` | Corrections for the design change |
| `tests/scenarios/run_use_scenarios.py` | Suggestions, a picture and the guide in T-USE-02 |

## Deleted

Nothing.
