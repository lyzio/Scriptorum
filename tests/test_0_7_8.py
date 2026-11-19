"""0.7.8: the four general themes WHFRP, The One Ring, WH40KRP and Rogue
Trader, and the two style hooks page-background and stat-row (F8, decided
19 November 2026; approved mockups in design document 12.11). Test Plan
T-LOOK-15.
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path

import pytest
from pypdf import PdfReader

from scriptorum.core.fonts import check_font, read_names
from scriptorum.core.preflight import font_chars

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "scriptorum" / "bundled"
NEW = ("scriptorum.whfrp", "scriptorum.the-one-ring", "scriptorum.wh40krp", "scriptorum.rogue-trader")
EARLIER = ("scriptorum.vaesen", "scriptorum.plain", "scriptorum.legends-and-lattes", "scriptorum.call-of-cthulhu")
NAMES = {"scriptorum.whfrp": "WHFRP", "scriptorum.the-one-ring": "The One Ring",
         "scriptorum.wh40krp": "WH40KRP", "scriptorum.rogue-trader": "Rogue Trader"}
FAMILIES = {
    "scriptorum.whfrp": {"Libre Caslon Display", "Crimson Text"},
    "scriptorum.the-one-ring": {"Uncial Antiqua", "EB Garamond", "Josefin Sans"},
    "scriptorum.wh40krp": {"Grenze Gotisch", "Spectral", "Share Tech Mono"},
    "scriptorum.rogue-trader": {"Cinzel Decorative", "Cinzel", "Cormorant Garamond"},
}


@pytest.mark.parametrize("theme", NEW)
def test_T_LOOK_15_manifest_licence_and_names(theme):
    """T-LOOK-15: a general theme requiring only the core element kit, named
    after its game, with the unofficial notice in its description and licence
    file; the word Warhammer is never used (F8)."""
    folder = BUNDLED / theme
    manifest = json.loads((folder / "module.json").read_text("utf-8"))
    assert manifest["id"] == theme and manifest["kind"] == "theme" and manifest["name"] == NAMES[theme]
    assert manifest["requires"] == [{"id": "scriptorum.core", "version": "1.x"}]
    assert "unofficial" in manifest["description"] and "not affiliated" in manifest["description"]
    licence = (folder / "LICENSE.txt").read_text("utf-8")
    assert "unofficial" in licence and "not affiliated" in licence
    for file in folder.rglob("*"):
        if file.is_file() and file.suffix in (".json", ".typ", ".svg", ".txt") and "vendor" not in file.parts:
            assert "warhammer" not in file.read_text("utf-8", errors="ignore").lower(), file


@pytest.mark.parametrize("theme", NEW)
def test_T_LOOK_15_fonts_open_static_with_licence(theme):
    """T-LOOK-15: every font passes the font guard (F11), is a static weight
    (no variable-font table), has å, ä and ö, and has its licence file."""
    # The app's own readers, as GitHub's test machine has no fontTools.
    fonts = BUNDLED / theme / "fonts"
    families = set()
    for file in sorted(fonts.iterdir()):
        if file.suffix.lower() not in (".ttf", ".otf"):
            continue
        data = file.read_bytes()
        result = check_font(data)
        assert result.ok, file.name
        count = struct.unpack(">H", data[4:6])[0]
        tables = {data[12 + 16 * i:16 + 16 * i] for i in range(count)}
        assert b"fvar" not in tables, f"{file.name} is a variable font"
        chars = font_chars(data)
        assert all(ord(c) in chars for c in "åäöÅÄÖ"), file.name
        names = read_names(data)
        families.add(names.get(16) or names.get(1))
        stem = file.name.split("-")[0]
        assert (fonts / f"{stem}-OFL.txt").is_file(), f"no licence file beside {file.name}"
    assert families == FAMILIES[theme]


@pytest.mark.parametrize("theme", NEW)
def test_T_LOOK_15_papers_print_friendly(theme):
    """T-LOOK-15: two handout papers, named in labels/en.json; never filled,
    marks pale (F6.5)."""
    folder = BUNDLED / theme
    papers = json.loads((folder / "handouts.json").read_text("utf-8"))["papers"]
    labels = json.loads((folder / "labels" / "en.json").read_text("utf-8"))
    assert len(papers) == 2
    for p in papers:
        assert "fill" not in p and p["label"] in labels
        assert p["marks"].get("opacity", 0.12) <= 0.2


def test_T_LOOK_15_style_hooks():
    """T-LOOK-15: the earlier themes keep the default hooks (no page
    background, the stats in one row), so they print as before; the new themes
    draw their own."""
    for theme in EARLIER:
        style = (BUNDLED / theme / "templates" / "_style.typ").read_text("utf-8")
        assert style.count("#let page-background") == 1 and "#let page-background = none" in style
        assert style.count("#let stat-row") == 1
    for theme in NEW:
        style = (BUNDLED / theme / "templates" / "_style.typ").read_text("utf-8")
        assert style.count("#let stat-row") == 2  # the default, then the theme's own
        assert style.count("#let page-background") == (1 if theme == "scriptorum.rogue-trader" else 2)
    for theme in EARLIER + NEW:
        page = (BUNDLED / theme / "templates" / "_page.typ").read_text("utf-8")
        assert "background: if page-background != none" in page
        assert "stat-row(f.stats)" in (BUNDLED / theme / "templates" / "creature.typ").read_text("utf-8")


def test_T_LOOK_15_offered_for_both_game_systems(session):
    """T-LOOK-15: each new theme styles every block, so it is offered for both
    bundled game systems and is never locked (F8, 9.6)."""
    systems = {g["id"]: g for g in session.game_systems()}
    for gs in ("scriptorum.free-league-vaesen", "scriptorum.plain-system"):
        offered = {t["id"] for t in systems[gs]["themes"]}
        assert set(NEW) <= offered
        assert not set(NEW) & {t if isinstance(t, str) else t.get("id") for t in systems[gs].get("locked", [])}


@pytest.mark.integration
@pytest.mark.parametrize("theme", NEW)
def test_T_LOOK_15_samples_build(session, sample, theme, record_property):
    """T-LOOK-15: m4-look, m5-plain and the example adventure build in each
    new theme without errors or warnings about the theme (no element in the
    generic frame, no paper breaking the handout rules); two builds are
    identical; the page count is reported."""
    counts = {}
    for name in ("m4-look", "m5-plain", "example-jattens-skuld"):
        session.open(sample(name))
        if session.adventure.theme.id != theme:
            session.set_theme(theme)
        first = session.build("pdf")
        assert first.ok, [session.localize(e) for e in first.errors]
        themed = [w for w in first.warnings if any(k in json.dumps(w, default=str) for k in ("generic", "paper"))]
        assert themed == [], themed
        again = session.build("pdf")
        assert again.output[0] == first.output[0]
        counts[name] = len(PdfReader(io.BytesIO(first.output[0])).pages)
    record_property("pages", json.dumps(counts))
    print(theme, counts)
