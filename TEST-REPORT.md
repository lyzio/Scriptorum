# Scriptorum 0.7.0 step 1 — Test Report

| | |
|---|---|
| Version | 0.7.0, step 1 of 5 (the internal API, F23, issue #29) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 |
| Date | 18 November 2026 |
| Result | **383 passed**, 0 failed, 0 skipped |

## This step

Built on 0.6.10 (accepted, `main` at 598a0b6). Before any change the 0.6.10 suite ran here: 375 passed. The step adds 8 tests in `tests/test_api.py`; every earlier test passes unchanged except T-UI-32's network-code check, corrected because the design moved the requests into the gate (below). The m1-basic checksum is unchanged.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.6.10 | Pass | Unchanged, with the one correction below. The window tests drive the interface through the bridge as before, so they check that every call still reaches the core |
| T-API-01 | Pass | New, two tests. The surface (102 operations, 9 events) matches `scriptorum/api/surface.json` for API 1.0; every operation is in its area's table in `docs/API.md` and every event in its list; an operation added without a new version makes the test fail |
| T-API-02 | Pass | New, two tests. For m1-basic, m3-world, m5-plain and m6-clues every read operation of the five areas gives plain JSON data; a change, a preview build, a save and an export work through the API; m1-basic exported through the API has the reference checksum |
| T-API-03 | Pass | New. No adventure open, a file that does not exist, an unknown entry, an http update address and a read-only adventure each give a plain error with its key; an unexpected error is written to a crash log and given plainly, and the codex is unchanged |
| T-API-04 | Pass | New. Opening, a text change, a codex change, a build, an app setting, saving and closing are each announced once, in that order, with plain details; a failing listener does not stop the others; after unsubscribing nothing more is heard |
| T-API-05 | Pass | New. The bridge imports nothing from `scriptorum/core`; each of its 113 slots uses Qt or passes its call to the API; 985 lines, down from 1,424 |
| T-API-06 | Pass | New. Only `scriptorum/api/net.py` contains network code; the update check asks through the gate, which records the address; without the gate the core asks nothing; http and unknown purposes are refused |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-USE-01, T-USE-02 | Pass | 129 checks, all passed, as in 0.6.10: the scenario script drives the real window, so every action goes through the new bridge and the API |

## Found while building

- **Opening a file that does not exist** (for example from Open recent after the file was moved) raised a raw error inside the bridge, so the window said nothing. The API now answers with the plain message "“…” could not be read: No such file or directory" (new text `error.scav.cannotRead`), and the window shows it like any other refusal to open.
- **Find gave some places as Python tuples.** They reached the interface as lists anyway, through JSON; the API now gives plain lists itself.

## T-USE findings

The same two as in 0.6.10: pasted labels stay after converting (issue #2, planned for step 3) and the script's fixed note about the map dialog (issue #3 is closed).

## Corrections to existing tests

- **T-UI-32** (`tests/test_m6c.py`, `test_T_UI_32_no_other_network_code`): it expected the network code in `core/updates.py`; from 0.7.0 it is in the API's gate, `api/net.py` (F23.6). The design changed.

## Tests added

T-API-01 (2), T-API-02 (2), T-API-03, T-API-04, T-API-05, T-API-06. All are in the Test Plan, added before the step was built.

## Hand checks for the project manager

Nothing should look or behave differently. Use the app as usual for a while: open and save, edit in Visual and Source mode, the codex and a map, export, Settings, About, Check for updates, a second tab. Anything that behaves differently from 0.6.10 is a fault of this step.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4.
