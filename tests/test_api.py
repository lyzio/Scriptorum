"""0.7.0 step 1: the internal Scriptorum API (design document F23, issue #29).

T-API-01  the public surface and its version; docs/API.md describes it
T-API-02  every area's results are JSON-safe; change, save and export work
T-API-03  plain errors, never raw exceptions; unexpected ones are logged
T-API-04  events
T-API-05  the bridge keeps only Qt and passes everything else to the API
T-API-06  one network gate
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from scriptorum import api as api_module
from scriptorum.api import API_VERSION, Api, surface
from scriptorum.api import net
from scriptorum.core.i18n import Strings
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.conftest import pack_sample

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "scriptorum" / "api"


def _same_json(value) -> bool:
    return json.loads(json.dumps(value)) == value


@pytest.fixture
def api(library, tmp_path):
    session = Session(library, Strings.from_library(library), RecentFiles(tmp_path / "recent.json"), tmp_path / "build",
                      home=tmp_path / "home")
    made = Api(session)
    made.crash_folder = str(tmp_path / "logs")
    return made


# --- T-API-01 the surface ------------------------------------------------------------------------

@pytest.mark.unit
def test_T_API_01_surface_and_version():
    """T-API-01: the surface matches the stored surface of this version, and
    docs/API.md describes every operation and event."""
    stored = json.loads((API_DIR / "surface.json").read_text("utf-8"))
    now = surface()
    # Corrected for 0.7.4: 1.1 adds the extensions area (F25), an addition (9.2).
    assert now["version"] == API_VERSION == stored["version"] == "1.1"
    assert now == stored, "the API's surface changed: raise API_VERSION (9.2) and store the new surface"
    doc = (ROOT / "docs" / "API.md").read_text("utf-8")
    assert f"Version **{API_VERSION}**" in doc
    for operation in now["operations"]:
        area, name = operation.split(".")
        section = doc[doc.index(f"## {area} "):]
        section = section[:section.index("\n## ", 1)] if "\n## " in section[1:] else section
        assert f"`{name}`" in section, operation
    for event in now["events"]:
        assert f"`{event}`" in doc, event
    assert set(now["operations"]) and all(op.split(".")[0] in api_module.AREAS for op in now["operations"])
    assert "API.md" in (ROOT / "docs" / "DEVELOPING.md").read_text("utf-8")


@pytest.mark.unit
def test_T_API_01_a_changed_surface_fails(monkeypatch):
    """T-API-01: an operation added without a new version makes the surface
    differ from the stored one."""
    from scriptorum.api.codex import CodexArea
    monkeypatch.setattr(CodexArea, "brand_new", lambda self, x: None, raising=False)
    stored = json.loads((API_DIR / "surface.json").read_text("utf-8"))
    assert surface() != stored and "codex.brand_new" in surface()["operations"]


# --- T-API-02 plain data --------------------------------------------------------------------------

@pytest.mark.integration
def test_T_API_02_json_safe_results(api, tmp_path):
    """T-API-02: every area's read operations give JSON-safe data for each
    sample; a change, a save and an export work through the API."""
    for sample in ("m1-basic", "m3-world", "m5-plain", "m6-clues"):
        (tmp_path / sample).mkdir()
        reply = api.adventure.open(str(pack_sample(sample, tmp_path / sample)))
        assert reply["ok"], reply
        for value in (
            api.app.settings(), api.app.strings(), api.app.about(), api.app.zoom(), api.app.preview_zoom(),
            api.app.version_info(), api.app.startup_report(), api.app.spell(["hej", "wrod"]),
            api.adventure.info(), api.adventure.editor_info(), api.adventure.tabs(), api.adventure.chapter(0),
            api.adventure.settings(), api.adventure.find("the"), api.adventure.fonts(), api.adventure.snapshots(),
            api.codex.codex(), api.codex.chart(), api.codex.scene_entries(0, 1), api.codex.upgrade_offer(),
            api.modules.game_systems(),
        ):
            assert _same_json(value), sample
        for entry in api.codex.codex()["entries"][:3]:
            assert _same_json(api.codex.entry(entry["id"]))
        for m in api.codex.codex()["maps"][:1]:
            info = api.codex.map_info(m["id"])
            assert info["ok"] and _same_json(info) and Path(info["file"]).is_file()
    # A change, a build, a save and an export.
    text = api.adventure.chapter(0)["text"]
    assert _same_json(api.adventure.set_chapter_text(0, text + "\nOne more line.\n"))
    preview = api.build.preview()
    assert preview["ok"] and _same_json(preview) and all(Path(f).is_file() for f in preview["files"])
    saved = api.adventure.save_to(str(tmp_path / "saved.scav"))
    assert saved["ok"] and Path(saved["path"]).is_file()
    exported = api.build.export(str(tmp_path / "out.pdf"))
    assert exported["ok"] and (tmp_path / "out.pdf").read_bytes().startswith(b"%PDF")
    assert _same_json(exported)


@pytest.mark.integration
def test_T_API_02_same_pdf_as_before(api, tmp_path):
    """T-API-02: the m1-basic sample exported through the API is the
    reference PDF (T-BUILD-03's checksum)."""
    import hashlib
    assert api.adventure.open(str(pack_sample("m1-basic", tmp_path)))["ok"]
    assert api.build.export(str(tmp_path / "m1.pdf"))["ok"]
    assert hashlib.sha256((tmp_path / "m1.pdf").read_bytes()).hexdigest() == \
        "8d2c3db82974b610e7a745d1b21bc6ed2cf4fac4e32d379bb28c7c351f7c8d69"


# --- T-API-03 plain errors ------------------------------------------------------------------------

@pytest.mark.unit
def test_T_API_03_plain_errors(api, tmp_path):
    """T-API-03: operations that cannot work give a plain error with its key;
    an unexpected error is logged and given plainly; nothing changes."""
    # No adventure open.
    reply = api.codex.create_entry("person", "Nobody")
    assert reply == {"ok": False, "error": api.app.text("error.codex.noAdventure"), "key": "error.codex.noAdventure"}
    assert api.codex.codex() == {"types": [], "entries": [], "maps": [], "handouts": []}
    # A file that is not there.
    reply = api.adventure.open(str(tmp_path / "missing.scav"))
    assert reply["ok"] is False and reply["key"] == "error.scav.cannotRead" and "missing.scav" in reply["error"]
    assert len(api.adventure.tabs()) == 1
    # An unknown codex entry.
    assert api.adventure.open(str(pack_sample("m6-clues", tmp_path)))["ok"]
    reply = api.codex.entry("no-such-entry")
    assert reply["ok"] is False and reply["error"] and "key" in reply
    # A refused update address.
    reply = api.app.set_update_address("http://example.org/update.json")
    assert reply == {"ok": False, "error": api.app.text("update.addressRefused"), "key": "update.addressRefused"}
    # A read-only adventure.
    api.session.read_only = "openElsewhere"
    reply = api.codex.create_entry("person", "Nobody")
    assert reply["ok"] is False and reply["error"].startswith("This adventure is read-only")
    api.session.read_only = None
    # An unexpected error.
    before = dict(api.session.world.entries())
    real = api.session.world.__class__.create_entry
    api.session.world.__class__.create_entry = lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("deliberate"))
    try:
        reply = api.codex.create_entry("person", "Nobody")
    finally:
        api.session.world.__class__.create_entry = real
    assert reply["ok"] is False and reply["key"] == "error.codex.failed" and reply["logged"] is True
    assert "deliberate" in Path(reply["log"]).read_text("utf-8")
    assert api.session.world.entries() == before


# --- T-API-04 events -------------------------------------------------------------------------------

@pytest.mark.unit
def test_T_API_04_events(api, tmp_path):
    """T-API-04: opening, editing the text and the codex, building, changing
    a setting, saving and closing are each announced once with JSON-safe details."""
    heard = []
    stop = api.events.subscribe(lambda name, details: heard.append((name, details)))
    api.events.subscribe(lambda name, details: 1 / 0)   # a failing listener changes nothing
    assert api.adventure.open(str(pack_sample("m6-clues", tmp_path)))["ok"]
    text = api.adventure.chapter(0)["text"]
    api.adventure.set_chapter_text(0, text + "\nMore.\n")
    entry = api.codex.create_entry("place", "The mill")
    assert entry["ok"]
    api.build.preview()
    api.app.set_settings({"snapshot_keep": 30})
    api.adventure.save_to(str(tmp_path / "saved.scav"))
    api.adventure.close_active_tab()
    names = [n for n, _ in heard]
    assert names == ["adventure.opened", "text.changed", "codex.changed", "build.finished", "settings.changed",
                     "adventure.saved", "adventure.closed"]
    for name, details in heard:
        assert _same_json(details) and set(details) == set(api_module.EVENTS[name]), name
    assert heard[3][1]["ok"] is True and heard[3][1]["pages"] > 0
    stop()
    (tmp_path / "again").mkdir()
    api.adventure.open(str(pack_sample("m1-basic", tmp_path / "again")))
    assert len(heard) == 7
    with pytest.raises(ValueError):
        api.events.emit("not.an.event")


# --- T-API-05 the bridge keeps only Qt ---------------------------------------------------------------

QT_WORDS = ("QFileDialog", "QMessageBox", "QDesktopServices", "QGuiApplication", "QUrl", "self.window", "_timer",
            ".emit(", "_in_background", "_open_in_browser", "_pick_file", "_save_dialog", "_url(", "QTimer",
            "threading", "_show_error", "requestBuild", "_title_changed", "confirm_discard",
            "last_build_payload")   # the last preview build as the window got it, for the preview window


@pytest.mark.unit
def test_T_API_05_bridge_keeps_only_qt():
    """T-API-05: the bridge imports nothing from scriptorum.core; every slot
    either uses Qt or passes its call to the API."""
    source = (ROOT / "scriptorum" / "app" / "bridge.py").read_text("utf-8")
    tree = ast.parse(source)
    imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
    imported += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    assert not [m for m in imported if m.startswith("scriptorum.core") or m == "scriptorum.core"], imported
    assert "scriptorum.api" in imported
    bridge = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Bridge")
    slots = [f for f in bridge.body if isinstance(f, ast.FunctionDef)
             and any(isinstance(d, ast.Call) and getattr(d.func, "id", "") == "Slot" for d in f.decorator_list)]
    assert len(slots) > 100
    for slot in slots:
        body = ast.get_source_segment(source, slot)
        uses_api = "self.api." in body or re.search(r"self\.(\w+)\(", body) is not None
        uses_qt = any(word in body for word in QT_WORDS)
        assert uses_api or uses_qt, slot.name
    assert len(source.splitlines()) < 1100   # roughly half moved out of 1,424 lines


# --- T-API-06 one network gate ----------------------------------------------------------------------

@pytest.mark.unit
def test_T_API_06_one_network_gate(api):
    """T-API-06: no module outside the gate opens a network connection; the
    update check and the download go through the gate, which records each
    address and refuses anything but https."""
    root = ROOT / "scriptorum"
    users = []
    for file in root.rglob("*.py"):
        text = file.read_text("utf-8")
        if re.search(r"\b(urllib\.request|urlopen|http\.client|socket\.|QNetworkAccessManager|requests\.)", text):
            users.append(file.relative_to(root).as_posix())
    assert users == ["api/net.py"]
    # The update check asks only through the gate. Corrected for 0.7.4
    # (F25.1): connections are blocked by default, so they are turned on first.
    api.session.app_settings.update({"connections_blocked": False})
    asked = []
    api.net.readers[net.UPDATE_FILE] = lambda address: asked.append(address) or b"{}"
    api.app.update_url = "https://example.org/scriptorum-update.json"
    result = api.app.check_updates()
    assert asked == ["https://example.org/scriptorum-update.json"] == api.net.requests
    assert result["state"] not in ("unreachable", "no-address")
    # Without the gate the core asks nothing.
    from scriptorum.core import updates
    assert updates.check("0.1.0", "https://example.org/x.json") == {"state": "unreachable"}
    with pytest.raises(updates.InstallError):
        updates.install({"url": "https://example.org/p.zip"}, api.app.versions)
    # Only https, and only the known purposes.
    with pytest.raises(OSError):
        api.net.fetch(net.UPDATE_FILE, "http://example.org/x.json")
    with pytest.raises(ValueError):
        api.net.fetch("telemetry", "https://example.org/")
    assert api.net.requests == ["https://example.org/scriptorum-update.json"]
