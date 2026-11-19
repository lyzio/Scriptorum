# Scriptorum 0.7.6 — Test Report

| | |
|---|---|
| Version | 0.7.6, on `build/0.7.0` after step 6 (the Latest release link on the documentation website, F24; issue #34) |
| Platform | GitHub Actions, ubuntu-24.04, Python 3.13, headless (the full suite); Linux (x86-64), headless, in the build session (the new and affected tests, with Zensical 0.1.2) |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · keyring 25.7.0 |
| Date | 19 November 2026 |
| Result | **441 passed**, 0 failed, 1 skipped (T-DOC-05, which needs Zensical): GitHub's Tests run for commit d32576d. In the build session T-DOC-05 also passed, with Zensical |

## This step

The website's sidebar ends with Latest release, after Status, linking to https://github.com/lyzio/Scriptorum/releases/latest. The design document was read as its changes since revision 439 (there were none), plus F24 and section 2 in full.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.5 | Pass | GitHub's run 44482017527 |
| T-DOC-07 | Pass | New. Read from the generated configuration: the last sidebar entry, at the top level after Status, is Latest release with the releases/latest address; it is the only entry that is not a page; the pages written are exactly the sidebar's pages; no guide text in Help names the address |
| T-DOC-05 | Pass | Ran in the build session with Zensical 0.1.2 (strict build, no warnings); it now also checks that the built site links to releases/latest and makes no page for it. Skipped on GitHub's Tests run, as before |
| T-DOC-01 to 04 | Pass | Unchanged (T-DOC-01 needed no correction, since the link is not a page) |
| T-REL-11, T-REL-14 | Pass | They read the changelog section of the app's version, so the in-progress section is now headed 0.7.6 |
| T-DOC-06 | Pending | After the merge into main and switching on GitHub Pages: also check that Latest release opens the newest release |
| T-EXT-16 | Pending | On your computer (keychain), as in 0.7.4 |
| T-BUILD-03 | Pending | Compare the checksum below on your machine |
| T-REL-02 | Pending | Network check on your machine |
| T-USE-01, T-USE-02 | Not run | Nothing this step touches is part of the app or used in the scenarios (the build procedure allows skipping them for such a build) |

## Looked at

The built site's Status page at 1440 × 900: Latest release is the last sidebar entry, under Status, in the sidebar's own style. Zensical's footer on the Status page also offers "Next: Latest release", since the footer follows the sidebar; it opens the same address.

## Found while building

Nothing.

## Corrections to existing tests

None. T-DOC-05 gained two checks for T-DOC-07.

## Tests added

T-DOC-07 (`tests/test_step4.py`), in the Test Plan before building.

## Sample checksum (Linux)

`m1-basic.pdf`: `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69` (unchanged since 0.6.4; nothing in this step prints).
