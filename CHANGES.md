# Scriptorum 0.7.0 step 1 — Changes

Base: **0.6.10** (`main`, accepted and merged on 18 November 2026). The first of five steps of 0.7.0 on the branch `build/0.7.0` (design document section 10, decided 18 November 2026): **the internal API** (F23, issue #29), alone, with no visible change.

- **`scriptorum/api/`**: the operations the interface uses, grouped by area (app, adventure, codex, build, modules), each taking and returning plain JSON-safe data; refusals as plain errors with their key; unexpected errors logged and given plainly; events; API version 1.0 with its stored surface
- **the bridge** keeps only Qt (dialogs, file pickers, windows, timers, the clipboard, local file addresses, the WebChannel signals) and passes everything else to the API; 1,424 lines became 985, and it imports nothing from `scriptorum/core`
- **one network gate** (`scriptorum/api/net.py`): the update check and the download go through it; the core's update module no longer opens connections
- **`docs/API.md`** describes every operation and event; `docs/DEVELOPING.md` points to it
- found on the way: opening a file that does not exist raised a raw error, so the window said nothing; it now says so plainly

The core, the interface, every file format, the installers and the release process are unchanged. Issues: #29 (step 1 of the internal API).

## Added

| File | Why |
|---|---|
| `scriptorum/api/__init__.py` | The API's entry: `Api`, `API_VERSION`, `surface()` (F23) |
| `scriptorum/api/workspace.py` | `Api`: the tabs, events, network gate and the five areas |
| `scriptorum/api/app.py` | App settings, palettes, About, start-up checks, spell check, zoom, updates |
| `scriptorum/api/adventure.py` | Tabs, new, open, save, recovery, snapshots, chapters, settings page, find, images, fonts |
| `scriptorum/api/codex.py` | Codex entries and types, maps, the chart, the M3 upgrade |
| `scriptorum/api/build.py` | The preview build and exports |
| `scriptorum/api/modules.py` | Game systems, the module manager, versions, Change game system |
| `scriptorum/api/errors.py` | Plain errors (F23.2) |
| `scriptorum/api/events.py` | The events (F23.3) |
| `scriptorum/api/net.py` | The one network gate (F23.6) |
| `scriptorum/api/surface.json` | The stored surface of API 1.0 (T-API-01) |
| `docs/API.md` | Every operation and event |
| `tests/test_api.py` | T-API-01 to 06 |

## Changed

| File | Why |
|---|---|
| `scriptorum/app/bridge.py` | Keeps only Qt; every other call goes to the API; the tests' hooks (`update_opener`, `update_requests`, …) now point into the API |
| `scriptorum/core/updates.py` | `fetch` and `fetch_pack` moved into the network gate; `check` and `install` read through the reader they are given |
| `scriptorum/bundled/scriptorum.en/strings/error.json` | `scav.cannotRead`: a file that could not be read |
| `tests/test_m6c.py` | T-UI-32's network-code check names the gate instead of `core/updates.py` (design changed) |
| `docs/DEVELOPING.md` | Points to `scriptorum/api/` and `docs/API.md` |
| `CHANGELOG.md` | The 0.7.0 section, step 1 |
| `pyproject.toml`, `scriptorum/__init__.py`, `ui-src/package.json` | Version 0.7.0 |
