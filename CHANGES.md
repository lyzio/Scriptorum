# Scriptorum 0.7.6 — Changes

Base: **0.7.5** (0.7.0 step 6, on `build/0.7.0`, commit 70d16ad). A small step on the same branch, decided on 19 November 2026 (design document F24, revision 439): the documentation website's sidebar ends with a link named **Latest release**, after Status, to https://github.com/lyzio/Scriptorum/releases/latest. GitHub forwards that address to the newest release, so the link never changes and the site needs no rebuild when a release is made. It is not a page of its own; the app and its in-app Help are unchanged.

Issues: Refs #34 (the documentation website).

## Added

Nothing.

## Changed

| File | Why |
|---|---|
| `docs/site/zensical.toml` | The Latest release entry, last in the sidebar (F24) |
| `scriptorum/__init__.py`, `pyproject.toml`, `ui-src/package.json` | Version 0.7.6 |
| `tests/test_step4.py` | T-DOC-07 (new); T-DOC-05 also checks the link in the built site |
| `CHANGELOG.md` | The in-progress section is now 0.7.6, with this step |
| `TEST-REPORT.md`, `CHANGES.md` | This step |

## Deleted

Nothing.
