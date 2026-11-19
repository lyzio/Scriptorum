"""0.7.2 (0.7.0 step 3, outcomes approved 18 November 2026).

T-SRC-21    lists parse and write back (issue #5, F4)
T-UI-55     lists in the Visual editor (issue #5)
T-UI-56     footnotes edited in place (issue #4, F7.7)
T-UI-57     pasted labels removed when converting (issue #2, F4)
T-WORLD-36  links between codex entries both ways (issue #17, F3)
"""

from __future__ import annotations

import io
import json

import pytest
from pypdf import PdfReader

from scriptorum.core import source
from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.conftest import pack_sample
from tests.test_m6c2 import BUNDLED, DRAG_HELPERS, FIND


# --- T-SRC-21 -----------------------------------------------------------------------------------

@pytest.fixture
def kinds(session):
    from tests.test_source import GS, TH
    session.new("Kinds", *GS, *TH)
    return session.kinds()


LISTS = (
    "- One\n- *Two* and _three_\n  - Under two\n    - Deeper\n- Back #dice(dice: \"D6\")",
    "+ First\n+ Second\n  + Second, a",
)


@pytest.mark.unit
@pytest.mark.parametrize("text", LISTS)
def test_T_SRC_21_lists_parse_and_write_back(kinds, text):
    """T-SRC-21: bulleted and numbered lists of up to three levels parse as
    list blocks and write back byte-identical."""
    chapter = "A paragraph.\n\n" + text + "\n\nAfter.\n"
    doc = source.parse(chapter, kinds)
    block = doc["blocks"][1]
    assert block["type"] == "list"
    assert block["ordered"] is text.startswith("+")
    assert [i["level"] for i in block["items"]] == ([0, 0, 1, 2, 0] if not block["ordered"] else [0, 0, 1])
    assert source.serialize(doc, kinds) == chapter


@pytest.mark.unit
def test_T_SRC_21_edited_list_is_canonical(kinds):
    doc = source.parse("-   One\n-  Two\n      - Under\n", kinds)
    block = doc["blocks"][0]
    assert block["type"] == "list" and [i["level"] for i in block["items"]] == [0, 0, 1]
    block["items"][1]["text"] = "Two, edited"
    block["ordered"] = True
    source.mark_changed(block)
    assert source.serialize(doc, kinds) == "+ One\n+ Two, edited\n  + Under\n"


@pytest.mark.unit
@pytest.mark.parametrize("text", [
    "- One\n  continued on a second line",
    "- One\n+ Two",
    "1. One\n2. Two",
    "- One\n- #table(columns: 1, [a])",
])
def test_T_SRC_21_other_lists_stay_locked(kinds, text):
    doc = source.parse(text + "\n", kinds)
    assert doc["blocks"][0]["type"] == "locked"
    assert source.serialize(doc, kinds) == text + "\n"


# --- T-WORLD-36 ---------------------------------------------------------------------------------

@pytest.mark.integration
def test_T_WORLD_36_links_both_ways(session, tmp_path):
    """T-WORLD-36: a link stored on one entry shows and prints on both; it is
    stored once; removing it from the other side removes it; the chart draws
    one line."""
    session.open(pack_sample("m6-clues", tmp_path))
    before = dict(session.adventure.files)
    # Opening changes no file: the links show on both sides at once.
    info = session.entry_info("c-broken-oar")
    assert info["linkedFrom"] == []  # a Clue has no Linked to of its own
    assert session.adventure.files == before
    # Ulrika links the Ferryman's man, Anders Lind.
    session.update_entry("c-ulrika", {"fields": {"linked-to": ["c-broken-oar", "c-anders-lind"]}})
    anders = session.entry_info("c-anders-lind")
    assert [x["id"] for x in anders["linkedFrom"]] == ["c-ulrika"]
    assert "linked-to" not in anders["fields"]  # stored only on Ulrika
    data = session.world.build_data("gm", {})
    assert data["entries"]["c-anders-lind"]["fields"]["linked-to"] == ["c-ulrika"]
    assert data["entries"]["c-ulrika"]["fields"]["linked-to"] == ["c-broken-oar", "c-anders-lind"]
    # Both printed cards list the other.
    text = session.adventure.chapter_text(session.adventure.chapters[0])
    session.set_chapter_text(0, text + '\n#card(entry: "c-anders-lind")[\n]\n')
    result = session.build("pdf")
    assert result.ok, [session.localize(p) for p in result.errors]
    pages = [p.extract_text() for p in PdfReader(io.BytesIO(result.output[0])).pages]
    anders_page = next(p for p in pages if "Anders Lind" in p and "Ulrika" in p)
    assert anders_page
    # Stored on both sides: shown once on each; the chart has one line.
    session.update_entry("c-anders-lind", {"fields": {"linked-to": ["c-ulrika"]}})
    assert session.entry_info("c-anders-lind")["linkedFrom"] == []
    assert session.world.build_data("gm", {})["entries"]["c-anders-lind"]["fields"]["linked-to"] == ["c-ulrika"]
    edges = session.world.chart()["edges"]
    assert sum(1 for e in edges if set((e["from"], e["to"]) if isinstance(e, dict) else e) == {"c-ulrika", "c-anders-lind"}) == 1
    # Removing it from Anders's side (the interface writes Ulrika's entry).
    session.update_entry("c-anders-lind", {"fields": {"linked-to": []}})
    session.update_entry("c-ulrika", {"fields": {"linked-to": ["c-broken-oar"]}})
    assert session.entry_info("c-anders-lind")["linkedFrom"] == []


# --- the window ---------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-step3")
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


KEY = """((sel, i, key, shift) => {{ const el = document.querySelectorAll(sel)[i]; el.focus();
    const r = document.createRange(); r.selectNodeContents(el); r.collapse(false);
    getSelection().removeAllRanges(); getSelection().addRange(r);
    el.dispatchEvent(new KeyboardEvent('keydown', {{key, shiftKey: shift, bubbles: true, cancelable: true}})); return true; }})"""


def _key(ui, sel: str, i: int, key: str, shift: bool = False):
    ui.js(KEY.format() + f"({json.dumps(sel)}, {i}, {json.dumps(key)}, {json.dumps(shift)})")
    ui.wait(150)


def _type(ui, sel: str, i: int, text: str):
    ui.js(f"""(() => {{ const el = document.querySelectorAll({json.dumps(sel)})[{i}]; el.focus();
        el.textContent = {json.dumps(text)}; el.dispatchEvent(new Event('input', {{bubbles: true}})); return true; }})()""")


def _text(ui) -> str:
    ui.run("window.__scriptorum.flush()")
    return ui.state()["text"]


@pytest.mark.ui
def test_T_UI_55_lists_in_the_visual_editor(ui):
    """T-UI-55: a list to type in: Enter, Tab, Shift+Tab, Enter on an empty
    item, Backspace, bulleted and numbered, one undo step each."""
    _open(ui, "m5-print", "lists")
    # The sample's list shows as a list, not as a locked block.
    assert ui.js("document.querySelectorAll('#visual section.blk-listing .list-edit').length") >= 1
    assert "Success" in ui.js("document.querySelector('#visual .list-edit').textContent")
    # Insert ▸ List after the first paragraph of the first scene.
    ui.js("document.querySelector('#visual .el-scene .para').focus(); true")
    ui.run("window.__scriptorum.insert('list')")
    ui.wait(300)
    new = f"#visual .list-edit .list-text"
    focused = ui.js("[...document.querySelectorAll('#visual .list-text')].indexOf(document.activeElement)")
    assert focused >= 0
    base = focused
    _type(ui, new, base, "Lantern")
    _key(ui, new, base, "Enter")
    _type(ui, new, base + 1, "Rope")
    _key(ui, new, base + 1, "Tab")
    _key(ui, new, base + 1, "Enter")
    _type(ui, new, base + 2, "Knot")
    text = _text(ui)
    assert "- Lantern\n  - Rope\n  - Knot" in text
    # Tab cannot skip a level: Knot goes one deeper than Rope at most.
    _key(ui, new, base + 2, "Tab")
    _key(ui, new, base + 2, "Tab")
    assert "  - Rope\n    - Knot" in _text(ui)
    _key(ui, new, base + 2, "Tab", shift=True)
    _key(ui, new, base + 2, "Tab", shift=True)
    t = _text(ui)
    assert "- Lantern\n  - Rope\n- Knot" in t, t[t.find("Lantern") - 5:t.find("Lantern") + 60]
    # Backspace on an empty item removes it.
    _key(ui, new, base + 2, "Enter")
    _key(ui, new, base + 3, "Backspace")
    assert "- Knot\n" in _text(ui) and "- \n" not in _text(ui)
    # Enter on an empty item ends the list with a paragraph after it.
    _key(ui, new, base + 2, "Enter")
    _key(ui, new, base + 3, "Enter")
    assert ui.js("document.activeElement.classList.contains('para')")
    # Numbered from the right-click menu, bulleted again from Format.
    ui.js(f"""(() => {{ const el = document.querySelectorAll({json.dumps(new)})[{base}];
        el.dispatchEvent(new MouseEvent('contextmenu', {{bubbles: true, clientX: 300, clientY: 300}})); return true; }})()""")
    ui.wait(150)
    ui.js("[...document.querySelectorAll('#menu-popup .menu-item')].find(i => i.firstChild.textContent === 'Numbered list').click(); true")
    ui.wait(200)
    assert "+ Lantern\n  + Rope\n+ Knot" in _text(ui)
    ui.js(f"document.querySelectorAll({json.dumps(new)})[{base}].focus(); true")
    assert ui.js("window.__scriptorum.focusedKind()") == "list:ordered"
    format_items = ui.js("JSON.stringify(window.__scriptorum.menuModel().find(m => m.key === 'menu.format').items.map(i => [i.label, !!i.disabled]))")
    assert ["Bulleted list", False] in json.loads(format_items)
    ui.js("[...document.querySelectorAll('#menubar .menu-btn')].find(b => b.textContent === 'Format').click(); true")
    ui.wait(150)
    ui.js("[...document.querySelectorAll('#menu-popup .menu-item')].find(i => i.firstChild.textContent === 'Bulleted list').click(); true")
    ui.wait(200)
    assert "- Lantern\n  - Rope\n- Knot" in _text(ui)
    # One undo takes back the switch.
    ui.run("window.__scriptorum.undo()")
    assert "+ Lantern\n  + Rope\n+ Knot" in _text(ui)


FOOTNOTE_CHIP = "#visual .ichip.footnote"


def _click_chip(ui, i: int):
    ui.js(f"document.querySelectorAll({json.dumps(FOOTNOTE_CHIP)})[{i}].click(); true")
    ui.wait(150)
    assert ui.js("!!document.querySelector('.footnote-edit')")


def _edit_box(ui, html: str):
    ui.js(f"""(() => {{ const b = document.querySelector('.footnote-edit .rich'); b.innerHTML = {json.dumps(html)};
        b.dispatchEvent(new Event('input', {{bubbles: true}})); return true; }})()""")


@pytest.mark.ui
def test_T_UI_56_footnotes_edited_in_place(ui, tmp_path):
    """T-UI-56: a click on a footnote chip opens its text; Enter and a click
    outside save, Esc changes nothing; a bold word prints."""
    _open(ui, "m5-print", "footnotes")
    assert ui.js(f"document.querySelectorAll({json.dumps(FOOTNOTE_CHIP)}).length") == 2
    _click_chip(ui, 0)
    assert ui.js("document.querySelector('.footnote-edit .rich').textContent") == "The log was kept from 1871 to 1903."
    _edit_box(ui, "The log was kept <b>badly</b> from 1871.")
    ui.js("document.querySelector('.footnote-edit .rich').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true})); true")
    ui.wait(200)
    assert not ui.js("!!document.querySelector('.footnote-edit')")
    assert '#footnote(text: "The log was kept *badly* from 1871.")' in _text(ui)
    assert "badly" in ui.js(f"document.querySelectorAll({json.dumps(FOOTNOTE_CHIP)})[0].textContent")
    # A click outside saves; Esc does not.
    _click_chip(ui, 1)
    _edit_box(ui, "The bell came from the wreck.")
    ui.js("document.body.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true})); true")
    ui.wait(200)
    assert '#footnote(text: "The bell came from the wreck.")' in _text(ui)
    _click_chip(ui, 1)
    _edit_box(ui, "Something else entirely.")
    ui.js("document.querySelector('.footnote-edit .rich').dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true})); true")
    ui.wait(200)
    assert "Something else" not in _text(ui)
    # One undo step per save.
    ui.run("window.__scriptorum.undo()")
    assert '#footnote(text: "The bell is the one from the wreck.")' in _text(ui)
    # The bold word prints at the foot of the page.
    reply = json.loads(ui.window.bridge.exportTo(str(tmp_path / "notes.pdf")))
    assert reply["ok"], reply
    pdf = PdfReader(str(tmp_path / "notes.pdf"))
    assert any("The log was kept badly from 1871." in p.extract_text() for p in pdf.pages)


PASTED = """Scene 1: The harbour
Location: Skärvik harbour, early morning
Present: Harbour master Lovisa Berg
Fog lies thick over the water.
SECRET: The bell belongs to the Hoppet.
PERSON: Lovisa Berg
Mood: Tired and stubborn
Description: Harbour master for twenty years.
Linked to: The harbour, the Hoppet
* [Publikt] No boat has gone out since Sunday.
Remember: the bell rings at dawn."""


@pytest.mark.ui
def test_T_UI_57_pasted_labels_removed(ui):
    """T-UI-57: converting pasted lines removes their labels and list markers,
    fills the fields named on the lines after them, in one undo step each."""
    _open(ui, "m1-basic", "paste")
    ui.js("document.querySelector('#visual .el-scene .para').focus(); true")
    ui.run("window.__scriptorum.insert('paragraph')")
    ui.wait(200)
    ui.js(f"""(() => {{ const p = document.activeElement; const dt = new DataTransfer(); dt.setData('text/plain', {json.dumps(PASTED)});
        p.dispatchEvent(new ClipboardEvent('paste', {{clipboardData: dt, bubbles: true, cancelable: true}})); return true; }})()""")
    ui.wait(300)
    ui.run("window.__scriptorum.flush()")

    def path_of(start: str) -> list:
        return json.loads(ui.js(f"""JSON.stringify((() => {{ const walk = (blocks, path) => {{
            for (let i = 0; i < blocks.length; i++) {{ const b = blocks[i];
              if (b.type === 'paragraph' && (b.text || '').startsWith({json.dumps(start)})) return [...path, i];
              if (b.body && b.body.blocks) {{ const f = walk(b.body.blocks, [...path, i]); if (f) return f; }} }}
            return null; }}; return walk(window.__scriptorum.state().doc.blocks, []); }})())"""))

    def convert(start: str, kind: str):
        path = path_of(start)
        assert path, start
        ui.js(f"window.__scriptorum.convert({json.dumps(path)}, {json.dumps(kind)}); true")
        ui.wait(250)

    convert("PERSON:", "person")
    text = _text(ui)
    assert '#person(name: "Lovisa Berg", mood: "Tired and stubborn", description: [Harbour master for twenty years.], linked-to: "The harbour, the Hoppet")' in text
    assert "Mood:" not in text and "PERSON:" not in text
    # One undo brings the pasted lines back.
    ui.run("window.__scriptorum.undo()")
    assert "PERSON: Lovisa Berg" in _text(ui) and "Mood: Tired and stubborn" in _text(ui)
    convert("PERSON:", "person")
    convert("SECRET:", "information")
    convert("\\* \\[Publikt\\]", "information")
    text = _text(ui)
    assert '#information(variant: "secret")[The bell belongs to the Hoppet.]' in text
    assert '#information(variant: "public")[No boat has gone out since Sunday.]' in text
    # A label in the middle of a line, and one that names no field, stay.
    assert "Remember: the bell rings at dawn." in text
    convert("Scene 1:", "scene")
    text = _text(ui)
    assert '#scene(title: "The harbour", location: "Skärvik harbour, early morning", present: "Harbour master Lovisa Berg")' in text
    assert "Location:" not in text and "Present:" not in text


@pytest.mark.ui
def test_T_UI_57_codex_names_link_and_swedish_labels(ui):
    """T-UI-57: a field label naming codex entries that exist links them;
    Swedish labels are recognised."""
    _open(ui, "m6-clues", "paste-sv")
    ui.js("document.querySelector('#visual .el-scene .para').focus(); true")
    ui.run("window.__scriptorum.insert('paragraph')")
    ui.wait(200)
    lines = "SLP: Agnes Holm\nHumör: Vaksam\nKopplad till: Ulrika och Anders Lind\nLedtråd: Åran är knäckt."
    ui.js(f"""(() => {{ const p = document.activeElement; const dt = new DataTransfer(); dt.setData('text/plain', {json.dumps(lines)});
        p.dispatchEvent(new ClipboardEvent('paste', {{clipboardData: dt, bubbles: true, cancelable: true}})); return true; }})()""")
    ui.wait(300)
    ui.run("window.__scriptorum.flush()")
    path = json.loads(ui.js("""JSON.stringify((() => { const walk = (blocks, path) => {
        for (let i = 0; i < blocks.length; i++) { const b = blocks[i];
          if (b.type === 'paragraph' && (b.text || '').startsWith('SLP:')) return [...path, i];
          if (b.body && b.body.blocks) { const f = walk(b.body.blocks, [...path, i]); if (f) return f; } }
        return null; }; return walk(window.__scriptorum.state().doc.blocks, []); })())"""))
    ui.js(f"window.__scriptorum.convert({json.dumps(path)}, 'person'); true")
    ui.wait(250)
    text = _text(ui)
    assert '#person(name: "Agnes Holm", mood: "Vaksam", links: ("c-ulrika", "c-anders-lind"))' in text
    path = json.loads(ui.js("""JSON.stringify((() => { const walk = (blocks, path) => {
        for (let i = 0; i < blocks.length; i++) { const b = blocks[i];
          if (b.type === 'paragraph' && (b.text || '').startsWith('Ledtråd:')) return [...path, i];
          if (b.body && b.body.blocks) { const f = walk(b.body.blocks, [...path, i]); if (f) return f; } }
        return null; }; return walk(window.__scriptorum.state().doc.blocks, []); })())"""))
    ui.js(f"window.__scriptorum.convert({json.dumps(path)}, 'information'); true")
    ui.wait(250)
    assert '#information(variant: "hint")[Åran är knäckt.]' in _text(ui)
