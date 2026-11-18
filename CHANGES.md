# Scriptorum 0.7.2 (0.7.0 step 3) — Changes

Base: **0.7.1** (0.7.0 step 2, on `build/0.7.0`, tested by the project manager on 18 November 2026: 392 passed). The third of five steps of 0.7.0 on the branch `build/0.7.0`, the first with its own number (decided 18 November 2026): lists in the Visual editor (issue #5), footnotes edited in place (issue #4), links between codex entries both ways (issue #17) and pasted labels removed when converting (issue #2). Outcomes approved on 18 November 2026 and written into the design document (F4, F7.7, F3).

- **#5**: a list block in the core (`- item`, `+ item`, up to three levels) and a list editor: Enter, Tab, Shift+Tab, Enter on an empty item, Backspace, bulleted or numbered from right-click and Format, Insert ▸ List.
- **#4**: a click on a footnote chip opens a box with its text; Enter or a click outside saves, Esc cancels. The footnote's text is inline markup from now on, so bold and italic print.
- **#17**: a link on one entry's Linked to shows, and prints, on the other entry's Linked to too, marked as set on that entry; removing it there removes the stored link.
- **#2**: Convert to removes a typed label and a list marker, sets a variant named by its label, and fills the fields named on the lines after it. The words come from the element's names and field labels plus an optional `paste_labels` list in its definition (English and Swedish for the core elements).
- The README and the 0.7.0 changelog say the Windows installer was tested with 0.6.9 and works (the project manager, 18 November 2026).

The file format, the API version (1.0), the installers and the release process are unchanged. Issues: Refs #5, #4, #17, #2.

## Added

| File | Why |
|---|---|
| `tests/test_step3.py` | T-SRC-21 (3), T-WORLD-36, T-UI-55, T-UI-56, T-UI-57 (2) |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.2 |
| `scriptorum/core/source.py` | The list block: `parse_list`, `list_text`; words of lists counted (#5) |
| `scriptorum/core/session.py` | Find and replace and the preview's element order see list items (#5); `linkedFrom` in an entry's information (#17); the elements' paste labels sent to the editor (#2) |
| `scriptorum/core/world.py` | `link_field`, `links_from_others`; the build's entries carry links both ways (#17); codex references in lists (#5) |
| `scriptorum/bundled/scriptorum.core/elements/*.json` (scene, read-aloud, information, person, creature, handout, box) | `paste_labels`, English and Swedish (#2) |
| `scriptorum/bundled/scriptorum.core/typst/elements.typ` | A footnote's text is printed as markup, with straight quotes kept (#4) |
| `scriptorum/bundled/scriptorum.en/strings/editor.json`, `codex.json` | List, List item, Bulleted list, Numbered list; "set on that entry" (#5, #17) |
| `tools/guides/how-to-write-a-game-system.md`, `strings/guide-game-system.json` | `paste_labels` in an element's definition (#2) |
| `ui-src/editor.ts` | The list editor, footnote editing, label removal in Convert to (#5, #4, #2) |
| `ui-src/app.ts` | List in the Insert menu, the + menu, right-click and Format; footnote typed text escaped and its chip labelled from its markup; test hooks `doc` and `focusedKind` (#5, #4) |
| `ui-src/world.ts` | Links from other entries in Linked to, with × (#17) |
| `ui-src/inline.ts`, `ui-src/model.ts` | A chip carries its kind as a class; the list block and paste labels in the model |
| `scriptorum/ui/styles.css`, `dist/app.js`, `tests/js/inline.cjs` | Styles for lists, the footnote box and links from other entries; the rebuilt interface |
| `tests/scenarios/run_use_scenarios.py` | T-USE-01 checks that the labels went; T-USE-02 writes a list and edits a footnote |
| `tests/test_source.py`, `test_m6c2.py`, `test_ui_m2.py`, `test_m6f.py`, `test_m6d.py` | Corrected because the design changed (see TEST-REPORT.md) |
| `README.md`, `CHANGELOG.md`, `CHANGES.md`, `TEST-REPORT.md` | 0.7.2; the Windows installer tested with 0.6.9 |

## Deleted

None.
