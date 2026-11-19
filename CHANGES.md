# Scriptorum 0.7.7 — Changes

Base: **0.7.6** (on `build/0.7.0`, commit 6e0e5ad). Three issues, outcomes approved on 19 November 2026 (design document F7.4, F4 and 11.10).

- **#30, a full-width section never covers a column.** Typst moves an unbreakable block out of the way of a full-width section only when the block does not measure its own width; maps, framed boxes and quotes do, and were drawn under it. The core element kit now sets every element a theme draws as an unbreakable block, and every never-split section, as one box of its measured size, keeping the theme's spacing. What the themes draw is unchanged (the reference PDF is byte-identical). An element too tall to fit beside a full-width section moves whole to the next column or page.
- **#33, pasted knowledge lines.** Converting a pasted line to a person also turns the lines after it that start with "She knows", "He knows", "Knows", "Hon vet", "Han vet" or "Vet" into Information inside the card, with the variant from the word in brackets (or the default one), in the same undo step. The words are a new `knows` list in the person card's `paste_labels`; How to write a game system says so. "Publik" joined Information's labels for Public.
- **#31, elements inside a Box.** Inside a Box, Information, read-aloud, check, dice and pacing notes are drawn without their own frames, separated by a thin line in the theme's rule colour; each keeps its label, icon and colours, the secret's fill included. Person and creature cards keep their frames. All four themes.

Issues: Refs #30, Refs #33, Refs #31.

## Added

| File | Why |
|---|---|
| `tests/test_step7.py` | T-BUILD-34, T-LOOK-14, T-UI-59 |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.7 |
| `scriptorum/bundled/scriptorum.core/typst/elements.typ` | #30: `_shield`, applied to every theme renderer and to never-split sections |
| `scriptorum/bundled/scriptorum.<theme>/templates/_style.typ` (four themes) | #31: `inside-box`, `in-box()`, `box-seen`, `box-part`, `box-pacing` |
| `scriptorum/bundled/scriptorum.<theme>/templates/box.typ`, `information.typ`, `read-aloud.typ`, `check.typ`, `dice.typ`, `pacing.typ` (four themes) | #31: the Box marks its text; the five kinds draw their frameless part inside it |
| `scriptorum/bundled/scriptorum.core/elements/person.json`, `information.json` | #33: the `knows` words; "Publik" |
| `ui-src/editor.ts`, `ui-src/model.ts`, `scriptorum/ui/dist/app.js` | #33: `takeKnowledge` in Convert to |
| `tools/guides/how-to-write-a-game-system.md`, `scriptorum/bundled/scriptorum.en/strings/guide-game-system.json` | #33: the guide describes `knows` |
| `tests/scenarios/run_use_scenarios.py` | T-USE-01 checks the knowledge lines instead of noting them as friction |
| `CHANGELOG.md`, `TEST-REPORT.md`, `CHANGES.md` | This step |

## Deleted

Nothing.
