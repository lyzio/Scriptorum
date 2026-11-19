"""0.7.5 (0.7.0 step 6, extension modules, design document F25: the Extensions
tab, suggestions and pictures, How to write an extension).

T-EXT-17   a suggestion replaces a block's text
T-EXT-18   a suggestion adds a block
T-EXT-19   suggestions that are refused
T-EXT-20   pictures: Use, Set as portrait, Regenerate, Cancel
T-EXT-21   the Extensions tab in the left pane
T-EXT-22   How to write an extension, and its worked example
"""

from __future__ import annotations

import json
import struct
import time
import zlib
from pathlib import Path

import pytest

from scriptorum.core.appsettings import AppSettings
from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library, pack_scmod
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.conftest import pack_sample
from tests.test_m6c2 import BUNDLED
from tests.test_step5 import FakeKeychain, install, make_extension, new_api, packed, wait_for

ROOT = Path(__file__).resolve().parents[1]


def png(width=8, height=6) -> bytes:
    raw = b"".join(b"\x00" + b"\x80\x40\x20" * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


HELPER = '''
import base64, json

PNG = base64.b64decode("%s")

def first(ext, kind, chapter=0):
    return next(b for b in ext.blocks(chapter) if b["kind"] == kind)

def setup(ext):
    @ext.command("suggest")
    def suggest(context):
        para = first(ext, "paragraph")
        ids = [ext.suggest_replace(0, para["path"], para["source"].replace("silent since midsummer", "quiet since the summer"),
                                   label="Plainer words")]
        reading = first(ext, "read-aloud")
        ids.append(ext.suggest_replace(0, reading["path"], "#read-aloud[\\nThe wheel stands still.\\n]", label="Shorter"))
        ids.append(ext.suggest_add(0, para["path"], "#read-aloud[\\nThe door is barred.\\n]", label="A read-aloud text"))
        return {"message": json.dumps(ids)}

    @ext.command("bad")
    def bad(context):
        answers = {}
        for name, call in (("path", lambda: ext.suggest_replace(0, [99], "Text.")),
                           ("source", lambda: ext.suggest_replace(0, first(ext, "paragraph")["path"], "#scene(title: \\"x\\"")),
                           ("picture", lambda: ext.picture(b"GIF89a not a png", "x", 0, [0]))):
            try:
                call()
                answers[name] = "shown"
            except Exception as exc:
                answers[name] = str(exc)
        return {"message": json.dumps(answers)}

    @ext.command("picture")
    def picture(context):
        kind = context.get("kind", "paragraph")
        block = first(ext, kind)
        if context.get("regenerate"):
            return {"message": "regenerated"}
        return {"message": ext.picture(PNG, "The mill at dusk", 0, block["path"])}
''' % __import__("base64").b64encode(png()).decode()


def suggester(folder: Path, changes="suggests", ext_id="test.helper", network=()):
    menu = [{"id": "suggest", "label": "Suggest"}, {"id": "bad", "label": "Bad"}, {"id": "picture", "label": "Picture"}]
    return make_extension(folder, ext_id=ext_id, changes=changes, network=network, main=HELPER,
                          extra={"menu": menu, "block_actions": [], "panels": [{"id": "found", "type": "findings", "title": "Found"}]})


def run(api, command, context=None, ext="test.helper"):
    reply = api.extensions.run(ext, command, context or {})
    assert reply["ok"], reply
    return wait_for(api)[-1]


@pytest.fixture
def api(tmp_path):
    a = new_api(tmp_path)
    install(a, suggester(tmp_path / "e"), tmp_path)
    a.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    yield a
    a.extensions.stop_all()


# --- T-EXT-17, T-EXT-18 suggestions ------------------------------------------------------------

@pytest.mark.integration
def test_T_EXT_17_18_suggestions(api):
    """T-EXT-17, 18: a new text for a paragraph and a read-aloud block, and a
    new block after the paragraph; each accepted in one undo step with every
    other byte unchanged; rejected changes nothing; a stale one says so."""
    before = api.adventure.chapter(0)["text"]
    ids = json.loads(run(api, "suggest")["message"])
    open_ = {s["id"]: s for s in api.extensions.suggestions_open()}
    assert list(open_) == ids
    para, reading, adding = (open_[i] for i in ids)
    assert para["kind"] == "replace" and para["label"] == "Plainer words" and para["line"] > 1
    marked = [p["text"] for p in para["pieces"] if p["changed"]]
    assert marked and "quiet" in " ".join(marked) and "midsummer." not in " ".join(marked)
    assert adding["kind"] == "add"
    # Accept the paragraph: only its words change.
    reply = api.extensions.accept_suggestion(para["id"])
    assert reply["ok"] and reply["undoName"] == "Checker: Plainer words"
    after = api.adventure.chapter(0)["text"]
    assert after == before.replace("silent since midsummer", "quiet since the summer")
    assert api.session.world_undo() and api.adventure.chapter(0)["text"] == before
    # Reject the read-aloud: nothing changes.
    assert api.extensions.reject_suggestion(reading["id"])["ok"]
    assert api.adventure.chapter(0)["text"] == before and reading["id"] not in {s["id"] for s in api.extensions.suggestions_open()}
    # Add a block after the paragraph.
    assert api.extensions.accept_suggestion(adding["id"])["ok"]
    text = api.adventure.chapter(0)["text"]
    assert "#read-aloud[\nThe door is barred.\n]" in text and text.replace("\n\n#read-aloud[\nThe door is barred.\n]", "", 1) == before
    assert api.session.world_undo() and api.adventure.chapter(0)["text"] == before
    # A suggestion for a block the author edits first cannot be accepted.
    ids = json.loads(run(api, "suggest")["message"])
    api.adventure.set_chapter_text(0, before.replace("The mill has been silent", "The mill has long been silent"))
    reply = api.extensions.accept_suggestion(ids[0])
    assert reply["ok"] is False and reply["key"] == "error.ext.suggestionStale"


@pytest.mark.integration
def test_T_EXT_19_refused_suggestions(tmp_path):
    """T-EXT-19: none may not suggest; suggests with a network host may; a
    block that does not exist, source that does not parse and a picture
    that is not PNG or JPEG are refused plainly."""
    api = new_api(tmp_path)
    try:
        install(api, suggester(tmp_path / "none", changes="none", ext_id="test.none"), tmp_path)
        install(api, suggester(tmp_path / "net", ext_id="test.net", network=["api.example.com"]), tmp_path)
        api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
        done = run(api, "suggest", ext="test.none")
        assert done["ok"] is False and "did not declare" in done["message"]
        assert api.extensions.suggestions_open() == []
        assert len(json.loads(run(api, "suggest", ext="test.net")["message"])) == 3
        answers = json.loads(run(api, "bad", ext="test.net")["message"])
        assert "in a way Scriptorum does not understand" in answers["path"]
        assert "cannot read as blocks" in answers["source"]
        assert "not a JPEG or PNG" in answers["picture"]
        assert len(api.extensions.suggestions_open()) == 3 and api.extensions.pictures_waiting() == []
    finally:
        api.extensions.stop_all()


# --- T-EXT-20 pictures -----------------------------------------------------------------------

@pytest.mark.integration
def test_T_EXT_20_pictures(api, tmp_path):
    """T-EXT-20: Use inserts an image block with its description after the
    paragraph in one undo step; Set as portrait on a loose card and on a
    codex card; Regenerate asks again; Cancel discards."""
    before = api.adventure.chapter(0)["text"]
    picture_id = run(api, "picture")["message"]
    waiting = api.extensions.pictures_waiting()[0]
    assert waiting["id"] == picture_id and waiting["blockKind"] == "paragraph" and waiting["format"] == "png"
    assert waiting["description"] == "The mill at dusk"
    reply = api.extensions.use_picture(picture_id)
    assert reply["ok"] and reply["undoName"] == "Checker: Use picture"
    text = api.adventure.chapter(0)["text"]
    image = '#image("/assets/images/helper-' + picture_id + '.png", alt: "The mill at dusk")'
    assert image in text and text.replace("\n\n" + image, "", 1) == before
    assert "assets/images/helper-" + picture_id + ".png" in api.session.adventure.files
    assert api.session.world_undo() and api.adventure.chapter(0)["text"] == before
    # The loose person card: Set as portrait.
    picture_id = run(api, "picture", {"kind": "person"})["message"]
    assert api.extensions.pictures_waiting()[0]["blockKind"] == "person"
    assert api.extensions.use_picture(picture_id, True)["portrait"] is True
    text = api.adventure.chapter(0)["text"]
    assert f'portrait: "/assets/images/helper-{picture_id}.png"' in text and 'portrait-description: "The mill at dusk"' in text
    # Regenerate and Cancel.
    picture_id = run(api, "picture")["message"]
    assert api.extensions.regenerate_picture(picture_id)["ok"]
    assert wait_for(api)[-1]["message"] == "regenerated" and api.extensions.pictures_waiting() == []
    picture_id = run(api, "picture")["message"]
    assert api.extensions.cancel_picture(picture_id)["ok"] and api.extensions.pictures_waiting() == []
    assert api.extensions.use_picture(picture_id)["key"] == "error.ext.noPicture"
    # A codex card: the portrait goes on the codex entry.
    api.adventure.open(str(pack_sample("m6-clues", tmp_path)))
    picture_id = run(api, "picture", {"kind": "card"})["message"]
    assert api.extensions.use_picture(picture_id, True)["ok"]
    entry = api.codex.entry("c-ulrika")
    fields = entry.get("fields") or entry.get("entry", {}).get("fields", {})
    assert fields["portrait"].endswith(f"helper-{picture_id}.png") and fields["portrait-description"] == "The mill at dusk"


# --- T-EXT-22 How to write an extension --------------------------------------------------------

def _guide() -> dict:
    return json.loads((BUNDLED / "scriptorum.en" / "strings" / "guide-extension.json").read_text("utf-8"))


def _guide_files() -> dict:
    files = {}
    for value in _guide().values():
        lines = value.splitlines()
        i = 0
        while i < len(lines):
            if lines[i].startswith("```file: "):
                name, body = lines[i][9:].strip(), []
                i += 1
                while not lines[i].startswith("```"):
                    body.append(lines[i])
                    i += 1
                files[name] = "\n".join(body) + "\n"
            i += 1
    return files


@pytest.mark.integration
def test_T_EXT_22_guide_and_worked_example(tmp_path):
    """T-EXT-22: the guide is in the language module, made from its Markdown,
    and covers what F25 says; its worked example, built from the guide's own
    code blocks, installs and does what the guide says."""
    guide = _guide()
    assert guide["title"] == "How to write an extension"
    titles = [v for k, v in guide.items() if k.endswith(".title")]
    for topic in ("What it needs", "The code", "Suggesting changes", "Pictures", "Settings and secrets",
                  "Connecting to the internet", "Worked example: Long read-aloud", "Packing it to share"):
        assert topic in titles, topic
    text = json.dumps(guide)
    assert "can only suggest changes" in text and "{secret:key}" in text and "Block all connections" in text
    files = _guide_files()
    assert set(files) == {"module.json", "extension.py"}
    folder = tmp_path / "long-read-aloud"
    folder.mkdir()
    for name, body in files.items():
        (folder / name).write_text(body, "utf-8")
    api = new_api(tmp_path)
    try:
        file = pack_scmod(folder, tmp_path / "long-read-aloud.scmod")
        info = api.extensions.inspect(str(file))
        assert info["ok"] and info["needs"] == ["Changes nothing in your adventures", "Reads the text of the open adventure"]
        assert api.extensions.install(str(file), agreed=True)["ok"]
        api.extensions.set_on("example.long-read-aloud", True)
        api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
        api.extensions.set_setting("example.long-read-aloud", "words", "60")
        assert api.extensions.run("example.long-read-aloud", "check", {})["ok"]
        done = wait_for(api)[-1]
        assert done["ok"] and done["message"] == "0 read-aloud texts over 60 words."
        assert api.extensions.findings()[0]["title"] == "Long read-aloud texts"
    finally:
        api.extensions.stop_all()


@pytest.mark.unit
def test_T_EXT_22_help_and_website():
    """T-EXT-22: Help has the guide; the website has its page."""
    app_ts = (ROOT / "ui-src" / "app.ts").read_text("utf-8")
    assert 'openGuide("guide-extension")' in app_ts
    menu = json.loads((BUNDLED / "scriptorum.en" / "strings" / "menu.json").read_text("utf-8"))
    assert menu["guideExtension"] == "How to write an extension"
    config = (ROOT / "docs" / "site" / "zensical.toml").read_text("utf-8")
    assert '{ "How to write an extension" = "guides/how-to-write-an-extension.md" }' in config


# --- the window: T-EXT-17, 18, 20, 21, 22 -----------------------------------------------------------

@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-step6")
    library = Library(folder / "library")
    library.install_bundled(BUNDLED)
    app = QApplication.instance() or QApplication([])
    session = Session(library, Strings.from_library(library), RecentFiles(folder / "recent.json"), folder / "build",
                      home=folder / "home", app_settings=AppSettings(folder / "home" / "app-settings.json"))
    window = MainWindow(session, headless_test=True)
    window.bridge.api.extensions.keychain = FakeKeychain()
    window.bridge.confirm_discard = lambda: True
    window.resize(1440, 900)
    window.show()
    driver = Driver(app, window)
    driver.folder = folder
    driver.wait_until(lambda: window.bridge.ui_ready, 60)
    yield driver
    window.bridge.api.extensions.stop_all()
    window.close()


def _tab_count(ui) -> int:
    return int(ui.js("Number(document.body.dataset.extTab || 0)"))


@pytest.mark.ui
def test_T_EXT_21_window(ui):
    """T-EXT-17, 18, 20, 21 in the window: the Extensions tab shows only while
    an extension is on; suggestions sit under their blocks with the changed
    words marked, and Accept is one named undo step; a picture's Use; a
    setting changed in the tab is stored; switched off, the tab goes."""
    api = ui.window.bridge.api
    assert ui.js("document.getElementById('lower-tabs').classList.contains('hidden')")
    install(api, suggester(ui.folder / "e"), ui.folder)
    second = make_extension(ui.folder / "s2", ext_id="test.second", changes="none",
                            settings=[{"id": "level", "kind": "choice", "label": "Level", "options": ["low", "high"]}])
    install(api, second, ui.folder)
    ui.run("window.__scriptorum.extensions.load()")
    assert not ui.js("document.getElementById('lower-tabs').classList.contains('hidden')")
    ui.js("document.getElementById('lt-extensions').click(); true")
    names = ui.js("[...document.querySelectorAll('#ext-tab .ext-section > summary')].map((s) => s.textContent)")
    assert len(names) == 2   # one section per switched-on extension
    assert ui.js("document.getElementById('scene-panel-list').classList.contains('hidden')")
    ui.js("document.getElementById('lt-scene').click(); true")
    assert not ui.js("document.getElementById('scene-panel-list').classList.contains('hidden')")
    ui.window.bridge.openPath(str(pack_sample("m1-basic", ui.folder)))
    ui.run("window.__scriptorum.refresh()")
    ui.run("window.__scriptorum.setMode('visual')")
    # Suggestions under their blocks.
    count = _tab_count(ui)
    ui.run("window.__scriptorum.extensions.run('test.helper', 'suggest', {})")
    ui.wait_until(lambda: ui.js("document.querySelectorAll('#visual .ext-suggestion').length") == 3, 20)
    assert _tab_count(ui) > count
    assert ui.js("document.getElementById('lt-extensions').getAttribute('aria-selected')") == "true"
    first = ui.js("[...document.querySelectorAll('#visual .ext-suggestion')].map((c) => c.previousElementSibling.dataset.line)")
    assert len(first) == 3
    marks = ui.js("[...document.querySelectorAll('#visual .ext-suggestion mark')].map((m) => m.textContent)")
    assert any("quiet" in m for m in marks)
    assert ui.js("[...document.querySelectorAll('#ext-tab .ext-suggestion-list li')].length") == 3
    before = ui.state()["text"]
    ui.js("""[...document.querySelectorAll('#visual .ext-suggestion')].find((c) => c.querySelector('mark') &&
        c.textContent.includes('quiet')).querySelector('.small-btn.primary').click(); true""")
    ui.wait_until(lambda: "quiet since the summer" in ui.state()["text"], 10)
    assert ui.state()["text"] == before.replace("silent since midsummer", "quiet since the summer")
    assert ui.js("window.__scriptorum.extensions.undoLabel()") == "Undo Checker: Plainer words"
    ui.run("window.__scriptorum.undo()")
    ui.wait_until(lambda: ui.state()["text"] == before, 10)
    # A picture: Use.
    ui.run("window.__scriptorum.extensions.run('test.helper', 'picture', {})")
    ui.wait_until(lambda: ui.js("document.querySelectorAll('#ext-tab .ext-picture img').length") == 1, 20)
    assert ui.js("document.querySelector('#ext-tab .ext-picture img').naturalWidth") in (0, 8)
    ui.js("document.querySelector('#ext-tab .ext-picture .small-btn.primary').click(); true")
    ui.wait_until(lambda: 'alt: "The mill at dusk"' in ui.state()["text"], 10)
    # A setting changed in the tab.
    ui.js("""(() => { const s = document.querySelector('#ext-tab [data-extension="test.second"] select[data-setting=level]');
        s.value = 'high'; s.dispatchEvent(new Event('change')); return true; })()""")
    ui.wait_until(lambda: api.extensions.store.state("test.second")["settings"].get("level") == "high", 10)
    # Switched off: the tab goes.
    api.extensions.set_on("test.helper", False)
    api.extensions.set_on("test.second", False)
    ui.run("window.__scriptorum.extensions.load()")
    assert ui.js("document.getElementById('lower-tabs').classList.contains('hidden')")
    assert ui.js("document.querySelectorAll('#visual .ext-suggestion').length") == 0


@pytest.mark.ui
def test_T_EXT_22_guide_in_help(ui):
    """T-EXT-22: Help ▸ How to write an extension opens inside the app with no
    network request."""
    labels = [i["label"] for m in ui.js("window.__scriptorum.menuModel()") if m["key"] == "menu.help" for i in m["items"]]
    assert "How to write an extension" in labels
    ui.js("window.__scriptorum.openGuide('guide-extension'); true")
    ui.wait_until(lambda: ui.js("document.getElementById('guide-dialog').open") is True, 5)
    assert ui.js("document.getElementById('guide-title').textContent") == "How to write an extension"
    assert ui.js("document.getElementById('guide-dialog').dataset.guide") == "guide-extension"
    ui.js("document.getElementById('guide-close').click(); true")
    assert ui.window.bridge.api.net.requests == []
