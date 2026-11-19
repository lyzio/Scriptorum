# Scriptorum 0.7.8 — Test Report

| | |
|---|---|
| Version | 0.7.8, on `build/0.7.0` (four general themes, F8) |
| Platform | GitHub Actions, ubuntu-24.04, Python 3.13, headless (the full suite); Linux (x86-64), headless, in the build session (the new and touched tests) |
| Pinned versions | PySide6 6.8.3 (Qt 6.8 LTS) · typst 0.15.0 · spylls 0.1.7 · cryptography 48.0.1 · keyring 25.7.0 |
| Date | 19 November 2026 |
| Result | Pending GitHub's Tests run for this commit |

## This build

Four more general themes, WHFRP, The One Ring, WH40KRP and Rogue Trader, and two style hooks for themes (page-background and stat-row). The design document was read in full in the build chat at revision 443; this build wrote revisions 444 to 446.

## Results

| ID | Result | Notes |
|---|---|---|
| Every test of M1 to 0.7.7 | Pending | GitHub's run |
| T-LOOK-15 | Pass | New, build session: manifests, licences, no "Warhammer", fonts (font guard, static, å ä ö, licence beside), papers, the hooks in all eight themes, offered for both game systems, and `m4-look`, `m5-plain` and the example adventure built twice in each new theme with identical output and no theme warning |
| T-MOD-01, T-LOOK-09, T-LOOK-13, T-LOOK-14 | Pass | Build session, with the four themes added to their lists |
| T-BUILD-03 | Pass here | m1-basic exports to the reference checksum `8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69`, unchanged: the earlier themes print byte-identically with the hooks |
| T-LOOK-07 | Pending | Compare the four themes with the approved mockups (12.11), on screen and on a black-and-white printer |
| T-DOC-06, T-EXT-16, T-REL-02 | Pending | As in 0.7.7 |
| T-USE-01, T-USE-02 | Not run | The scenarios use no theme this build adds or changes |

## Looked at

Pages 2 and 3 of `m5-plain` in each new theme: the bands, the chapter tab on the outer edge of odd and even pages, the page number on the foot band, torn panels, red diamonds and vine corners, the arched frames, the dossier and the charter.

## Found while building

- **WH40KRP's Clearance stamp covered the secret's text.** It now sits on the dossier's top line.
- **WH40KRP's printout paper printed its head and ruling through the handwriting.** The paper has neither now.
- **Rogue Trader's seal touched a quote's description** below a framed quote. It now hangs from the charter's lower right corner, smaller.
- **Libre Caslon Text and Alegreya ship only as variable fonts**, which Typst cannot use: Crimson Text and Cormorant Garamond take their place (design F8).

## Corrections to existing tests

T-LOOK-09 (`tests/test_m4.py`): the themes offered for the test game system and for Vaesen include the four new themes.
