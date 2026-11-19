# Scriptorum 0.7.4 (0.7.0 step 5) — Test Report

| | |
|---|---|
| Version | 0.7.4, step 5 of 0.7.0 (extension modules, F25, issue #27) |
| Platform | Linux 6.18 (x86-64), headless (`QT_QPA_PLATFORM=offscreen`) |
| Python | 3.13.18 |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · keyring 25.7.0 (new) |
| Date | 19 November 2026 |
| Result | **434 passed**, 0 failed, 0 skipped (on a machine without Zensical: 433 passed, 1 skipped, T-DOC-05) |

## This step

Extension modules (design document F25, sections A to C, the findings list and point 18): Block all connections outside the app, on by default; the one-time offline message; installing an extension with the author's agreement to what it needs; licences, signatures and the API version; Settings ▸ Extensions with settings and secrets in the keychain; each switched-on extension in a process of its own, with its needs enforced, writes as one named undo step, a time limit and a crash count; the Extensions menu, block actions and the findings list. The internal API is version 1.1. The previous build's 412 tests passed on this branch before anything was changed (0.7.3).

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.3 | Pass | With the corrections below |
| T-EXT-01 | Pass | New, three tests. On by default; while on the gate refuses every purpose and records the refusals, Check for updates answers "blocked" with nothing sent, the weekly check never runs, Download and install is refused; the window shows the message and Open Settings, which opens Application with the switch; with it off the check works as before |
| T-EXT-02 | Pass | New. No weekly question; the offline message (exact wording) once, on a new install and on one that had the weekly check on, which starts blocked |
| T-EXT-03 | Pass | New, two tests. Needs in words before installing; nothing installed without agreement; same needs install without asking; an added need asks again and is named; the older version is replaced; a .py file in a theme and a compiled file (.so, .pyd, .dll, .exe) in an extension are refused, the file named |
| T-EXT-04 | Pass | New. Network plus writes refused (fixed host, entered address, localhost) with the exact message; suggests and none install; http only to localhost |
| T-EXT-05 | Pass | New. Seven GPL-compatible licences accepted; proprietary, CC-BY-NC-4.0 and none refused, named |
| T-EXT-06 | Pass | New. Signed with a test key: verified; a file changed after signing, another key, or no signature: unverified |
| T-EXT-07 | Pass | New. api 1.x and 1.1 accepted; 2.x refused naming both versions; 1.9 refused |
| T-EXT-08 | Pass | New, core and window. No process and no items until switched on; switched on, its process runs and an Extensions menu appears; kept after a restart; "needs the network" while blocked |
| T-EXT-09 | Pass | New, core and window. Another process id than the app's; the findings list drawn by the app, `<b>` shown as text; a click goes to the line |
| T-EXT-10 | Pass | New. Covered call answered; undeclared and unknown calls refused plainly; text events heard only with reads text; an extension that reads nothing hears none |
| T-EXT-11 | Pass | New, core and window. Two chapters changed in one undo step named "Checker: Mark every chapter"; the Edit menu reads "Undo Checker: Mark every chapter"; one undo brings both back; writes from an event, after the author changed the text, and in a read-only adventure refused |
| T-EXT-12 | Pass | New. A crash and a hang (limit shortened to 1.5 s) each give a plain message, the adventure untouched; the third failure switches it off; switched on by hand it works again |
| T-EXT-13 | Pass | New. Blocked: refused naming the switch, nothing sent; allowed: declared host, entered address and localhost go through the gate, other hosts and http to another computer refused; the secret is filled in by the app ("Bearer s3cret"); a changed address no longer allows the old host |
| T-EXT-14 | Pass | New, two tests. Settings kept after a restart; a choice outside its options refused; the secret only in the keychain (stand-in), not in state.json; without a keychain in a file with mode 600; removing clears state, data folder, secret file and keychain entry; keyring pinned, in About and carried into the installers |
| T-EXT-15 | Pass | New, core and window. Six menus, no Extensions menu, "No extension is installed."; with connections on and no extension, only the update request |
| T-EXT-16 | Pending | On your computer: install `tests/extensions/heading-check` (packed as the try-it commands show), enter a secret, check it is in the keychain, remove it. Its automated part passes: the extension installs and lists the headings |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine (the app is now offline by default) |
| T-USE-01, T-USE-02 | Pass | 150 checks, all passed. New: T-USE-02 finds the app offline, Check for updates says so and Open Settings leads to the switch, which is turned off before the update steps; at the end it installs a small extension (needs shown, unverified), switches it on, runs Extensions ▸ Check headings and sees its findings |

## Looked at

The consent dialog, Settings ▸ Extensions with an installed extension, the findings list over the editor, the Extensions menu and the blocked update check, in the scenario's screenshots. Markup in a finding shows as text.

## Found while building

- **The "text changed while it worked" check** first compared against the text at the extension's first write, so a change by the author before that write would have been overwritten. It now compares against the text as it was when the author clicked.
- **An extension's message was cut at 300 characters**, which broke longer answers. The limit is 2,000.

## T-USE findings

- Unchanged: issue #33 (friction, later), and the script's fixed note about the map dialog (issue #3 is closed).

## Corrections to existing tests (the design changed)

- **T-API-01** (`tests/test_api.py`): API 1.1.
- **T-API-06** (`tests/test_api.py`), **T-UI-32** update check in the window (`tests/test_m6c.py` fixture), **T-REL-05**, **T-UI-44**, **T-UI-45** (`tests/test_m6c5.py`): connections are turned on first, since they are blocked by default.
- **T-UI-32** first start (`tests/test_m6c.py`): the offline message instead of the weekly question.
- **T-UI-19** (`tests/test_ui_m4.py`): Extensions in the Settings sidebar.
- **T-UI-34** (`tests/test_m6b.py`): keyring in About ▸ Under the hood.
- **T-REL-09** (`tests/test_m6d.py`), **T-REL-14** (`tests/test_m6f.py`): kit 1.0.5.

## Tests added

T-EXT-01 (3), T-EXT-02, T-EXT-03 (2), T-EXT-04 to T-EXT-07, T-EXT-08, T-EXT-09, T-EXT-11 (core and one window test for 08, 09 and 11), T-EXT-10, T-EXT-12, T-EXT-13, T-EXT-14 (2), T-EXT-15 (2), T-EXT-16's automated part, and T-EXT-16 by hand. All are in the Test Plan, saved before the step was built.

## Hand checks for the project manager

- First start of this build: the offline message appears once. Help ▸ Check for updates says connections are blocked; Open Settings goes to the switch.
- T-EXT-16 on your own computer (the try-it commands include a small extension to install).

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`

Unchanged since 0.6.4.
