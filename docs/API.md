# The internal Scriptorum API

Version **1.1** (1.0 in 0.7.0 step 1, design document F23, issue #29; 1.1 in 0.7.4 adds the extensions area and Block all connections outside the app, F25, issue #27).

The internal API is the one layer between Scriptorum's core (`scriptorum/core/`) and everything that uses it. The app's own interface reaches it through the bridge (`scriptorum/app/bridge.py`), which keeps only what needs Qt: dialogs, file pickers, windows, timers, the clipboard, local file addresses for the web view and the WebChannel signals. From 1.1 extension modules (F25) use it too, each from a process of its own, through the calls listed under extensions below.

```python
from scriptorum.api import Api
from scriptorum.core.session import Session

api = Api(Session.start())
api.adventure.open("/path/to/adventure.scav")
api.adventure.chapter(0)                    # {"text": ..., "doc": ...}
api.build.export("/tmp/adventure.pdf")      # {"ok": True, ...}
```

## Rules

- **Plain data.** Every operation takes and returns JSON-safe data: text, numbers, true and false, `None`, lists and maps. Nothing returned is a Python object, so the same calls can travel as JSON over a pipe.
- **Plain errors.** An operation that cannot do what it was asked returns `{"ok": False, "error": <text>, "key": <key>}`. The text comes from the interface-language module (F15); the key is its name there. No raw exception leaves the API. An unexpected error is written to a crash log in the app's own folder (F2.11) and returned as a plain error (`"logged": true`).
- **The active tab.** Several adventures can be open, one per tab (F2.2). Operations work on the active tab; `adventure.switch_tab` changes it.
- **One network gate.** Every network request goes through `api.net.fetch(purpose, address)` (`scriptorum/api/net.py`), and no other code in the app opens a connection (F23.6, D9). The purposes are `update-file` (F21) and `update-pack` (F22), each only when the author asks, and from 1.1 a switched-on extension's request (`api.net.request`, F25.16). While Block all connections outside the app is on, which is the default, the gate refuses every request before anything is sent (`ConnectionsBlocked`; F25.1). `api.net.requests` lists every address asked and `api.net.refused` every one the switch stopped.
- **Versions.** A change that breaks a caller raises the major number; an addition raises the minor number. `scriptorum.api.surface()` lists every operation and event with its inputs; `scriptorum/api/surface.json` holds the surface of this version, and a test fails when the two differ (T-API-01).

## Events

`api.events.subscribe(handler)` hears every event as `handler(name, details)`; it returns a function that stops listening. A handler that fails is skipped; it never stops the operation.

| Event | Details | When |
|---|---|---|
| `adventure.opened` | tab, title, readOnly | an adventure was made, opened or restored, or a tab was switched to |
| `adventure.closed` | tab | a tab was closed |
| `adventure.saved` | tab, path | the adventure was saved |
| `adventure.edited` | tab | an image, portrait or font was added; nothing needs building |
| `text.changed` | tab | the text, the settings page, the theme or a module version changed: the preview needs a new build |
| `codex.changed` | tab | a codex entry, type, map or the chart changed: the preview needs a new build |
| `settings.changed` | what (`"app"`) | the app settings changed (F18) |
| `modules.changed` | rebuild | a module was installed, enabled, disabled or removed; `rebuild` when an open adventure is affected |
| `build.finished` | tab, ok, pages, errors, warnings | a preview build finished (counts) |

## app — the app itself

| Operation | Inputs | Returns |
|---|---|---|
| `strings` | | every interface text of the chosen language (F15) |
| `text` | key, details | one interface text with its details filled in |
| `ui_ready` | | the window is up: marks this version as started (F22.5) |
| `settings` | | the app settings, palettes, interface languages and the module list (F14, F16, F18) |
| `set_settings` | changes | stores the changes at once (out-of-range values are ignored); the settings again |
| `save_palette` | request (name, light, dark) | New palette from this one, saved as a palette module and chosen (F16) |
| `reset_palette` | | back to Claret & Ink |
| `zoom` / `set_zoom` | percent | the whole window's zoom, one of the steps 50 … 200 (F9, issue #16) |
| `preview_zoom` / `set_preview_zoom` | wanted | the preview's zoom for the active adventure (F7.2) |
| `about` | | Help ▸ About: version, programs, packages, fonts, dictionaries, licences (F9) |
| `about_text` | ref | the full licence or notice text behind a row |
| `idea_site` | | the address "Idea by lyzio" links to |
| `crash_log_folder` | | the folder of the crash logs (F2.11) |
| `startup_report` | | what the start-up checks found missing (F9) |
| `check_installation` | | Help ▸ Check installation: every check again |
| `theme_self_test` | tab | the slower theme self-test (9.7.5) |
| `spell` | words | which words are misspelt, with the adventure's language (F4.8) |
| `suggest` | word | suggestions for one word |
| `update_address` | | the update address in use: the one entered, or the built-in one (F22) |
| `check_updates` | auto | asks for the update file through the network gate; what it says (F21) |
| `can_install` | | whether the last update file named a pack this app can install |
| `install_update` | | downloads, checks and unpacks that pack for the next start (F22) |
| `use_moved_address` | | the signed update file said the address moved, and the author agreed |
| `set_update_address` | address | Settings ▸ Updates ▸ Update address; only https |
| `version_info` | | the version running, the app's own, the one Go back would run, the start notice |
| `go_back` | | Help ▸ Go back to version X, from the next start |
| `weekly_check_due` | | whether the weekly check should run now (F21.4) |
| `update_prompt` | ask_at_start | from 1.1 always `{"ask": false}`: the question gave way to the offline message (F25.2) |
| `answer_update_prompt` | weekly | the answer to it (kept for older callers) |
| `connections_blocked` | | whether Block all connections outside the app is on (F25.1) |
| `offline_notice` | show_at_start | whether to show the one-time offline message (F25.2) |
| `offline_notice_seen` | | it was shown |
| `download_page` | | the download page named in the last update file |

## adventure — the open adventures

| Operation | Inputs | Returns |
|---|---|---|
| `info` | | the active tab: title, game system, theme, modes, recent files and more |
| `editor_info` | | what the editor needs: elements, kinds, codex types |
| `is_open` | | whether the active tab holds an adventure |
| `unsaved` | tab | whether a tab has unsaved changes |
| `title` | | the active adventure's title, or "Untitled adventure" |
| `tabs` | | every tab: id, title, unsaved, read-only, active |
| `switch_tab` | tab_id | makes that tab active |
| `close_active_tab` | | closes the active tab (the caller asked about unsaved changes first) |
| `close_all` | | closes every tab, before quitting |
| `new` | data (title, gameSystem, theme) | a new adventure, in an empty tab or a new one (F1) |
| `open` | path | opens a .scav file or an adventure folder; an already open one becomes active (F2) |
| `open_example` | | a copy of the example adventure in the user's documents (F20) |
| `needs_file_name` | | whether saving needs a file name first |
| `path` | | the file the adventure was opened from or saved to |
| `save_to` | path, as_folder | saves, as a file or an unpacked folder (F2.4) |
| `save_suggestion` | | the file name Save as suggests |
| `export_suggestion` | kind, variant | the file name an export suggests |
| `recoveries` / `restore_recovery` / `discard_recovery` | session_id | recovery copies after a crash (F2.5) |
| `snapshot_tick` | | takes the snapshots that are due (F2.6) |
| `snapshots` / `revert_to` | snapshot_id | the snapshots, and going back to one |
| `chapter` | index | a chapter's text and its document model |
| `set_chapter_text` | index, text | Source mode's text |
| `set_chapter_doc` | index, doc | the Visual editor's document model |
| `block_source` | block | one block's source, as Hybrid mode shows it (F4.1) |
| `settings` / `set_settings` | data | the adventure settings page (F7.3, F7.9) |
| `set_theme` | theme_id | the adventure's theme (F8) |
| `find` | query, match_case | every place the text occurs (F4.7) |
| `replace_all` | query, replacement, match_case | how many were replaced |
| `add_image` | name, data_base64 | an image dropped into the editor (F4.6) |
| `add_image_file` / `add_portrait_file` / `add_font_file` | path | an image, a person's portrait (11.4) or a font through the font guard (F11) |
| `fonts` | | the adventure's own fonts |
| `image_file` | path | a local copy of an adventure image, for showing it |

## codex — codex, maps and the relationship chart

| Operation | Inputs | Returns |
|---|---|---|
| `codex` | | every type, entry, map and handout (F3) |
| `entry` | entry_id | one entry with where it is used |
| `create_entry` | type_id, title, fields, folder | a new entry |
| `update_entry` | entry_id, data | the changed entry |
| `delete_entry` | entry_id | refused while the entry is used, with the places (F3.8) |
| `save_type` | data | an author-defined codex type |
| `convert_info` / `convert_to_entry` | chapter, path, type_id, link | Convert to codex entry (F3) |
| `scene_entries` | chapter, line | "In this scene" (F3.5) |
| `undo` | | undoes the last codex or map change |
| `map_info` | map_id | a map and a local copy of its base image (F5) |
| `create_map` / `create_map_file` | title, name, data_base64 / path | a new map from a JPEG or PNG |
| `update_map` / `delete_map` | data / map_id | |
| `chart` / `set_chart_positions` | data | the relationship chart (F3.9) |
| `upgrade_offer` / `apply_upgrade` | data | text values that can become codex links (F3.12) |

## build — the preview and exports

| Operation | Inputs | Returns |
|---|---|---|
| `preview` | player, show_breaks | builds the preview now: its SVG page files, warnings or errors (F7.1, F7.2) |
| `export` | path, variant | exports to the file: `full` (the adventure PDF), `handouts`, `booklet`, `print-shop` or `accessible` (F7.6, F17) |

## modules — game systems, themes and the module manager

| Operation | Inputs | Returns |
|---|---|---|
| `game_systems` | | the installed game systems with their themes (F1) |
| `install` | path | installs a .scmod with every check of 9.7 |
| `set_disabled` / `remove` | module_id, version | (F14) |
| `file_name` / `save_to` | module_id, version, path | Save as .scmod file… |
| `preview_version` / `apply_version` / `cancel_version` | which, version | tries another module version in the preview first (F14.3) |
| `game_system_fit` / `preview_game_system` | gs_id, version / data | Change game system (F14) |

## extensions — extension modules (F25, from 1.1)

| Operation | Inputs | Returns |
|---|---|---|
| `list` | | the installed extensions for Settings ▸ Extensions: on or off, needs in words, verified or not, settings (never a secret's value), whether the keychain is used, whether connections are blocked |
| `contributions` | | the menu items, block actions and panels of the switched-on extensions |
| `inspect` | path | what a .scmod file is; for an extension, its needs in words, the ones a newer version adds, verified or not, and whether the author must agree first; nothing is installed |
| `install` | path, agreed | installs an extension the author agreed to (F25.5); a newer version replaces the older one, keeping the author's state |
| `set_on` | ext_id, on | switches an extension on (its process starts) or off (it stops) (F25.10) |
| `set_setting` | ext_id, key, value | one setting; a secret goes to the keychain, or to a file only the author's user can read (F25.18) |
| `remove` | ext_id | removes it and everything it stored (F25.18) |
| `run` | ext_id, command, context | the author clicked one of its items; the answer comes later as a notice (`done`) |
| `findings` | | the findings lists shown |
| `running` | | the extensions whose process runs |
| `pump` | | handles what running extensions sent and notices a crash or a command over the time limit; the bridge calls it on a timer, on the window's thread |
| `stop_all` | | stops every extension's process (the window closes) |

Notices go to `api.extensions.listeners` (the bridge's `extensionNotice` signal): `done` (with `wrote` and `undoName` when it changed the text, one undo step), `findings`, `failed` (a crash, a start that failed, or 30 seconds without an answer, F25.14) and `switchedOff` (after three failures in one session).

### What an extension's process may ask (F25.13)

An extension runs in its own process (`scriptorum/core/exthost.py`) and talks to the app with one JSON message per line. Its calls are checked against the needs in its manifest; anything else is refused with a plain error and nothing changes.

| Call | Needs | Returns |
|---|---|---|
| `adventure.info` | reads text | title, read-only, chapters, game system and theme |
| `adventure.chapter` | reads text | `{"index", "text", "outline"}` of one chapter |
| `codex.codex`, `codex.entry` | reads codex | the codex, one entry |
| `adventure.settings` | reads settings | the adventure's settings |
| `adventure.set_chapter_text` | changes: writes, and only while a command the author started runs | one change; everything a command writes is one undo step, refused if the author changed the text meanwhile |
| `net.request` | a declared host (or the address entered in its settings) | through the gate, never following a redirect; `{secret:<id>}` in a header or the body is filled in by the app, so a secret never enters the extension's process |
| `settings.get` | | its own settings, without secrets |

Events it hears (F25.15): `adventure.opened`, `adventure.closed`, `adventure.saved`, `text.changed` and `build.finished` when it reads the text, `codex.changed` when it reads the codex.

