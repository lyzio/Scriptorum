"""M6 fix build 0.6.10 (decided 18 November 2026).

T-WORLD-35  where the map key goes (issue #22, F5)
T-UI-49     the window's zoom (issue #16, F9)
T-UI-50     the + menu of a block in groups (issue #18, F9)
T-UI-51     the logo (F9, D16, section 7)
T-UI-52     New entry ▸ Creature in Vaesen, not offered in Plain (issue #1)
T-REL-13    the update file's name (issue #26, F21)
T-REL-14    the release files (issue #25, F10)
T-REL-15    the repository's workflows (D12)
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import struct
import subprocess
import zlib
from pathlib import Path

import pytest
from pypdf import PdfReader

from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.conftest import pack_sample
from tests.test_m6c2 import BUNDLED, DRAG_HELPERS, FIND

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
THEMES = ("scriptorum.vaesen", "scriptorum.plain", "scriptorum.legends-and-lattes", "scriptorum.call-of-cthulhu")
OLD_NAME = "scriptor" + "ium-update.json"   # the misspelt name of issue #26, never written out in full


def _tool(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- T-REL-13 the update file's name (issue #26) -----------------------------------------------

@pytest.mark.unit
def test_T_REL_13_update_file_name():
    """T-REL-13: UPDATE_URL asks for the file the release script writes and
    the release publishes; nothing in the app or its tests names the older
    spelling."""
    from scriptorum.core import updates
    release = (ROOT / "tools" / "release.py").read_text("utf-8")
    written = set(re.findall(r'out / "([a-z-]+\.json)"', release))
    assert written == {"scriptorum-update.json"}
    assert updates.UPDATE_URL.rsplit("/", 1)[1] == "scriptorum-update.json"
    assert updates.UPDATE_URL == "https://github.com/lyzio/Scriptorum/releases/latest/download/scriptorum-update.json"
    for folder in ("scriptorum", "tests", "tools", "ui-src", "packaging", ".github"):
        for file in (ROOT / folder).rglob("*"):
            if "node_modules" in file.parts or not file.is_file() or file.suffix in (".png", ".ttf", ".otf", ".pyc", ".dic", ".aff", ".zip"):
                continue
            assert OLD_NAME not in file.read_text("utf-8", errors="replace"), file


# --- T-REL-14 the release files (issue #25) ----------------------------------------------------

@pytest.mark.integration
def test_T_REL_14_kit_writes_only_the_installer():
    """T-REL-14: the kit writes only the installer: no INSTALL-*.txt, no
    SHA256SUMS-<platform>.txt and no source zip (kit 1.0.4)."""
    build = (ROOT / "packaging" / "build.py").read_text("utf-8")
    finish = "\n".join(line for line in build[build.index('say("6/7 package")'):].splitlines()
                       if not line.strip().startswith("#"))
    assert "def source_archive" not in build and "source.zip" not in build
    assert "SHA256SUMS" not in finish and "user-docs" not in finish
    assert "zipfile" not in build
    assert json.loads((ROOT / "packaging" / "kit.json").read_text("utf-8"))["kit_version"] == "1.0.4"
    # The notes stay inside the installers.
    assert "INSTALL-macOS.txt" in build and "INSTALL-Windows.txt" in build
    for notes in (ROOT / "packaging" / "user-docs").glob("INSTALL-*.txt"):
        text = notes.read_text("utf-8")
        assert "source.zip" not in text and "https://github.com/lyzio/Scriptorum" in text, notes.name


@pytest.mark.integration
def test_T_REL_14_one_checksum_file(tmp_path):
    """T-REL-14: the attach job uploads the installers and one SHA256SUMS.txt
    with a line for every installer, keeping the lines of installers that an
    earlier run attached."""
    text = (WORKFLOWS / "installers.yml").read_text("utf-8")
    assert '--pattern SHA256SUMS.txt' in text and "out/SHA256SUMS.txt" in text
    assert 'gh release upload "$TAG" out/* --clobber' in text
    block = text[text.index("mkdir -p sums"):text.index('echo "Attaching:')]
    lines = [line.strip() for line in block.splitlines() if line.strip() and "gh release download" not in line]
    script = "\n".join(["set -euo pipefail"] + lines)
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "Scriptorum-9.9.9-linux-x86_64.AppImage").write_bytes(b"linux, built again")
    (tmp_path / "out" / "Scriptorum-9.9.9-windows-x64-setup.exe").write_bytes(b"windows")
    (tmp_path / "sums").mkdir()
    (tmp_path / "sums" / "SHA256SUMS.txt").write_text(
        "1111  Scriptorum-9.9.9-macos-arm64.dmg\n2222  Scriptorum-9.9.9-linux-x86_64.AppImage\n")
    subprocess.run(["bash", "-c", script], cwd=tmp_path, check=True)
    sums = (tmp_path / "out" / "SHA256SUMS.txt").read_text().splitlines()
    names = [line.split("  ", 1)[1] for line in sums]
    assert names == sorted(names) == ["Scriptorum-9.9.9-linux-x86_64.AppImage", "Scriptorum-9.9.9-macos-arm64.dmg",
                                      "Scriptorum-9.9.9-windows-x64-setup.exe"]
    import hashlib
    assert sums[0].split("  ")[0] == hashlib.sha256(b"linux, built again").hexdigest()   # replaced, not kept
    assert sums[1] == "1111  Scriptorum-9.9.9-macos-arm64.dmg"                          # kept from the release


@pytest.mark.unit
def test_T_REL_14_release_description_with_linux_notes(tmp_path):
    """T-REL-14: the release description is the version's section of
    CHANGELOG.md followed by the Linux install notes; the release job still
    publishes the update pack and scriptorum-update.json under their names."""
    tool = _tool("release_tool_f", ROOT / "tools" / "release.py")
    version = __import__("scriptorum").__version__
    text = tool.release_description(version)
    section = tool.changelog_section(version)
    assert text.startswith(section) and "\n\n## Installing on Linux\n\n```text\n" in text
    assert f"Scriptorum-{version}-linux-x86_64.AppImage" in text and "<version>" not in text
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 9.9.9 — test\n\n- One line.\n")
    notes = tmp_path / "notes.txt"
    notes.write_text("Run Scriptorum-<version>-linux-x86_64.AppImage\n")
    assert tool.release_description("9.9.9", changelog, notes) == (
        "- One line.\n\n## Installing on Linux\n\n```text\nRun Scriptorum-9.9.9-linux-x86_64.AppImage\n```")
    assert tool.release_description("9.9.9", changelog, tmp_path / "missing.txt") == "- One line."
    release = (ROOT / "tools" / "release.py").read_text("utf-8")
    assert "description = release_description(args.version)" in release
    assert 'out / "scriptorum-update.json"' in release and '-update.zip' in release


# --- T-REL-15 the repository's workflows --------------------------------------------------------

# The first major version of each action that runs on Node 24.
NODE24 = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6,
          "actions/download-artifact": 7, "actions/setup-node": 5, "github/codeql-action/init": 4,
          "github/codeql-action/analyze": 4}


@pytest.mark.unit
def test_T_REL_15_actions_pinned_and_current():
    """T-REL-15: every action is at its Node 24 version and pinned to a full
    commit SHA with the version in a comment."""
    seen = set()
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for line in workflow.read_text("utf-8").splitlines():
            if line.strip().startswith("#") or "uses:" not in line:
                continue
            match = re.search(r"uses: ([\w./-]+)@([0-9a-f]{40})  # v(\d+)\.\d+\.\d+$", line)
            assert match, f"{workflow.name}: {line.strip()}"
            name, _, major = match.groups()
            assert int(major) >= NODE24[name], f"{workflow.name}: {name} v{major}"
            seen.add(name)
    assert {"actions/checkout", "actions/setup-python", "actions/upload-artifact", "actions/download-artifact"} <= seen
    assert not (WORKFLOWS / "devskim.yml").exists()


@pytest.mark.unit
def test_T_REL_15_audit_and_tests_workflows():
    """T-REL-15: a dependency audit (pip-audit on the pinned Python packages,
    npm audit on the interface) weekly and on every pull request, and the
    tests on every pull request and push to a build branch, both read-only."""
    audit = (WORKFLOWS / "audit.yml").read_text("utf-8")
    assert "pull_request:" in audit and "schedule:" in audit and "cron:" in audit
    assert "pip_audit --requirement pinned-requirements.txt --strict" in audit and "['project']['dependencies']" in audit
    assert 'pip-audit==' in audit and "npm audit --audit-level=moderate" in audit and "working-directory: ui-src" in audit
    tests = (WORKFLOWS / "tests.yml").read_text("utf-8")
    assert "pull_request:" in tests and 'branches: ["build/**"]' in tests
    assert "python -m pytest" in tests and 'python-version: "3.13"' in tests and "QT_QPA_PLATFORM: offscreen" in tests
    for text in (audit, tests):
        top = text.split("\njobs:", 1)[0]
        assert "permissions:\n  contents: read" in top and "write" not in text and "secrets." not in text
        assert "persist-credentials: false" in text


# --- T-WORLD-35 where the map key goes (issue #22) ---------------------------------------------

def _png(w: int, h: int) -> bytes:
    raw = b"".join(b"\x00" + b"\xff" * (w * 3) for _ in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _key_columns(session, map_id: str, chapter: str, settings=None) -> tuple:
    """Build the chapter; give the x of the text's left edge, where the map
    starts, and the distinct x positions of the five key lines."""
    from tests.test_m6c2 import _lines
    if settings is not None:
        session.set_settings({"page": settings})
    session.set_chapter_text(0, chapter)
    result = session.build("pdf")
    assert result.ok, result.problems
    reader = PdfReader(io.BytesIO(result.output[0]))
    page = next(p for p in reader.pages if "Keyplace1" in p.extract_text())
    runs = _lines(page)
    keys = [(x, y) for t, x, y in runs if re.search(r"Keyplace\d", t)]
    # The map starts at the left edge of the text (the first column).
    left = min(x for t, x, y in runs if t.strip())
    return left, sorted({round(x) for x, _ in keys}), float(page.mediabox.width)


@pytest.mark.integration
@pytest.mark.parametrize("theme", THEMES)
def test_T_WORLD_35_key_beside_only_where_wide(session, tmp_path, theme):
    """T-WORLD-35: the key sits beside an upright map only where the space is
    at least 12 cm wide (a full-width section, a landscape page) and under it
    in a column of a portrait page; under the map it is in two columns only
    where the space is that wide; a landscape map always has its key under it."""
    session.open(pack_sample("m3-world", tmp_path))
    if theme != "scriptorum.vaesen":
        session.set_theme(theme)
    pins = [{"type": "pin", "x": 0.1 + 0.15 * i, "y": 0.3, "text": f"Keyplace{i + 1}"} for i in range(5)]
    tall = session.create_map("Tallmap", "tall.png", _png(1400, 2000))["id"]
    wide = session.create_map("Widemap", "wide.png", _png(2200, 1400))["id"]
    for made in (tall, wide):
        session.update_map({"id": made, "layers": [{"name": "L", "show_in_handout": True, "items": pins}]})
    original = session.adventure.chapter_text(session.adventure.chapters[0])

    def place(map_id, wrap_full_width, settings=None):
        body = f'#map(map: "{map_id}")'
        if wrap_full_width:
            body = f"#full-width[\n{body}\n]"
        return _key_columns(session, map_id, f"{body}\n\n" + original, settings)

    # A column of a two-column portrait A4 page (about 8 cm): under, one column.
    left, xs, width = place(tall, False, {"columns": 2, "orientation": "portrait"})
    assert len(xs) == 1 and abs(xs[0] - left) < 40
    # A full-width section of that page (17 cm): beside the upright map.
    left, xs, width = place(tall, True)
    assert len(xs) == 1 and xs[0] - left > width * 0.4
    # A landscape map in the full-width section: under it, in two columns.
    left, xs, width = place(wide, True)
    assert len(xs) == 2 and abs(xs[0] - left) < 40
    # The same landscape map in a column: under, one column.
    left, xs, width = place(wide, False)
    assert len(xs) == 1
    # A landscape page with one column: beside the upright map.
    left, xs, width = place(tall, False, {"columns": 1, "orientation": "landscape"})
    assert len(xs) == 1 and xs[0] - left > width * 0.4
    session.set_chapter_text(0, original)


@pytest.mark.unit
def test_T_WORLD_35_key_left_aligned():
    """T-WORLD-35: in every theme the key's text is left-aligned, never
    justified, and the rule for beside or under is the width of the space."""
    for theme in THEMES:
        template = (BUNDLED / theme / "templates" / "map.typ").read_text("utf-8")
        key = template[template.index("let key-grid(lines)"):template.index("let draw-map")]
        assert "set par(justify: false)" in key and "set align(left)" in key, theme
        assert "let wide = size.width >= 12cm" in template, theme
        assert "f.aspect >= 0.9 and wide" in template and "if key-lines.len() > 4 and wide {" in template, theme


# --- the window ----------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-m6f")
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


def _new(ui, text_: str, system=("scriptorum.free-league-vaesen", "scriptorum.vaesen")):
    reply = json.loads(ui.window.bridge.newAdventure(json.dumps({
        "title": "Fix", "gameSystem": {"id": system[0], "version": "1.0.0"},
        "theme": {"id": system[1], "version": "1.0.0"}})))
    assert reply["ok"]
    ui.window.bridge.session.set_chapter_text(0, text_)
    ui.run("window.__scriptorum.refresh()")
    ui.run("window.__scriptorum.setMode('visual')")
    ui.js(DRAG_HELPERS)
    ui.js(FIND)


def _text(ui) -> str:
    ui.run("window.__scriptorum.flush()")
    return ui.state()["text"]


# --- T-UI-51 the logo (runs first: the welcome screen shows with no adventure open) -------------

@pytest.mark.ui
def test_T_UI_51_logo(ui):
    """T-UI-51: the logo shows on the welcome screen (in place of the pen nib
    and the name), in the About window and in the start-up window, as a card
    with rounded corners and the description "Scriptorum logo"; About still
    shows the name and version; Under the hood lists it with CC BY-SA 4.0 and
    its full text, which the Licences tab also holds; the README starts with
    it; the file icons are unchanged; no exported PDF holds it."""
    logo = "document.querySelector('#welcome .welcome-logo')"
    assert ui.js("!document.getElementById('welcome').classList.contains('hidden')")
    ui.wait_until(lambda: ui.js(f"{logo}.complete && {logo}.naturalWidth") == 512, 10)
    assert ui.js(f"{logo}.alt") == "Scriptorum logo"
    assert ui.js(f"parseFloat(getComputedStyle({logo}).borderTopLeftRadius)") >= 8
    assert ui.js("document.querySelector('#welcome .nib')") is None
    assert ui.js("document.querySelector('#welcome h1').textContent") == "Scriptorum"
    assert ui.js("document.querySelector('#welcome h1').getBoundingClientRect().width") <= 1
    # The About window, in light and dark mode.
    for mode in ("light", "dark"):
        ui.window.bridge.session.app_settings.update({"mode": mode})
        ui.run("window.__scriptorum.about.openAbout()")
        about = "document.querySelector('#about-dialog .about-logo')"
        ui.wait_until(lambda: ui.js(f"{about}.complete && {about}.naturalWidth") == 512, 10)
        assert ui.js(f"{about}.alt") == "Scriptorum logo" and ui.js(f"{about}.getBoundingClientRect().width") > 60
        assert ui.js(f"parseFloat(getComputedStyle({about}).borderTopLeftRadius)") >= 8
        assert ui.js("document.querySelector('#about-dialog .about-head h2').textContent") == "Scriptorum"
        assert __import__("scriptorum").__version__ in ui.js("document.getElementById('about-version').textContent")
        ui.js("document.getElementById('about-close').click(); true")
    ui.window.bridge.session.app_settings.update({"mode": "system"})
    # Under the hood and the Licences tab.
    from scriptorum.core import about
    rows = {r["id"]: r for r in about.programs()}
    assert rows["logo"]["licence"] == "CC-BY-SA-4.0" and rows["logo"]["name"] == "Scriptorum logo"
    assert "AI image tool" in about.text("part:parts/logo.txt") and "CC BY-SA 4.0" in about.text("part:parts/logo.txt")
    licence = about.text("licence:CC-BY-SA-4.0")
    assert licence.startswith("Creative Commons Attribution-ShareAlike 4.0 International") and len(licence) > 15000
    # The README and the files.
    readme = (ROOT / "README.md").read_text("utf-8")
    assert readme.startswith('<p align="center"><img src="scriptorum/ui/logo.png"') and "CC BY-SA 4.0" in readme
    assert (ROOT / "docs" / "logo" / "scriptorum-logo.png").stat().st_size > 1_000_000
    assert not (ROOT / "scriptorum" / "ui" / "logo.svg").exists()
    for icon in ("scriptorum.png", "scav.png", "scmod.png"):
        assert (ROOT / "packaging" / "icons" / icon).is_file()
    # The start-up window: the logo above the name, with rounded corners.
    from scriptorum.app.startup_window import LOGO_SIZE, StartupWindow, logo_pixmap
    from scriptorum.core.startup import Startup, bundled_strings
    window = StartupWindow(Startup(), bundled_strings(), "0.6.10")
    assert not window.logo.pixmap().isNull() and window.logo.accessibleName() == "Scriptorum logo"
    card = logo_pixmap(LOGO_SIZE, 1.0).toImage()
    assert card.width() == LOGO_SIZE and card.pixelColor(0, 0).alpha() == 0 and card.pixelColor(60, 60).alpha() == 255
    window.close()


@pytest.mark.ui
def test_T_UI_51_no_logo_in_pdf(tmp_path):
    """T-UI-51: no exported PDF holds the logo: the Typst build folder never
    gets it, and the app's PDFs carry no picture of its size."""
    for theme_dir in BUNDLED.iterdir():
        assert not list(theme_dir.rglob("logo.png")), theme_dir
    assert "logo.png" not in (ROOT / "scriptorum" / "core" / "build.py").read_text("utf-8")


# --- T-UI-49 the window's zoom (issue #16) ------------------------------------------------------

def _key(ui, key: str, target: str = "document.activeElement || document.body"):
    ui.js(f"({target}).dispatchEvent(new KeyboardEvent('keydown', {{key: {json.dumps(key)}, ctrlKey: true,"
          " bubbles: true, cancelable: true})); true")


def _wheel(ui, target: str, delta: int):
    ui.js(f"(() => {{ const t = {target}; const r = t.getBoundingClientRect();"
          f" t.dispatchEvent(new WheelEvent('wheel', {{deltaY: {delta}, ctrlKey: true, bubbles: true, cancelable: true,"
          " clientX: r.left + 20, clientY: r.top + 20})); return true; })()")


@pytest.mark.ui
def test_T_UI_49_app_zoom(ui):
    """T-UI-49: the window zooms in the steps with Ctrl and the wheel and
    with Ctrl + plus, minus and 0 outside the preview; the status bar shows
    the zoom only when it is not 100 % and clicking it goes back; inside the
    preview only the preview zooms; the zoom is kept for the next start; no
    adventure file changes."""
    _new(ui, "Some words.\n")
    view = ui.window.view
    settings = ui.window.bridge.session.app_settings
    before = dict(ui.window.bridge.session.adventure.files)
    zoom = "document.getElementById('st-zoom')"
    assert ui.js(f"{zoom}.classList.contains('hidden')")
    ui.run("window.__scriptorum.focusBlock([0])")
    _key(ui, "+")
    ui.wait_until(lambda: settings.get("app_zoom") == 110, 5)
    assert abs(view.zoomFactor() - 1.1) < 0.001
    ui.wait_until(lambda: not ui.js(f"{zoom}.classList.contains('hidden')"), 5)
    assert ui.js(f"{zoom}.textContent") == "Zoom 110 %"
    _key(ui, "=")
    ui.wait_until(lambda: settings.get("app_zoom") == 125, 5)
    _key(ui, "-")
    ui.wait_until(lambda: settings.get("app_zoom") == 110, 5)
    _key(ui, "0")
    ui.wait_until(lambda: settings.get("app_zoom") == 100, 5)
    assert abs(view.zoomFactor() - 1.0) < 0.001
    ui.wait_until(lambda: ui.js(f"{zoom}.classList.contains('hidden')"), 5)
    # The scroll wheel over the editor, one step per notch, down to the ends.
    for expected in (90, 80, 75, 67, 50, 50):
        _wheel(ui, "document.getElementById('visual')", 120)
        ui.wait_until(lambda: settings.get("app_zoom") == expected, 5)
        ui.wait(150)
    ui.js(f"{zoom}.click(); true")
    ui.wait_until(lambda: settings.get("app_zoom") == 100, 5)
    for expected in (110, 125, 150, 175, 200, 200):
        _key(ui, "+")
        ui.wait_until(lambda: settings.get("app_zoom") == expected, 5)
    _key(ui, "0")
    ui.wait_until(lambda: settings.get("app_zoom") == 100, 5)
    # In the preview only the preview zooms (F7.2).
    preview_before = ui.js("window.__scriptorum.zoomPercent ? window.__scriptorum.zoomPercent() : null")
    _wheel(ui, "document.getElementById('preview-pane')", -120)
    ui.wait(300)
    assert settings.get("app_zoom") == 100 and abs(view.zoomFactor() - 1.0) < 0.001
    ui.js("document.getElementById('preview-pane').tabIndex = -1; document.getElementById('preview-pane').focus(); true")
    _key(ui, "+", "document.getElementById('preview-pane')")
    ui.wait(300)
    assert settings.get("app_zoom") == 100
    del preview_before
    # The next start opens at the zoom it was left at; out-of-step values are ignored.
    settings.update({"app_zoom": 125})
    assert ui.window.apply_app_zoom() == 125 and abs(view.zoomFactor() - 1.25) < 0.001
    stored = json.loads(settings.file.read_text("utf-8"))
    assert stored["app_zoom"] == 125
    settings.update({"app_zoom": 133})
    assert settings.get("app_zoom") == 125
    settings.update({"app_zoom": 100})
    ui.window.apply_app_zoom()
    assert dict(ui.window.bridge.session.adventure.files) == before


# --- T-UI-50 the + menu in groups (issue #18) ---------------------------------------------------

GROUPED = """Top paragraph.

#scene(title: "Hall")[
Inside the scene.

#box(title: "A box")[
Inside the box.
]

#person(name: "Ada")[
#information(variant: "secret")[She knows.]
]
]
"""


def _plus_menu(ui, block: str) -> list:
    ui.js(f"(() => {{ const b = {block}; b.scrollIntoView({{block: 'center'}});"
          " const c = b.querySelector(':scope > .blk-controls'); c.querySelectorAll('button')[2].click(); return true; })()")
    ui.wait_until(lambda: not ui.js("document.getElementById('menu-popup').classList.contains('hidden')"), 5)
    return ui.js("[...document.querySelectorAll('#menu-popup .menu-column')].map(c => [c.querySelector('.menu-heading').textContent,"
                 " ...[...c.querySelectorAll('.menu-item')].map(i => i.firstChild.textContent)])")


ORDER = ["Text", "Structure", "Boxes", "People", "Rules", "Handouts", "Layout", "Other"]


@pytest.mark.ui
def test_T_UI_50_plus_menu_in_groups(ui):
    """T-UI-50: the + menu shows its groups side by side as columns with
    headings, in the order Text, Structure, Boxes, People, Rules, Handouts,
    Layout, Other, each with only the elements allowed there; a group with
    none is left out; in a person card only Information (and Clue) is
    offered; picking an item inserts it after the block in one undo step;
    the right-click menu and the Insert menu stay one list."""
    for system in (("scriptorum.free-league-vaesen", "scriptorum.vaesen"), ("scriptorum.plain-system", "scriptorum.plain")):
        _new(ui, GROUPED, system)
        top = _plus_menu(ui, "window.__blk('Top paragraph.')")
        assert ui.js("document.getElementById('menu-popup').classList.contains('popup-columns')")
        headings = [c[0] for c in top]
        assert headings == [h for h in ORDER if h in headings]
        assert headings[:3] == ["Text", "Structure", "Boxes"] and "People" in headings and "Rules" in headings
        columns = {c[0]: c[1:] for c in top}
        assert [x.rstrip("…") for x in columns["Text"]] == ["Paragraph", "Table", "Image", "Footnote"]
        assert columns["Layout"] == ["Table of contents", "Full-width section", "Never split"]
        assert "Other" not in columns          # the bundled game systems add no element outside the groups
        assert columns["Boxes"][:3] == ["Read-aloud", "Secret", "Public information"]
        assert all(len(c) > 1 for c in top)                                   # no empty group
        # Side by side: the columns' tops line up.
        tops = ui.js("[...document.querySelectorAll('#menu-popup .menu-column')].map(c => Math.round(c.getBoundingClientRect().top))")
        assert len(set(tops)) < len(tops)
        ui.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); true")
        # In a person card only Information (with Clue).
        inner = _plus_menu(ui, "window.__blk('She knows.')")
        assert [c[0] for c in inner] == ["Boxes"]
        assert inner[0][1:4] == ["Secret", "Public information", "Hint"]
        ui.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); true")
        # Picking an item inserts it after the block, in one undo step.
        before = _text(ui)
        _plus_menu(ui, "window.__blk('Inside the scene.')")
        ui.js("[...document.querySelectorAll('#menu-popup .menu-item')].find(i => i.firstChild.textContent === 'Box').click(); true")
        ui.wait(200)
        after = _text(ui)
        assert after.index("Inside the scene.") < after.index("#box[") < after.index('#box(title: "A box")')
        ui.run("window.__scriptorum.undo()")
        assert _text(ui) == before
    # The Insert menu stays one list.
    ui.js("document.querySelector('.menu-btn[data-menu=\"menu.insert\"]')?.click(); true")
    ui.wait(150)
    if not ui.js("document.getElementById('menu-popup').classList.contains('hidden')"):
        assert not ui.js("document.getElementById('menu-popup').classList.contains('popup-columns')")
    ui.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); true")


# --- T-UI-52 New entry ▸ Creature (issue #1) ----------------------------------------------------

def _new_entry_choices(ui) -> list:
    ui.js("(() => { const b = [...document.querySelectorAll('#codex-panel .codex-actions button')][0]; b.click(); return true; })()")
    ui.wait_until(lambda: ui.js("document.getElementById('prompt-dialog').open"), 5)
    return ui.js("[...document.getElementById('prompt-choice').options].map(o => o.value)")


@pytest.mark.ui
def test_T_UI_52_new_creature_entry(ui):
    """T-UI-52: in a Vaesen adventure Codex ▸ New entry ▸ Creature makes and
    opens a Creature entry in one undo step; in a Plain adventure no Creature
    is offered under New entry."""
    for sub, sample in (("vaesen", "m6-clues"), ("plain", "m5-plain")):
        (ui.folder / sub).mkdir(exist_ok=True)
        assert json.loads(ui.window.bridge.openPath(str(pack_sample(sample, ui.folder / sub))))["ok"]
        ui.run("window.__scriptorum.refresh()")
        ui.js("document.getElementById('nav-codex').click(); true")
        ui.wait(200)
        session = ui.window.bridge.session
        choices = _new_entry_choices(ui)
        if sample == "m5-plain":
            assert "creature" not in choices and "person" in choices
            ui.js("document.getElementById('prompt-cancel').click(); true")
            continue
        assert "creature" in choices
        before = set(session.world.entries())
        history = len(session.world_history)
        ui.js("document.getElementById('prompt-choice').value = 'creature';"
              " document.getElementById('prompt-input').value = 'The well-wight';"
              " document.getElementById('prompt-ok').click(); true")
        ui.wait_until(lambda: len(session.world.entries()) == len(before) + 1, 5)
        new = (set(session.world.entries()) - before).pop()
        entry = session.world.entry(new)
        assert entry["type"] == "creature" and entry["title"] == "The well-wight"
        assert len(session.world_history) == history + 1
        ui.wait_until(lambda: ui.js("!document.getElementById('worldview').classList.contains('hidden')"), 5)
        assert "The well-wight" in ui.js("document.getElementById('worldview').textContent")
        ui.js("document.getElementById('worldview-back').click(); true")
