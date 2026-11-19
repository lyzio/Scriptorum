"""0.7.0 step 2 (outcomes approved 18 November 2026).

T-LOOK-13   every theme with every game system it styles (issue #23, F8)
T-BUILD-33  the Columns section prints (issue #20, F7.4)
T-UI-53     the Columns section is offered only on a one-column page (issue #20)
T-UI-54     the preview follows the Visual editor (issue #21, F7.2)
"""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from scriptorum.core import source
from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library, game_system_blocks, theme_missing, theme_offered_for
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.conftest import pack_sample
from tests.test_m6c2 import BUNDLED, DRAG_HELPERS, FIND, _lines

# 0.7.8: every bundled theme, the four general themes of F8 included.
THEMES = ("scriptorum.plain", "scriptorum.vaesen", "scriptorum.legends-and-lattes", "scriptorum.call-of-cthulhu",
          "scriptorum.whfrp", "scriptorum.the-one-ring", "scriptorum.wh40krp", "scriptorum.rogue-trader")
PLAIN_GS = "scriptorum.plain-system"
VAESEN_GS = "scriptorum.free-league-vaesen"


def _theme_copy(tmp_path, module_id: str, drop=(), **manifest_changes) -> Path:
    target = tmp_path / "src" / module_id
    shutil.copytree(BUNDLED / "scriptorum.plain", target)
    manifest = json.loads((target / "module.json").read_text("utf-8"))
    manifest.update({"id": module_id, "name": module_id.split(".")[1].title(), "description": "A test theme."})
    manifest.pop("standard", None)
    manifest.update(manifest_changes)
    (target / "module.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    for name in drop:
        (target / "templates" / f"{name}.typ").unlink()
    return target


def _game_system(tmp_path, elements) -> Path:
    folder = tmp_path / "src" / "test.small-game"
    folder.mkdir(parents=True)
    (folder / "module.json").write_text(json.dumps({
        "id": "test.small-game", "kind": "game-system", "name": "Small game", "version": "1.0.0", "format": 1,
        "app": "0.1.0", "licence": "GPL-3.0-or-later", "authors": ["Test"], "description": "A test game system",
        "requires": [{"id": "scriptorum.core", "version": "1.x"}]}), "utf-8")
    (folder / "elements.json").write_text(json.dumps({"on": list(elements)}), "utf-8")
    return folder


# --- T-LOOK-13 every theme with every game system (issue #23) ------------------------------------------

@pytest.mark.integration
def test_T_LOOK_13_bundled_themes_with_both_game_systems(library, session):
    """T-LOOK-13: each bundled theme is offered for both bundled game systems;
    a theme's manifest no longer requires a game system; made_for only puts
    a theme first."""
    systems = {g["id"]: g for g in session.game_systems()}
    for gs in (PLAIN_GS, VAESEN_GS):
        assert {t["id"] for t in systems[gs]["themes"]} == set(THEMES) and systems[gs]["locked"] == []
    assert systems[VAESEN_GS]["themes"][0]["id"] == "scriptorum.vaesen"     # made_for
    assert systems[PLAIN_GS]["themes"][0]["id"] == "scriptorum.plain"       # the standard one
    for theme in THEMES:
        manifest = json.loads((BUNDLED / theme / "module.json").read_text("utf-8"))
        assert manifest["requires"] == [{"id": "scriptorum.core", "version": "1.x"}], theme
    assert json.loads((BUNDLED / "scriptorum.vaesen" / "module.json").read_text("utf-8"))["made_for"] == VAESEN_GS
    blocks = game_system_blocks(library, library.newest(PLAIN_GS))
    assert {"scene", "creature", "box", "codex-card", "end-clues", "end-index", "contents"} <= set(blocks)
    assert not {"page-break", "column-break", "full-width", "keep-together", "column-section", "footnote", "card",
                "mention", "see"} & set(blocks)


@pytest.mark.integration
def test_T_LOOK_13_locked_where_a_block_is_missing(library, session, tmp_path):
    """T-LOOK-13: a theme without the Creature template is locked for game
    systems that use Creature, greyed out with the reason, and offered for
    one that does not; a requirement of a game system is ignored."""
    library.install_folder(_game_system(tmp_path, ["scene", "read-aloud", "box"]))
    no_creature = library.install_folder(_theme_copy(tmp_path, "test.nocreature", drop=("creature",),
                                                     requires=[{"id": "scriptorum.core", "version": "1.x"},
                                                               {"id": VAESEN_GS, "version": "1.x"}]))
    try:
        assert theme_missing(library, no_creature, library.newest(PLAIN_GS)) == ["creature"]
        assert not theme_offered_for(library, no_creature, library.newest(VAESEN_GS))   # its requirement does not help
        assert theme_offered_for(library, no_creature, library.newest("test.small-game"))
        systems = {g["id"]: g for g in session.game_systems()}
        for gs in (PLAIN_GS, VAESEN_GS):
            locked = {t["id"]: t for t in systems[gs]["locked"]}
            assert locked["test.nocreature"]["reason"] == "no styling for: Creature"
            assert "test.nocreature" not in {t["id"] for t in systems[gs]["themes"]}
        assert "test.nocreature" in {t["id"] for t in systems["test.small-game"]["themes"]}
        # The settings page lists it greyed out too.
        session.open(pack_sample("m5-plain", tmp_path))
        info = session.settings_info()
        assert {"id": "test.nocreature", "name": "Nocreature", "reason": "no styling for: Creature"} in info["themesLocked"]
        with pytest.raises(ValueError):
            session.set_theme("test.nocreature")
    finally:
        shutil.rmtree(library.root / "test.nocreature", ignore_errors=True)
        shutil.rmtree(library.root / "test.small-game", ignore_errors=True)


@pytest.mark.integration
def test_T_LOOK_13_locked_later_still_builds(library, session, tmp_path):
    """T-LOOK-13: an adventure whose theme lost a template later still builds;
    the block is drawn in the generic frame with a warning."""
    library.install_folder(_theme_copy(tmp_path, "test.later"))
    try:
        session.open(pack_sample("m5-plain", tmp_path))
        session.set_theme("test.later")
        (library.root / "test.later" / "1.0.0" / "templates" / "creature.typ").unlink()
        result = session.build("pdf")
        assert result.ok
        assert any(w.key == "warning.build.genericFrame" and w.details["element"] == "creature" for w in result.warnings)
        assert session.settings_info()["themesLocked"][0]["id"] == "test.later"
    finally:
        shutil.rmtree(library.root / "test.later", ignore_errors=True)


# --- T-BUILD-33 the Columns section (issue #20) ----------------------------------------------------

WORDS = " ".join(["lorem ipsum dolor sit"] * 30)


def _section(count: int) -> str:
    return (f"Before the section.\n\n#column-section(count: {count})[\nFirstcol {WORDS}\n\n#column-break()\n\n"
            "Secondcol here.\n]\n\nAfterwards one column.\n")


@pytest.mark.integration
@pytest.mark.parametrize("theme", THEMES)
def test_T_BUILD_33_columns_section(session, tmp_path, theme):
    """T-BUILD-33: on a one-column page a Columns section sets its blocks in
    2 or 3 columns where it is written; the column break moves to its next
    column; the text after it is in one column again; it parses and writes
    back byte-identical; on a two-column page it still prints."""
    session.open(pack_sample("m5-plain", tmp_path))
    session.set_theme(theme)
    session.set_settings({"page": {"columns": 1}})
    original = session.adventure.chapter_text(session.adventure.chapters[0])
    for count in (2, 3):
        text = _section(count) + "\n" + original
        doc = source.parse(text, session.kinds())
        section = next(b for b in doc["blocks"] if b.get("kind") == "column-section")
        assert section["fields"]["count"] == count
        assert source.serialize(doc, session.kinds()) == text
        session.set_chapter_text(0, text)
        result = session.build("pdf")
        assert result.ok, [session.localize(p) for p in result.errors]
        page = next(p for p in PdfReader(io.BytesIO(result.output[0])).pages if "Firstcol" in p.extract_text())
        runs = _lines(page)
        x = {name: next(r[1] for r in runs if r[0].startswith(name)) for name in ("Before", "Firstcol", "Secondcol", "Afterwards")}
        y = {name: next(r[2] for r in runs if r[0].startswith(name)) for name in ("Before", "Firstcol", "Afterwards")}
        width = float(page.mediabox.width)
        assert abs(x["Firstcol"] - x["Before"]) < 2 and abs(x["Afterwards"] - x["Before"]) < 2
        # The second column starts at a half (2) or a third (3) of the text width.
        share = (x["Secondcol"] - x["Before"]) / (width - 2 * x["Before"])
        assert abs(share - (0.5 if count == 2 else 1 / 3)) < 0.06, share
        # Where it is written: after "Before", and "Afterwards" comes below the section.
        assert y["Before"] > y["Firstcol"] > y["Afterwards"]
    # On a page with two columns it still prints.
    session.set_settings({"page": {"columns": 2}})
    assert session.build("pdf").ok
    session.set_chapter_text(0, original)


# --- the window -------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-step2")
    library = Library(folder / "library")
    library.install_bundled(BUNDLED)
    app = QApplication.instance() or QApplication([])
    session = Session(library, Strings.from_library(library), RecentFiles(folder / "recent.json"), folder / "build",
                      home=folder / "home")
    window = MainWindow(session, headless_test=True)
    window.bridge.confirm_discard = lambda: True
    window.resize(1440, 900)
    window.show()
    driver = Driver(app, window)
    driver.folder = folder
    driver.wait_until(lambda: window.bridge.ui_ready, 60)
    yield driver
    window.close()


def _open(ui, sample: str, sub: str):
    (ui.folder / sub).mkdir(exist_ok=True)
    assert json.loads(ui.window.bridge.openPath(str(pack_sample(sample, ui.folder / sub))))["ok"]
    ui.run("window.__scriptorum.refresh()")
    ui.run("window.__scriptorum.setMode('visual')")
    ui.js(DRAG_HELPERS)
    ui.js(FIND)


def _menu_items(ui) -> list:
    return ui.js("[...document.querySelectorAll('#menu-popup .menu-item, #menu-popup .menu-heading')].map(i => i.firstChild.textContent)")


def _close_menu(ui):
    ui.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); true")


@pytest.mark.ui
def test_T_UI_53_columns_section_offered_on_one_column(ui):
    """T-UI-53: the Columns section is offered only on a one-column page,
    under Layout in the Insert menu and the + menu; it is inserted with 2
    columns; the field offers 2 and 3; each change is one undo step."""
    _open(ui, "m5-plain", "cols")
    bridge = ui.window.bridge
    for columns, offered in ((2, False), (1, True)):
        bridge.setSettings(json.dumps({"page": {"columns": columns}}))
        ui.run("window.__scriptorum.refresh()")
        ui.js("[...document.querySelectorAll('#menubar .menu-btn')].find(b => b.textContent === 'Insert').click(); true")
        ui.wait(150)
        assert not ui.js("document.getElementById('menu-popup').classList.contains('hidden')")
        items = _menu_items(ui)
        _close_menu(ui)
        assert ("Columns section" in items) is offered, items
        if offered:
            assert items.index("Columns section") > items.index("Layout")
        ui.js("(() => { const b = document.querySelector('#visual section.blk'); b.scrollIntoView({block: 'center'});"
              " b.querySelector(':scope > .blk-controls').querySelectorAll('button')[2].click(); return true; })()")
        ui.wait(150)
        columns_menu = ui.js("[...document.querySelectorAll('#menu-popup .menu-column')].map(c => [...c.querySelectorAll('.menu-heading, .menu-item')].map(i => i.firstChild.textContent))")
        layout = next((c for c in columns_menu if c[0] == "Layout"), [])
        assert ("Columns section" in layout) is offered
        if offered:
            before = ui.state()["text"]
            ui.js("[...document.querySelectorAll('#menu-popup .menu-item')].find(i => i.firstChild.textContent === 'Columns section').click(); true")
            ui.wait(200)
            ui.run("window.__scriptorum.flush()")
            text = ui.state()["text"]
            assert "#column-section(count: 2)[" in text
            ui.js("(() => { const i = [...document.querySelectorAll('#visual .el-column-section input')][0];"
                  " i.value = '3'; i.dispatchEvent(new Event('input', {bubbles: true})); i.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
            ui.wait(200)
            ui.run("window.__scriptorum.flush()")
            assert "#column-section(count: 3)[" in ui.state()["text"]
            ui.run("window.__scriptorum.undo()")
            ui.run("window.__scriptorum.undo()")
            assert ui.state()["text"] == before
        else:
            _close_menu(ui)


@pytest.mark.ui
def test_T_UI_54_preview_follows_the_editor(ui):
    """T-UI-54: the preview scrolls to the block with the cursor, with a
    short mark; not within two seconds of scrolling it by hand; never with
    Follow off; Follow is on by default and remembered; a click in the
    preview moves the editor to its block."""
    _open(ui, "example-jattens-skuld", "follow")
    settings = ui.window.bridge.session.app_settings
    assert settings.get("preview_follow") is True
    assert ui.js("document.getElementById('zoom-follow').getAttribute('aria-pressed')") == "true"
    ui.wait_until(lambda: ui.state()["pages"] > 4 and len(ui.state()["elements"]) > 10, 60)
    ui.wait(600)
    pane = "document.getElementById('preview-pane')"
    elements = ui.state()["elements"]
    late = elements[-3]
    early = elements[1]
    ui.js("document.getElementById('editor-pane').scrollTop = 0; true")
    ui.js(f"{pane}.scrollTop = 0; true")
    ui.wait(2100)   # longer than the pause after a scroll by hand
    ui.run(f"window.__scriptorum.focusBlock({json.dumps(late['path'])})")
    ui.wait(300)
    top = ui.js(f"{pane}.scrollTop")
    assert top > 500
    assert ui.js("document.querySelectorAll('#preview-pane .follow-mark').length") == 1
    # Scrolling the preview by hand pauses following.
    ui.js(f"{pane}.dispatchEvent(new WheelEvent('wheel', {{deltaY: 100, bubbles: true}})); true")
    ui.run(f"window.__scriptorum.focusBlock({json.dumps(early['path'])})")
    ui.wait(300)
    assert ui.js(f"{pane}.scrollTop") == top
    # After the pause it follows again.
    ui.wait(2100)
    ui.run(f"window.__scriptorum.focusBlock({json.dumps(late['path'])})")
    ui.run(f"window.__scriptorum.focusBlock({json.dumps(early['path'])})")
    ui.wait(300)
    assert ui.js(f"{pane}.scrollTop") < top
    # Follow off: never scrolls; remembered.
    ui.js("document.getElementById('zoom-follow').click(); true")
    ui.wait_until(lambda: settings.get("preview_follow") is False, 5)
    assert ui.js("document.getElementById('zoom-follow').getAttribute('aria-pressed')") == "false"
    here = ui.js(f"{pane}.scrollTop")
    ui.run(f"window.__scriptorum.focusBlock({json.dumps(late['path'])})")
    ui.wait(300)
    assert ui.js(f"{pane}.scrollTop") == here
    ui.js("document.getElementById('zoom-follow').click(); true")
    ui.wait_until(lambda: settings.get("preview_follow") is True, 5)
    # A click in the preview moves the editor to the element's block.
    spot = elements[len(elements) // 2]
    ui.js(f"""(() => {{ const img = document.querySelectorAll('#pages img.page')[{spot['page'] - 1}];
        img.scrollIntoView({{block: 'start'}});
        const r = img.getBoundingClientRect();
        const x = r.left + ({spot['x']} + 6) / (img.naturalWidth * 0.75) * r.width;
        const y = r.top + ({spot['y']} + 4) / (img.naturalHeight * 0.75) * r.height;
        img.dispatchEvent(new MouseEvent('click', {{clientX: x, clientY: y, bubbles: true}})); return true; }})()""")
    ui.wait(500)
    # The block of that element is in view in the editor.
    shown = ui.js(f"""(() => {{ const b = window.__scriptorum.blockAt({json.dumps(spot['path'])});
        const sections = [...document.querySelectorAll('#visual section.blk')];
        const pane = document.getElementById('editor-pane').getBoundingClientRect();
        return sections.some(s => {{ const r = s.getBoundingClientRect(); return r.bottom > pane.top && r.top < pane.bottom; }}); }})()""")
    assert shown
    ui.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); true")
