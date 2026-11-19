"""0.7.4 (0.7.0 step 5, extension modules, design document F25, issue #27).

T-EXT-01   Block all connections outside the app
T-EXT-02   the one-time offline message instead of the update question
T-EXT-03   installing with the author's agreement to what it needs
T-EXT-04   network and writes, and plain http only to localhost
T-EXT-05   licences
T-EXT-06   verified or not
T-EXT-07   the API version
T-EXT-08   off until switched on; Settings ▸ Extensions
T-EXT-09   its own process, a menu item and the findings list
T-EXT-10   needs enforced on every call; events only as the needs cover
T-EXT-11   writes as one undo step, only when asked
T-EXT-12   crashes and the time limit
T-EXT-13   network through the gate
T-EXT-14   settings and secrets, and removal
T-EXT-15   nothing changes without extensions

The tests' extensions are written here, into temporary folders; they are
packed as .scmod files and installed as the author would install them. No
test reaches the internet: the network gate gets a stand-in reader.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import time
import zipfile
from pathlib import Path

import pytest

from scriptorum.api import Api, net
from scriptorum.core import extensions as ext_core
from scriptorum.core.appsettings import AppSettings
from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library, ModuleError, pack_scmod, validate_folder
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from scriptorum.core.signing import new_key_pair
from tests.conftest import SAMPLES, pack_sample
from tests.test_m6c2 import BUNDLED

ROOT = Path(__file__).resolve().parents[1]

CHECKER = '''
import json, os, time

def setup(ext):
    log = ext.data_folder / "events.json"

    @ext.on("text.changed")
    def changed(details):
        seen = json.loads(log.read_text()) if log.exists() else []
        seen.append("text.changed")
        log.write_text(json.dumps(seen))
        try:
            ext.call("adventure.set_chapter_text", index=0, text="unasked")
        except Exception as exc:
            (ext.data_folder / "unasked.txt").write_text(str(exc))

    @ext.command("check")
    def check(context):
        info = ext.call("adventure.info")
        text = ext.call("adventure.chapter", index=0)["text"]
        items = [{"text": line.strip(), "chapter": 0, "line": n}
                 for n, line in enumerate(text.splitlines(), 1) if line.startswith("=")]
        items.append({"text": "<b>not markup</b>", "chapter": 0, "line": 1})
        ext.findings("findings", items)
        return {"message": "pid %d, %d found in %s" % (os.getpid(), len(items), info["title"])}

    @ext.command("upper")
    def upper(context):
        for index in range(len(ext.call("adventure.info")["chapters"])):
            text = ext.call("adventure.chapter", index=index)["text"]
            ext.call("adventure.set_chapter_text", index=index, text=text + "\\nWRITTEN BY THE EXTENSION\\n")
        return {"message": "Both chapters."}

    @ext.command("slow-write")
    def slow_write(context):
        text = ext.call("adventure.chapter", index=0)["text"]
        time.sleep(1.5)
        ext.call("adventure.set_chapter_text", index=0, text=text + "\\nLATE\\n")
        return {}

    @ext.command("asks")
    def asks(context):
        answers = {}
        for op, args in (("codex.codex", {}), ("adventure.settings", {}), ("no.such", {}),
                         ("adventure.info", {})):
            try:
                ext.call(op, **args)
                answers[op] = "ok"
            except Exception as exc:
                answers[op] = str(exc)
        return {"message": json.dumps(answers)}

    @ext.command("crash")
    def crash(context):
        os._exit(3)

    @ext.command("hang")
    def hang(context):
        time.sleep(30)
        return {}

    @ext.command("fetch")
    def fetch(context):
        answers = {}
        for url in context.get("urls", []):
            try:
                answers[url] = ext.request(url, method="POST", headers={"Authorization": "Bearer {secret:key}"},
                                           body="question")["status"]
            except Exception as exc:
                answers[url] = "refused: " + str(exc)
        return {"message": json.dumps(answers)}
'''


def make_extension(folder: Path, ext_id="test.checker", version="1.0.0", reads=("text",), changes="writes",
                   network=(), licence="GPL-3.0-or-later", api="1.x", settings=None, main=CHECKER, extra=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": ext_id, "kind": "extension", "name": "Checker", "version": version, "format": 1, "app": "1.0.0",
        "licence": licence, "authors": ["Test author"], "description": "An extension for the tests.",
        "requires": [{"id": "api", "version": api}], "main": "extension.py",
        "needs": {"reads": list(reads), "changes": changes, "network": list(network)},
        "settings": settings if settings is not None else [],
        "menu": [{"id": "check", "label": "Check headings"}, {"id": "upper", "label": "Mark every chapter"},
                 {"id": "slow-write", "label": "Write slowly"}, {"id": "asks", "label": "Ask"},
                 {"id": "crash", "label": "Crash"}, {"id": "hang", "label": "Hang"}, {"id": "fetch", "label": "Fetch"}],
        "block_actions": [{"id": "check", "label": "Check this", "kinds": ["scene"]}],
        "panels": [{"id": "findings", "type": "findings", "title": "Headings"}],
    }
    manifest.update(extra or {})
    (folder / "module.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    (folder / "extension.py").write_text(main, "utf-8")
    return folder


def packed(folder: Path, out: Path) -> Path:
    return pack_scmod(folder, out / f"{folder.name}.scmod")


class FakeKeychain:
    def __init__(self, available=True):
        self.store = {}
        self.ok = available

    def available(self):
        return self.ok

    def get(self, service, name):
        return self.store.get((service, name))

    def set(self, service, name, value):
        self.store[(service, name)] = value

    def delete(self, service, name):
        self.store.pop((service, name), None)


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    lib = Library(tmp_path_factory.mktemp("ext-lib") / "library")
    lib.install_bundled(BUNDLED)
    return lib


def new_api(tmp_path, library=None, home=None) -> Api:
    if library is None:
        library = Library(tmp_path / "library")
        library.install_bundled(BUNDLED)
    home = home or tmp_path / "home"
    session = Session(library, Strings.from_library(library), RecentFiles(tmp_path / "recent.json"), tmp_path / "build",
                      home=home, app_settings=AppSettings(home / "app-settings.json"))
    api = Api(session)
    api.extensions.keychain = FakeKeychain()
    return api


@pytest.fixture
def api(tmp_path):
    a = new_api(tmp_path)
    yield a
    a.extensions.stop_all()


def two_chapters(tmp_path: Path) -> Path:
    """m1-basic with a second chapter, in a temporary copy (samples are never changed)."""
    folder = tmp_path / "two"
    shutil.copytree(SAMPLES / "m1-basic", folder)
    (folder / "text" / "chapter-02.typ").write_text("= Act two\n\nMore text.\n", "utf-8")
    manifest = json.loads((folder / "manifest.json").read_text("utf-8"))
    manifest["chapters"] = ["text/chapter-01.typ", "text/chapter-02.typ"]
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    target = tmp_path / "two.scav"
    with zipfile.ZipFile(target, "w") as zf:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(folder).as_posix())
    return target


def install(api: Api, folder: Path, tmp_path: Path, on=True) -> dict:
    reply = api.extensions.install(str(packed(folder, tmp_path)), agreed=True)
    assert reply["ok"], reply
    if on:
        api.extensions.set_on(reply["installed"]["id"], True)
    return reply


def wait_for(api: Api, kinds=("done", "failed"), count=1, timeout=20.0) -> list:
    """Pump until ``count`` new notices of these kinds arrived; return them."""
    start = len(api.extensions.notices)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        api.extensions.pump()
        fresh = [n for n in api.extensions.notices[start:] if n["kind"] in kinds]
        if len(fresh) >= count:
            return fresh
        time.sleep(0.03)
    raise AssertionError(f"no {kinds} notice: {api.extensions.notices[start:]}")


def run(api: Api, command: str, context=None) -> dict:
    reply = api.extensions.run("test.checker", command, context or {})
    assert reply["ok"], reply
    return wait_for(api)[-1]


# --- T-EXT-01 Block all connections outside the app ------------------------------------------

@pytest.mark.unit
def test_T_EXT_01_switch_blocks_everything(api):
    """T-EXT-01: on by default; while on nothing leaves the app: the update
    check says so and sends nothing, the weekly check does not run, the gate
    refuses every purpose; with it off the update check works as before."""
    settings = api.session.app_settings
    assert settings.get("connections_blocked") is True and api.app.connections_blocked()
    asked = []
    api.net.readers[net.UPDATE_FILE] = lambda address: asked.append(address) or b"not json"
    result = api.app.check_updates()
    assert result["state"] == "blocked" and not asked and api.net.requests == []
    for purpose in (net.UPDATE_FILE, net.UPDATE_PACK):
        with pytest.raises(net.ConnectionsBlocked):
            api.net.fetch(purpose, "https://example.org/x")
    with pytest.raises(net.ConnectionsBlocked):
        api.net.request("https://example.org/x")
    assert api.net.requests == [] and len(api.net.refused) == 3
    settings.update({"update_weekly": True, "update_last_check": 0})
    assert api.app.weekly_check_due() is False
    api.app.update_pack = {"url": "https://example.org/p.zip"}
    assert api.app.install_update() == {"ok": False, "reason": "blocked"}
    settings.update({"connections_blocked": False})
    assert api.app.weekly_check_due() is True
    result = api.app.check_updates()
    assert result["state"] == "invalid" and len(asked) == 1 and api.net.requests == asked


@pytest.mark.unit
def test_T_EXT_01_texts_and_setting():
    """T-EXT-01: the words of the switch and of the blocked update check come
    from the interface-language module (F15)."""
    strings = json.loads((BUNDLED / "scriptorum.en" / "strings" / "update.json").read_text("utf-8"))
    assert strings["blocked"].startswith("Connections outside the app are blocked")
    settings = json.loads((BUNDLED / "scriptorum.en" / "strings" / "settings.json").read_text("utf-8"))
    assert settings["app.blockConnections"] == "Block all connections outside the app"
    shell = (ROOT / "ui-src" / "shell.ts").read_text("utf-8")
    assert 'blocked.id = "app-connectionsBlocked"' in shell and "connections_blocked: blocked.checked" in shell


# --- T-EXT-02 the offline message ------------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_02_offline_message(tmp_path):
    """T-EXT-02: no update question; the offline message once, on a new
    install and on one updated from an earlier version that had turned the
    weekly check on, which starts with connections blocked too."""
    text = json.loads((BUNDLED / "scriptorum.en" / "strings" / "connections.json").read_text("utf-8"))["offlineNotice"]
    assert text == ("Scriptorum is offline by default, including updates. "
                    "To get updates, open Settings and turn on connections.")
    fresh = new_api(tmp_path / "fresh")
    assert fresh.app.update_prompt(True) == {"ask": False}
    assert fresh.app.offline_notice(True) == {"show": True}
    assert fresh.app.offline_notice(False) == {"show": False}   # test windows skip it
    fresh.app.offline_notice_seen()
    assert fresh.app.offline_notice(True) == {"show": False}
    assert new_api(tmp_path / "fresh", home=tmp_path / "fresh" / "home").app.offline_notice(True) == {"show": False}
    old_home = tmp_path / "old" / "home"
    old_home.mkdir(parents=True)
    (old_home / "app-settings.json").write_text(json.dumps({"update_asked": True, "update_weekly": True}), "utf-8")
    old = new_api(tmp_path / "old", home=old_home)
    assert old.app.connections_blocked() and old.app.offline_notice(True) == {"show": True}
    app_ts = (ROOT / "ui-src" / "app.ts").read_text("utf-8")
    assert 'call("offlineNotice")' in app_ts and 'openSettingsWindow("application")' in app_ts
    assert 'call("answerUpdatePrompt"' not in app_ts


# --- T-EXT-03 installing with agreement --------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_03_agreement_before_installing(api, tmp_path):
    """T-EXT-03: what it needs is shown before installing, and nothing is
    installed until the author agrees; a newer version with the same needs
    installs without asking, one that adds a need asks and names it."""
    file = packed(make_extension(tmp_path / "v1"), tmp_path)
    info = api.extensions.inspect(str(file))
    assert info["ok"] and info["extension"] and info["askConsent"] and info["installedVersion"] is None
    assert info["name"] == "Checker" and info["licence"] == "GPL-3.0-or-later" and info["verified"] is False
    assert "Reads the text of the open adventure" in info["needs"]
    assert any("Changes the open adventure directly" in n for n in info["needs"])
    via_modules = api.modules.install(str(file))
    assert via_modules["ok"] is False and via_modules["extension"] and via_modules["inspect"]["needs"] == info["needs"]
    refused = api.extensions.install(str(file))
    assert refused["ok"] is False and refused["key"] == "error.ext.notAgreed"
    assert api.session.library.of_kind("extension") == []
    assert api.extensions.install(str(file), agreed=True)["ok"]
    same = packed(make_extension(tmp_path / "v2", version="1.1.0"), tmp_path)
    info = api.extensions.inspect(str(same))
    assert info["askConsent"] is False and info["added"] == [] and info["installedVersion"] == "1.0.0"
    assert api.extensions.install(str(same))["ok"]
    more = packed(make_extension(tmp_path / "v3", version="1.2.0", reads=("text", "codex")), tmp_path)
    info = api.extensions.inspect(str(more))
    assert info["askConsent"] is True and info["added"] == ["Reads the codex of the open adventure"]
    assert api.extensions.install(str(more))["key"] == "error.ext.notAgreed"
    assert api.extensions.install(str(more), agreed=True)["ok"]
    versions = [m.version for m in api.session.library.installed(True) if m.id == "test.checker"]
    assert versions == ["1.2.0"]   # a newer version replaces the older one
    assert all(m["kind"] != "extension" for m in api.app.settings()["modules"])   # not in Settings ▸ Modules


@pytest.mark.unit
def test_T_EXT_03_python_only_in_extensions(tmp_path):
    """T-EXT-03: a .py file in a theme and a compiled file in an extension
    are refused with the file named."""
    theme = tmp_path / "theme"
    shutil.copytree(BUNDLED / "scriptorum.plain", theme)
    (theme / "helper.py").write_text("x = 1\n", "utf-8")
    with pytest.raises(ModuleError) as caught:
        validate_folder(theme)
    assert caught.value.key == "error.module.forbiddenFile" and caught.value.details["file"] == "helper.py"
    for name in ("speed.so", "lib/fast.pyd", "tool.dll", "run.exe"):
        folder = make_extension(tmp_path / name.replace("/", "-"))
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(b"\x7fELF")
        with pytest.raises(ModuleError) as caught:
            validate_folder(folder)
        assert caught.value.details["file"] == name
    validate_folder(make_extension(tmp_path / "fine"))


# --- T-EXT-04 network and writes ---------------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_04_network_cannot_write(api, tmp_path):
    """T-EXT-04: a network host with writes is refused, localhost included;
    with suggests or none it installs; plain http only to localhost."""
    setting = [{"id": "address", "kind": "text", "label": "Address"}]
    for n, network in enumerate((["api.example.com"], [{"setting": "address"}], ["localhost"])):
        file = packed(make_extension(tmp_path / f"w{n}", network=network, settings=setting), tmp_path)
        info = api.extensions.inspect(str(file))
        assert info["ok"] is False and info["key"] == "error.ext.networkWrites", info
        assert info["error"].startswith("An extension that uses an outside service can only suggest changes.")
    for n, changes in enumerate(("suggests", "none")):
        file = packed(make_extension(tmp_path / f"s{n}", ext_id=f"test.s{n}", network=["api.example.com"],
                                     changes=changes), tmp_path)
        assert api.extensions.install(str(file), agreed=True)["ok"]
    assert net.extension_address_ok("http://localhost:11434/api") and net.extension_address_ok("http://127.0.0.1/x")
    assert net.extension_address_ok("https://api.example.com/v1")
    assert not net.extension_address_ok("http://api.example.com/v1") and not net.extension_address_ok("ftp://x.org")


# --- T-EXT-05 licences -------------------------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_05_licences(api, tmp_path):
    """T-EXT-05: GPL-compatible licences install; the others are refused with
    the licence named."""
    for licence in ("GPL-3.0-or-later", "MIT", "BSD-3-Clause", "Apache-2.0", "LGPL-3.0-or-later", "MPL-2.0",
                    "MIT OR Apache-2.0"):
        assert ext_core.licence_ok(licence), licence
    for n, licence in enumerate(("LicenseRef-Proprietary", "CC-BY-NC-4.0", "")):
        assert not ext_core.licence_ok(licence)
        info = api.extensions.inspect(str(packed(make_extension(tmp_path / f"l{n}", licence=licence), tmp_path)))
        assert info["ok"] is False and info["key"] == "error.ext.licence"
        assert f"“{licence}”" in info["error"]


# --- T-EXT-06 verified or not ------------------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_06_verified(api, tmp_path):
    """T-EXT-06: signed with the project's key: from the Scriptorum project;
    changed after signing, or unsigned: unverified."""
    private, public = new_key_pair()
    api.extensions.key = public
    signed = make_extension(tmp_path / "signed")
    ext_core.sign_folder(signed, private)
    assert api.extensions.inspect(str(packed(signed, tmp_path)))["verified"] is True
    changed = tmp_path / "changed"
    shutil.copytree(signed, changed)
    (changed / "extension.py").write_text(CHECKER + "\n# changed\n", "utf-8")
    assert api.extensions.inspect(str(packed(changed, tmp_path)))["verified"] is False
    assert api.extensions.inspect(str(packed(make_extension(tmp_path / "plain"), tmp_path)))["verified"] is False
    other, _ = new_key_pair()
    wrong = make_extension(tmp_path / "wrong")
    ext_core.sign_folder(wrong, other)
    assert api.extensions.inspect(str(packed(wrong, tmp_path)))["verified"] is False
    texts = json.loads((BUNDLED / "scriptorum.en" / "strings" / "ext.json").read_text("utf-8"))
    assert texts["verified"] == "From the Scriptorum project."
    assert texts["unverified"] == "Unverified: runs program code; only install from people you trust."


# --- T-EXT-07 the API version ------------------------------------------------------------------

@pytest.mark.unit
def test_T_EXT_07_api_version(api, tmp_path):
    """T-EXT-07: api 1.x and 1.1 install; 2.x is refused with both versions."""
    from scriptorum.api import API_VERSION
    assert API_VERSION == "1.1"
    for n, wanted in enumerate(("1.x", "1.1")):
        assert api.extensions.inspect(str(packed(make_extension(tmp_path / f"a{n}", api=wanted), tmp_path)))["ok"]
    info = api.extensions.inspect(str(packed(make_extension(tmp_path / "a2", api="2.x"), tmp_path)))
    assert info["ok"] is False and info["key"] == "error.ext.apiVersion" and "2.x" in info["error"] and "1.1" in info["error"]
    assert not ext_core.api_matches("1.9")   # needs operations this app does not have


# --- T-EXT-08, T-EXT-10 to T-EXT-14 in the core ---------------------------------------------------

@pytest.mark.integration
def test_T_EXT_08_off_until_switched_on(tmp_path):
    """T-EXT-08: no process and no items until switched on; the choice is
    kept for the next start."""
    api = new_api(tmp_path)
    try:
        install(api, make_extension(tmp_path / "e"), tmp_path, on=False)
        assert api.extensions.running() == [] and api.extensions.contributions() == []
        row = api.extensions.list()["extensions"][0]
        assert row["on"] is False and row["verified"] is False and row["needsNetwork"] is False
        api.extensions.set_on("test.checker", True)
        assert api.extensions.running() == ["test.checker"]
        assert api.extensions.contributions()[0]["menu"][0] == {"id": "check", "label": "Check headings"}
    finally:
        api.extensions.stop_all()
    again = new_api(tmp_path, library=api.session.library, home=tmp_path / "home")
    assert again.extensions.list()["extensions"][0]["on"] is True
    net_ext = make_extension(tmp_path / "n", ext_id="test.net", changes="suggests", network=["api.example.com"])
    install(again, net_ext, tmp_path, on=False)
    rows = {r["id"]: r for r in again.extensions.list()["extensions"]}
    assert rows["test.net"]["needsNetwork"] is True and rows["test.checker"]["needsNetwork"] is False
    again.extensions.stop_all()


@pytest.mark.integration
def test_T_EXT_09_own_process_and_findings(api, tmp_path):
    """T-EXT-09: it runs in a process of its own and its findings arrive as
    plain data for the app to draw."""
    install(api, make_extension(tmp_path / "e"), tmp_path)
    api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    done = run(api, "check")
    assert done["ok"] and done["wrote"] is False
    assert int(done["message"].split()[1].rstrip(",")) != os.getpid()
    shown = api.extensions.findings()[0]
    assert shown["title"] == "Headings" and shown["name"] == "Checker"
    assert {"text": "= Act one: The silent mill", "chapter": 0, "line": 1} in shown["items"]
    assert {"text": "<b>not markup</b>", "chapter": 0, "line": 1} in shown["items"]


@pytest.mark.integration
def test_T_EXT_10_needs_enforced(api, tmp_path):
    """T-EXT-10: a covered call is answered; an undeclared and an unknown one
    are refused plainly; events only as the needs cover."""
    install(api, make_extension(tmp_path / "e", changes="none"), tmp_path)
    api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    answers = json.loads(run(api, "asks")["message"])
    assert answers["adventure.info"] == "ok"
    assert "did not declare" in answers["codex.codex"] and "did not declare" in answers["adventure.settings"]
    assert "not something an extension can ask for" in answers["no.such"]
    data = api.extensions.store.data_folder("test.checker")
    text = api.adventure.chapter(0)["text"]
    api.adventure.set_chapter_text(0, text + "\nAn edit.\n")
    end = time.monotonic() + 10
    while time.monotonic() < end and not (data / "unasked.txt").exists():
        api.extensions.pump()
        time.sleep(0.03)
    assert json.loads((data / "events.json").read_text()) == ["text.changed"]
    assert "did not declare" in (data / "unasked.txt").read_text()   # changes: none
    # An extension that reads nothing hears no text events.
    quiet = make_extension(tmp_path / "q", ext_id="test.quiet", reads=(), changes="none")
    install(api, quiet, tmp_path)
    api.adventure.set_chapter_text(0, text)
    for _ in range(20):
        api.extensions.pump()
        time.sleep(0.03)
    assert not (api.extensions.store.data_folder("test.quiet") / "events.json").exists()


@pytest.mark.integration
def test_T_EXT_11_writes_one_undo_step(api, tmp_path):
    """T-EXT-11: two chapters changed in one undo step named after the
    extension; writes outside a command, in a read-only adventure and after
    the author changed the text are refused."""
    install(api, make_extension(tmp_path / "e"), tmp_path)
    api.adventure.open(str(two_chapters(tmp_path)))
    before = [api.adventure.chapter(i)["text"] for i in (0, 1)]
    done = run(api, "upper")
    assert done["ok"] and done["wrote"] and done["chapters"] == [0, 1]
    assert done["undoName"] == "Checker: Mark every chapter"
    assert all("WRITTEN BY THE EXTENSION" in api.adventure.chapter(i)["text"] for i in (0, 1))
    assert api.session.world_undo()
    assert [api.adventure.chapter(i)["text"] for i in (0, 1)] == before
    # Unasked: the event listener's write was refused (it is not in a command).
    data = api.extensions.store.data_folder("test.checker")
    end = time.monotonic() + 10
    while time.monotonic() < end and not (data / "unasked.txt").exists():
        api.extensions.pump()
        time.sleep(0.03)
    assert "without being asked" in (data / "unasked.txt").read_text()
    assert [api.adventure.chapter(i)["text"] for i in (0, 1)] == before
    # The author changes the text while the extension works.
    assert api.extensions.run("test.checker", "slow-write", {})["ok"]
    api.adventure.set_chapter_text(0, before[0] + "\nThe author's line.\n")
    done = wait_for(api)[-1]
    assert done["ok"] is False and "The text changed while Checker was working" in done["message"]
    assert "LATE" not in api.adventure.chapter(0)["text"]
    # Read-only.
    api.session.read_only = True
    done = run(api, "upper")
    assert done["ok"] is False and done["wrote"] is False and "read-only" in done["message"]
    api.session.read_only = False
    app_ts = (ROOT / "ui-src" / "app.ts").read_text("utf-8")
    assert 't("menu.undoNamed", { name: named.name })' in app_ts
    assert json.loads((BUNDLED / "scriptorum.en" / "strings" / "menu.json").read_text("utf-8"))["undoNamed"] == "Undo {name}"


@pytest.mark.integration
def test_T_EXT_12_crashes_and_time_limit(api, tmp_path):
    """T-EXT-12: a crash and a command over the time limit give a plain
    message and the app keeps working; after three the extension is off."""
    install(api, make_extension(tmp_path / "e"), tmp_path)
    api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    text = api.adventure.chapter(0)["text"]
    api.extensions.run("test.checker", "crash", {})
    failed = wait_for(api, ("failed",))[-1]
    assert failed["message"] == "Checker stopped unexpectedly. Scriptorum and your adventure are fine."
    api.extensions.time_limit = 1.5
    api.extensions.run("test.checker", "hang", {})
    failed = wait_for(api, ("failed",))[-1]
    assert "did not answer within 1 seconds" in failed["message"] or "within 1" in failed["message"]
    assert api.extensions.running() == []
    assert api.adventure.chapter(0)["text"] == text   # the adventure is untouched
    api.extensions.run("test.checker", "crash", {})
    notices = wait_for(api, ("switchedOff",))
    assert "failed 3 times and has been switched off" in notices[-1]["message"]
    assert api.extensions.store.state("test.checker")["on"] is False
    assert api.extensions.run("test.checker", "check", {})["key"] == "error.ext.notOn"
    api.extensions.set_on("test.checker", True)   # switched on by hand: a fresh start
    assert run(api, "check")["ok"]


@pytest.mark.integration
def test_T_EXT_13_network_through_the_gate(api, tmp_path):
    """T-EXT-13: blocked: refused naming the switch. Allowed: the declared
    host, the address entered and localhost through the gate; the others
    refused; a secret is filled in by the app."""
    settings = [{"id": "address", "kind": "text", "label": "Address"}, {"id": "key", "kind": "secret", "label": "API key"}]
    folder = make_extension(tmp_path / "e", changes="suggests", network=["api.example.com", {"setting": "address"}, "localhost"],
                            settings=settings)
    install(api, folder, tmp_path)
    api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    seen = []
    api.net.readers[net.EXTENSION] = lambda url, method, headers, body: (
        seen.append((url, method, headers.get("Authorization"), body)) or {"status": 200, "headers": {}, "base64": ""})
    urls = ["https://api.example.com/v1"]
    answers = json.loads(run(api, "fetch", {"urls": urls})["message"])
    assert "connections outside the app are blocked" in answers[urls[0]] and seen == []
    api.session.app_settings.update({"connections_blocked": False})
    api.extensions.set_setting("test.checker", "key", "s3cret")
    api.extensions.set_setting("test.checker", "address", "https://my.server.net/api")
    urls = ["https://api.example.com/v1", "https://my.server.net/api", "http://localhost:11434/x",
            "https://other.example.org/", "http://api.example.com/v1"]
    answers = json.loads(run(api, "fetch", {"urls": urls})["message"])
    assert [answers[u] for u in urls[:3]] == [200, 200, 200]
    assert "did not declare" in answers[urls[3]] and "did not declare" in answers[urls[4]]
    assert [s[0] for s in seen] == urls[:3] and all(s[1] == "POST" and s[2] == "Bearer s3cret" for s in seen)
    assert all(s[3] == b"question" for s in seen)
    api.extensions.set_setting("test.checker", "address", "https://elsewhere.net/")
    answers = json.loads(run(api, "fetch", {"urls": ["https://my.server.net/api"]})["message"])
    assert "did not declare" in answers["https://my.server.net/api"]


@pytest.mark.integration
def test_T_EXT_14_settings_secrets_and_removal(tmp_path):
    """T-EXT-14: settings kept; a secret in the keychain and never in a
    settings file; without a keychain in a file only the user can read;
    removing removes everything."""
    settings = [{"id": "model", "kind": "choice", "label": "Model", "options": ["small", "large"], "default": "small"},
                {"id": "key", "kind": "secret", "label": "API key"}]
    api = new_api(tmp_path)
    keychain = api.extensions.keychain
    install(api, make_extension(tmp_path / "e", changes="suggests", network=["api.example.com"], settings=settings),
            tmp_path, on=False)
    api.extensions.set_setting("test.checker", "model", "large")
    assert api.extensions.set_setting("test.checker", "model", "huge")["ok"] is False
    api.extensions.set_setting("test.checker", "key", "s3cret")
    store_root = api.extensions.store.root
    assert "s3cret" not in (store_root / "state.json").read_text()
    assert keychain.store == {("Scriptorum extension test.checker", "key"): "s3cret"}
    again = new_api(tmp_path, library=api.session.library, home=tmp_path / "home")
    again.extensions.keychain = keychain
    row = again.extensions.list()["extensions"][0]
    assert row["settings"][0]["value"] == "large" and row["settings"][1] == {
        "id": "key", "label": "API key", "kind": "secret", "note": "", "set": True}
    assert again.extensions.list()["keychain"] is True
    # Without a keychain.
    plain = new_api(tmp_path / "nokeychain")
    plain.extensions.keychain = FakeKeychain(available=False)
    install(plain, make_extension(tmp_path / "e2", changes="suggests", network=["api.example.com"], settings=settings),
            tmp_path, on=False)
    plain.extensions.set_setting("test.checker", "key", "s3cret")
    assert plain.extensions.list()["keychain"] is False
    secret_file = plain.extensions.store.root / "secrets" / "test.checker.json"
    assert json.loads(secret_file.read_text()) == {"key": "s3cret"}
    if os.name == "posix":
        assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600
    assert plain.extensions.store.secret("test.checker", "key") == "s3cret"
    # Removing.
    plain.extensions.store.data_folder("test.checker")
    assert plain.extensions.remove("test.checker")["extensions"] == []
    assert not secret_file.exists() and not (plain.extensions.store.root / "data" / "test.checker").exists()
    assert "test.checker" not in json.loads((plain.extensions.store.root / "state.json").read_text())
    again.extensions.remove("test.checker")
    assert keychain.store == {}


@pytest.mark.unit
def test_T_EXT_15_nothing_without_extensions(api):
    """T-EXT-15: with connections allowed and no extension, the only request
    is the update check; nothing is running."""
    api.session.app_settings.update({"connections_blocked": False})
    api.net.readers[net.UPDATE_FILE] = lambda address: b"{}"
    api.app.check_updates()
    assert len(api.net.requests) == 1 and api.extensions.running() == [] and api.extensions.list()["extensions"] == []


@pytest.mark.unit
def test_T_EXT_keyring_pinned_and_packaged():
    """T-EXT-14, T-EXT-16: keyring is pinned, in About ▸ Under the hood, and
    carried into the installers with its keychain backends."""
    pyproject = (ROOT / "pyproject.toml").read_text("utf-8")
    assert '"keyring==25.7.0"' in pyproject
    spec = (ROOT / "packaging" / "common" / "scriptorum.spec").read_text("utf-8")
    assert '"keyring")' in spec and 'collect_submodules("keyring.backends")' in spec
    assert 'needed.append("keyring")' in (ROOT / "packaging" / "build.py").read_text("utf-8")
    from scriptorum.core import about
    rows = {r["id"]: r for r in about.programs()}
    assert rows["keyring"]["licence"] == "MIT" and rows["keyring"]["version"] == "25.7.0"
    assert "SecretStorage" in about.text("part:parts/keyring.txt")


# --- the window: T-EXT-01, 08, 09, 11, 15 -----------------------------------------------------------

@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-step5")
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


def _menus(ui) -> list:
    return ui.js("[...document.querySelectorAll('#menubar .menu-btn')].map((b) => b.textContent)")


@pytest.mark.ui
def test_T_EXT_15_window_without_extensions(ui):
    """T-EXT-15: six menus and no Extensions menu; Settings ▸ Extensions says
    none is installed."""
    assert _menus(ui) == ["File", "Edit", "View", "Insert", "Format", "Help"]
    ui.run("window.__scriptorum.openSettingsWindow('extensions')")
    ui.wait_until(lambda: ui.js("!!document.getElementById('ext-none')"), 10)
    assert ui.js("document.getElementById('ext-none').textContent") == "No extension is installed."
    ui.js("document.getElementById('settings-close').click(); true")


@pytest.mark.ui
def test_T_EXT_01_window(ui):
    """T-EXT-01: Settings ▸ Application has the switch, on; Check for updates
    says connections are blocked, with a button to the setting."""
    ui.run("window.__scriptorum.openSettingsWindow('application')")
    assert ui.js("document.getElementById('app-connectionsBlocked').checked") is True
    ui.js("document.getElementById('settings-close').click(); true")
    done = int(ui.js("Number(document.body.dataset.updateDone || 0)"))
    ui.run("window.__scriptorum.updates.check()")
    ui.wait_until(lambda: int(ui.js("Number(document.body.dataset.updateDone || 0)")) > done, 10)
    assert ui.js("document.body.dataset.updateState") == "blocked"
    assert ui.js("document.getElementById('update-text').textContent").startswith("Connections outside the app are blocked")
    assert ui.js("!document.getElementById('update-settings').classList.contains('hidden')")
    ui.js("document.getElementById('update-settings').click(); true")
    ui.wait_until(lambda: ui.js("!document.getElementById('settings').classList.contains('hidden')"), 5)
    assert ui.js("document.getElementById('sp-application').classList.contains('hidden')") is False
    ui.js("document.getElementById('settings-close').click(); true")
    assert ui.window.bridge.api.net.requests == []


@pytest.mark.ui
def test_T_EXT_08_09_11_window(ui):
    """T-EXT-08, 09, 11: install with the needs shown, switch on in Settings ▸
    Extensions, run its menu item, findings drawn by the app and a click goes
    to the line; a write is one undo step named after the extension."""
    api = ui.window.bridge.api
    file = packed(make_extension(ui.folder / "ext"), ui.folder)
    ui.run("window.__scriptorum.openSettingsWindow('extensions')")
    ui.js(f"window.__scriptorum.shell.installExtensionFile({json.dumps(str(file))}); true")
    ui.wait_until(lambda: ui.js("document.getElementById('ext-consent').open"), 10)
    needs = ui.js("[...document.querySelectorAll('#ext-consent-needs li')].map((li) => li.textContent)")
    assert "Reads the text of the open adventure" in needs
    assert ui.js("document.getElementById('ext-consent-verified').textContent").startswith("Unverified")
    ui.js("document.getElementById('ext-consent-ok').click(); true")
    ui.wait_until(lambda: ui.js("!!document.querySelector('[data-extension=\"test.checker\"]')"), 10)
    assert api.extensions.running() == [] and "Extensions" not in _menus(ui)
    ui.js("document.querySelector('[data-extension=\"test.checker\"] input[data-action=on]').click(); true")
    ui.wait_until(lambda: "Extensions" in _menus(ui), 10)
    assert api.extensions.running() == ["test.checker"]
    ui.js("document.getElementById('settings-close').click(); true")
    reply = json.loads(ui.window.bridge.openPath(str(pack_sample("m1-basic", ui.folder))))
    assert reply.get("ok", True)
    ui.run("window.__scriptorum.refresh()")
    ui.run("window.__scriptorum.setMode('visual')")
    count = int(ui.js("Number(document.body.dataset.extNotices || 0)"))
    ui.run("window.__scriptorum.extensions.run('test.checker', 'check', {})")
    ui.wait_until(lambda: int(ui.js("Number(document.body.dataset.extNotices || 0)")) >= count + 2, 20)
    # Corrected for 0.7.5 (F25, the Extensions tab): the findings list is in
    # the Extensions tab at the bottom of the left pane, not a floating panel.
    ui.wait_until(lambda: ui.js("document.querySelectorAll('#ext-tab .ext-findings li').length") > 0, 10)
    assert ui.js("document.getElementById('lt-extensions').getAttribute('aria-selected')") == "true"
    assert ui.js("document.querySelector('#ext-tab .ext-section h4').textContent").startswith("Headings")
    items = ui.js("[...document.querySelectorAll('#ext-tab .ext-findings li')].map((li) => li.textContent)")
    assert "= Act one: The silent mill" in items and "<b>not markup</b>" in items
    assert ui.js("document.querySelector('#ext-tab .ext-findings b')") is None
    ui.js("document.querySelector('#ext-tab .ext-findings li.goes').click(); true")
    # A write: one undo step, named after the extension.
    count = int(ui.js("Number(document.body.dataset.extNotices || 0)"))
    ui.run("window.__scriptorum.extensions.run('test.checker', 'upper', {})")
    ui.wait_until(lambda: int(ui.js("Number(document.body.dataset.extNotices || 0)")) >= count + 1, 20)
    ui.wait_until(lambda: "WRITTEN BY THE EXTENSION" in ui.state()["text"], 10)
    assert ui.js("window.__scriptorum.extensions.undoLabel()") == "Undo Checker: Mark every chapter"
    ui.run("window.__scriptorum.undo()")
    ui.wait_until(lambda: "WRITTEN BY THE EXTENSION" not in ui.state()["text"], 10)
    assert ui.js("window.__scriptorum.extensions.undoLabel()") == "Undo"


@pytest.mark.integration
def test_T_EXT_16_hand_check_extension_works(api, tmp_path):
    """T-EXT-16 (the automated part): the small extension in tests/extensions/
    that the project manager installs by hand passes every check and lists
    the headings of the open chapter."""
    reply = api.extensions.install(str(packed(ROOT / "tests" / "extensions" / "heading-check", tmp_path)), agreed=True)
    assert reply["ok"], reply
    api.extensions.set_on("lyzio.heading-check", True)
    api.adventure.open(str(pack_sample("m1-basic", tmp_path)))
    assert api.extensions.run("lyzio.heading-check", "list", {"chapter": 0})["ok"]
    done = wait_for(api)[-1]
    assert done["ok"] and done["message"].endswith("headings.")
    assert api.extensions.findings()[0]["items"][0]["text"].startswith("=")
