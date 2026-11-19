# Scriptorum 0.7.4 (0.7.0 step 5) — Changes

Base: **0.7.3** (0.7.0 step 4, on `build/0.7.0`). The fifth of six steps of 0.7.0: extension modules (design document F25, issue #27), outcome approved on 19 November 2026. This step builds sections A to C of F25, the findings-list panel and point 18 (settings, secrets in the keychain, removal), as decided the same day; the chat, suggestion and picture panels and How to write an extension follow in 0.7.5.

- **Block all connections outside the app** (F25.1 to F25.3): a switch in Settings ▸ Application, on by default, checked in the API's one network gate. While on, nothing is sent: Check for updates says so, with Open Settings. The first-start question about the weekly check gives way to a one-time offline message. D9 changed accordingly.
- **Installing an extension** (F25.4 to F25.9): kind `extension`, the only kind that may hold `.py` files; compiled code refused in every kind. What it needs (reads, changes, network hosts) is shown in words before installing and the author must agree; an update that needs more asks again. Network plus writes is refused. GPL-compatible licences only. Signed with the project's key: "from the Scriptorum project"; otherwise unverified. It names the API version it needs.
- **Running** (F25.10 to F25.16): off until switched on in Settings ▸ Extensions. Each switched-on extension runs in its own process (the app's own program, `--scriptorum-extension-host`), talking with JSON messages. Every call is checked against its needs; writes only during a command the author started, as one undo step named after it, refused if the author changed the text meanwhile; events only as its needs cover. 30 seconds without an answer, or a crash, gives a plain message; three failures switch it off. Network requests only through the gate, to declared hosts, never following a redirect; secrets are filled in by the app.
- **Interface** (F25.17): an Extensions menu (only when a switched-on extension has a menu item), block actions in the block's right-click menu, and a findings list drawn by the app, where a click goes to the place.
- **Settings and secrets** (F25.18): each extension's settings in Settings ▸ Extensions; secrets in the computer's keychain through keyring 25.7.0 (MIT, new pinned dependency), or in a file only the author's user can read where there is no keychain; removing an extension removes everything it stored.
- The internal API is version 1.1 (the extensions area, the switch and the offline message). Packaging kit 1.0.5 carries keyring with its keychain backends.

The file format and the release process are unchanged. Issues: Refs #27.

## Added

| File | Why |
|---|---|
| `scriptorum/core/extensions.py` | Checks an extension's manifest, needs, licence, API version and signature; the author's state, settings and secrets (F25.4 to F25.10, F25.18) |
| `scriptorum/core/exthost.py` | The extension's own process: loads it, runs its commands, passes its calls and findings (F25.11) |
| `scriptorum/api/extensions.py` | The API's extensions area: install, on and off, settings, removal, running, needs enforced, writes as one undo step, time limit and crashes, network through the gate (F25) |
| `scriptorum/bundled/scriptorum.en/strings/ext.json`, `connections.json` | The texts of extensions and of the offline message (F15) |
| `scriptorum/licences/parts/keyring.txt` | keyring's licence and those of the libraries it brings, for About ▸ Under the hood |
| `tools/sign_extension.py` | Signs one of the project's extensions with the update key (F25.8) |
| `tests/test_step5.py` | T-EXT-01 to T-EXT-15, and T-EXT-16's automated part |
| `tests/extensions/heading-check/`, `tests/extensions/README.md` | A small extension for the hand check T-EXT-16 (not shipped in the app) |

## Changed

| File | Why |
|---|---|
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.4; keyring 25.7.0 pinned |
| `scriptorum/__main__.py` | The extension-host mode of the installed app |
| `scriptorum/api/net.py` | The switch checked first; an extension's request (no redirects, https or localhost http) |
| `scriptorum/api/app.py` | The update check, weekly check and install respect the switch; the offline message |
| `scriptorum/api/workspace.py`, `scriptorum/api/__init__.py`, `scriptorum/api/surface.json` | API 1.1 with the extensions area |
| `scriptorum/api/modules.py` | Install module… hands an extension to the agreement step |
| `scriptorum/app/bridge.py` | Extension slots, the notice signal, the timer that handles their messages; extensions start with the window and stop with it; the offline message |
| `scriptorum/core/modules.py` | The kind `extension`; `.py` only in extensions, compiled code in none; the `api` requirement |
| `scriptorum/core/modmanager.py` | No font or Typst checks for extensions; extensions not listed in Settings ▸ Modules |
| `scriptorum/core/appsettings.py` | `connections_blocked` (on by default) and `offline_notice_shown` |
| `scriptorum/core/about.py`, `strings/about.json` | keyring in About ▸ Under the hood |
| `scriptorum/bundled/scriptorum.en/strings/error.json`, `menu.json`, `settings.json`, `update.json` | The new texts |
| `scriptorum/ui/index.html`, `scriptorum/ui/styles.css` | Settings ▸ Extensions, the agreement dialog, the findings panel, Open Settings in the update window |
| `ui-src/app.ts`, `ui-src/shell.ts`, `scriptorum/ui/dist/app.js` | The switch, the offline message, Settings ▸ Extensions, the Extensions menu, block actions, findings, named undo |
| `packaging/build.py`, `packaging/common/scriptorum.spec`, `packaging/kit.json`, `packaging/README.md` | Kit 1.0.5: keyring required, carried with its backends and metadata |
| `docs/API.md` | API 1.1: the extensions area and the calls an extension may make |
| `docs/DEVELOPING.md`, `README.md`, `CHANGELOG.md` | Extensions, offline by default |
| `tests/test_api.py`, `test_m6b.py`, `test_m6c.py`, `test_m6c5.py`, `test_m6d.py`, `test_m6f.py`, `test_ui_m4.py` | Corrections for the design change (TEST-REPORT.md lists them) |
| `tests/scenarios/run_use_scenarios.py` | The offline steps and the extension steps of T-USE-02 |
| `TEST-REPORT.md`, `CHANGES.md` | This step |

## Deleted

Nothing.
