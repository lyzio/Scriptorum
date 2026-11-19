"""The API's extensions area (design document F25, 0.7.4, issue #27).

Installing extensions with the author's agreement to what they need, turning
them on and off, their settings and secrets, and running the switched-on
ones, each in a process of its own (``core/exthost.py``). An extension's
code reaches the app only through the calls this area answers, each checked
against what the extension declared it needs (F25.13):

    adventure.info, adventure.chapter        needs "reads": ["text"]
    codex.codex, codex.entry                 needs "reads": ["codex"]
    adventure.settings                       needs "reads": ["settings"]
    adventure.blocks                         needs "reads": ["text"] (0.7.5)
    adventure.set_chapter_text               needs "changes": "writes", and only
                                             while a command the author started runs
    suggest.replace, suggest.add             needs "changes": "suggests" or "writes" (0.7.5)
    picture.show                             a picture for the author to Use or not (0.7.5)
    net.request                              a declared host, through the gate (F25.16)
    settings.get                             its own settings (never a secret)

What happens is told to the window through ``listeners`` (the bridge) as
small JSON-safe notices: a command finished, findings arrived, an extension
failed or was switched off.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import base64
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Dict, List, Optional

from scriptorum.api import net
from scriptorum.core import extensions as ext_core
from scriptorum.core import modmanager
from scriptorum.core.modules import ModuleError, unpack_scmod, validate_folder

COMMAND_LIMIT = 30.0     # F25.14: seconds an extension may take to answer
CRASH_LIMIT = 3          # F25.14: crashes in one session before it is switched off
MESSAGE_LIMIT = 2000     # the longest message an extension's answer may carry
_ROOT = Path(__file__).resolve().parents[2]

# F25.13: what each call needs.
READS = {
    "adventure.info": "text",
    "adventure.chapter": "text",
    "adventure.blocks": "text",
    "codex.codex": "codex",
    "codex.entry": "codex",
    "adventure.settings": "settings",
}
# F25.15: the events each read covers.
EVENT_NEEDS = {
    "adventure.opened": "text", "adventure.closed": "text", "adventure.saved": "text",
    "text.changed": "text", "build.finished": "text", "codex.changed": "codex",
}
SECRET = re.compile(r"\{secret:([a-z0-9][a-z0-9-]{0,40})\}")


class Refused(Exception):
    def __init__(self, key: str, **details):
        super().__init__(key)
        self.key = key
        self.details = details


class Command:
    def __init__(self, number: int, item: dict, session):
        self.number = number
        self.item = item
        self.session = session
        self.started = time.monotonic()
        self.wrote = False
        self.chapters_written: set = set()
        self.texts: Dict[int, str] = {}


class ExtensionProcess:
    """One switched-on extension's process, seen from the app (F25.11)."""

    def __init__(self, area: "ExtensionsArea", module):
        self.area = area
        self.module = module
        self.id = module.id
        self.process: Optional[subprocess.Popen] = None
        self.messages: "Queue[Optional[dict]]" = Queue()
        self.lock = threading.Lock()
        self.ready = False
        self.stopping = False
        self.command: Optional[Command] = None
        self.started = 0.0

    @property
    def manifest(self) -> dict:
        return self.module.manifest

    @property
    def needs(self) -> dict:
        return self.manifest.get("needs") or {}

    def _command_line(self) -> list:
        if getattr(sys, "frozen", False):  # an installed app (F10) runs its own host
            return [sys.executable, "--scriptorum-extension-host"]
        code = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from scriptorum.core.exthost import serve; serve()")
        return [sys.executable, "-c", code, str(_ROOT)]

    def start(self) -> None:
        store = self.area.store
        data = store.data_folder(self.id)
        log = open(data / "extension.log", "ab")  # noqa: SIM115 - kept open by the process
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        self.process = subprocess.Popen(
            self._command_line(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
            creationflags=flags, cwd=str(data))
        log.close()
        self.started = time.monotonic()
        threading.Thread(target=self._read, daemon=True).start()
        self.send({"type": "start", "id": self.id, "folder": str(self.module.path),
                   "main": self.manifest["main"], "data": str(data), "settings": self.area._plain_settings(self.module)})

    def _read(self) -> None:
        stream = self.process.stdout
        for raw in iter(stream.readline, b""):
            try:
                message = json.loads(raw.decode("utf-8"))
            except ValueError:
                continue
            if isinstance(message, dict):
                self.messages.put(message)
        self.messages.put(None)  # the process ended

    def send(self, message: dict) -> bool:
        if self.process is None or self.process.poll() is not None:
            return False
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
                return True
            except (BrokenPipeError, OSError, ValueError):
                return False

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self) -> None:
        self.stopping = True
        if self.process is None:
            return
        self.send({"type": "stop"})
        try:
            self.process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.process.kill()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass
        for stream in (self.process.stdin, self.process.stdout):
            try:
                stream.close()
            except (OSError, ValueError):
                pass


class ExtensionsArea:
    def __init__(self, api):
        self.api = api
        self.key: Optional[str] = None            # the tests stand in for the project's key
        self.keychain = None                      # the tests stand in for the computer's keychain
        self.time_limit = COMMAND_LIMIT
        self.processes: Dict[str, ExtensionProcess] = {}
        self.failures: Dict[str, int] = {}
        self.findings_shown: Dict[str, dict] = {}
        self.listeners: List[Callable[[dict], None]] = []
        self.notices: List[dict] = []             # the last notices, for the tests
        self._number = 0
        self._store = None
        self.suggestions: Dict[str, dict] = {}   # 0.7.5: open suggestions, by id
        self.pictures: Dict[str, dict] = {}      # 0.7.5: pictures waiting for Use, Regenerate or Cancel
        self.activity: Dict[str, float] = {}     # 0.7.5: when each extension last showed something
        api.events.subscribe(self._on_event)

    # --- helpers ------------------------------------------------------------------------------------
    @property
    def session(self):
        return self.api.session

    @property
    def store(self) -> ext_core.ExtensionStore:
        if self._store is None or (self.keychain is not None and self._store.keychain is not self.keychain):
            root = Path(self.api.sessions[0].app_settings.file).parent / "extensions"
            self._store = ext_core.ExtensionStore(root, self.keychain)
        return self._store

    def _t(self, key: str, **details) -> str:
        return self.session.t(key, **details)

    def _installed(self) -> List:
        return sorted(self.session.library.of_kind(ext_core.KIND), key=lambda m: m.name.lower())

    def _module(self, ext_id: str):
        return next((m for m in self._installed() if m.id == ext_id), None)

    def _notify(self, notice: dict) -> None:
        self.notices.append(notice)
        del self.notices[:-100]
        for listener in list(self.listeners):
            try:
                listener(dict(notice))
            except Exception:  # noqa: BLE001 - one listener never stops another
                pass

    def _refusal(self, exc: Exception) -> dict:
        if isinstance(exc, Refused):
            return {"ok": False, "error": self._t(exc.key, **exc.details), "key": exc.key}
        return self.api.error(exc)

    def _plain_settings(self, module) -> dict:
        """Its settings without the secrets, which never leave the app (F25.18)."""
        state = self.store.state(module.id)["settings"]
        out = {}
        for item in module.manifest.get("settings", []):
            if item.get("kind", "text") != "secret":
                out[item["id"]] = state.get(item["id"], item.get("default", ""))
        return out

    # --- the list (F25.10) --------------------------------------------------------------------------
    def list(self) -> dict:
        blocked = self.api.app.connections_blocked()
        return {"ok": True, "blocked": blocked, "keychain": self.store.keychain_used(),
                "extensions": [ext_core.module_info(m, self.store, self._t, self.key, blocked) for m in self._installed()]}

    def contributions(self) -> list:
        """The menu items, block actions and panels of the switched-on extensions (F25.17)."""
        out = []
        for module in self._installed():
            if not self.store.state(module.id)["on"]:
                continue
            info = ext_core.module_info(module, self.store, self._t, self.key)
            out.append({"id": module.id, "name": module.name, "menu": info["menu"],
                        "blockActions": info["blockActions"], "panels": info["panels"]})
        return out

    # --- installing (F25.4 to F25.9) ----------------------------------------------------------------
    def inspect(self, path: str) -> dict:
        """What a .scmod file is, and for an extension what it needs, before
        anything is installed. Nothing is written to the library."""
        library = self.session.library
        tmp = Path(tempfile.mkdtemp(prefix=".inspect-", dir=library.root))
        try:
            try:
                unpack_scmod(Path(path), tmp)
            except (OSError, ValueError) as exc:
                raise ModuleError("error.module.notModule", path=str(path)) from exc
            except Exception as exc:  # noqa: BLE001 - a zip that is not a module
                if isinstance(exc, ModuleError):
                    raise
                raise ModuleError("error.module.notModule", path=str(path)) from exc
            manifest = validate_folder(tmp)
            if manifest["kind"] != ext_core.KIND:
                return {"ok": True, "extension": False}
            ext_core.check_manifest(manifest, tmp)
            tokens = ext_core.need_tokens(manifest)
            installed = self._module(manifest["id"])
            if installed is None:
                added = tokens
            else:
                agreed = self.store.state(installed.id)["agreed"] or ext_core.need_tokens(installed.manifest)
                added = ext_core.added_needs(agreed, tokens)
            return {
                "ok": True, "extension": True, "id": manifest["id"], "name": manifest["name"],
                "version": manifest["version"], "description": manifest.get("description", ""),
                "authors": manifest.get("authors", []), "licence": manifest.get("licence", ""),
                "verified": ext_core.verified(tmp, manifest, self.key),
                "needs": ext_core.need_texts(manifest, self._t),
                "added": ext_core.need_texts(manifest, self._t, added) if installed is not None else [],
                "installedVersion": installed.version if installed is not None else None,
                "askConsent": installed is None or bool(added),
            }
        except Exception as exc:  # noqa: BLE001 - refused, with the reason in plain words
            return self._refusal(exc)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def install(self, path: str, agreed: bool = False) -> dict:
        """Install an extension the author agreed to (F25.5). A newer version
        replaces the older one; the author's state and settings are kept."""
        info = self.inspect(path)
        if not info.get("ok"):
            return info
        if not info.get("extension"):
            return self.api.modules.install(path)
        if info["askConsent"] and not agreed:
            return self._refusal(Refused("error.ext.notAgreed", name=info["name"]))
        library = self.session.library
        try:
            result = modmanager.install(library, Path(path), self.session.localize)
        except Exception as exc:  # noqa: BLE001
            return self._refusal(exc)
        module = result["module"]
        for old in [m for m in library.installed(True) if m.id == module.id and m.version != module.version]:
            library.remove(old.id, old.version)
        self.store.agree(module.id, ext_core.need_tokens(module.manifest))
        running = self.processes.pop(module.id, None)
        if running is not None:
            running.stop()
        self.api.emit("modules.changed", rebuild=False)
        reply = self.list()
        reply.update({"status": result["status"], "installed": {"id": module.id, "name": module.name,
                                                                "version": module.version}})
        return reply

    # --- on and off, settings, removal (F25.10, F25.18) ----------------------------------------------
    def set_on(self, ext_id: str, on: bool) -> dict:
        module = self._module(ext_id)
        if module is None:
            return self._refusal(Refused("error.ext.notInstalled", id=ext_id))
        self.store.set_on(ext_id, bool(on))
        if on:
            self.failures.pop(ext_id, None)   # switched on by hand: a fresh start
            self._ensure(module)
        else:
            self._stop(ext_id)
            self._forget_shown(ext_id)
        return self.list()

    def set_setting(self, ext_id: str, key: str, value: str) -> dict:
        module = self._module(ext_id)
        item = next((s for s in (module.manifest.get("settings", []) if module else []) if s.get("id") == key), None)
        if item is None:
            return self._refusal(Refused("error.ext.notInstalled", id=ext_id))
        if item.get("kind") == "secret":
            self.store.set_secret(ext_id, key, str(value or ""))
        else:
            if item.get("kind") == "choice" and value not in [str(o) for o in item.get("options", [])]:
                return self._refusal(Refused("error.ext.badValue", label=item["label"]))
            self.store.set_setting(ext_id, key, str(value or ""))
            proc = self.processes.get(ext_id)
            if proc is not None and proc.alive():
                proc.send({"type": "settings", "settings": self._plain_settings(module)})
        return self.list()

    def remove(self, ext_id: str) -> dict:
        """Removing an extension removes everything it stored (F25.18)."""
        self._stop(ext_id)
        library = self.session.library
        modules = [m for m in library.installed(True) if m.id == ext_id and m.kind == ext_core.KIND]
        if not modules:
            return self._refusal(Refused("error.ext.notInstalled", id=ext_id))
        try:
            for module in modules:
                library.remove(module.id, module.version)
        except Exception as exc:  # noqa: BLE001
            return self._refusal(exc)
        self.store.forget(ext_id)
        self.failures.pop(ext_id, None)
        self.findings_shown = {k: v for k, v in self.findings_shown.items() if v.get("id") != ext_id}
        self._forget_shown(ext_id)
        self.api.emit("modules.changed", rebuild=False)
        return self.list()

    # --- running (F25.11 to F25.16) ------------------------------------------------------------------
    def _ensure(self, module) -> ExtensionProcess:
        proc = self.processes.get(module.id)
        if proc is None or not proc.alive():
            proc = ExtensionProcess(self, module)
            self.processes[module.id] = proc
            proc.start()
        return proc

    def _stop(self, ext_id: str) -> None:
        proc = self.processes.pop(ext_id, None)
        if proc is not None:
            proc.stop()

    def stop_all(self) -> None:
        for ext_id in list(self.processes):
            self._stop(ext_id)

    def running(self) -> List[str]:
        return [ext_id for ext_id, proc in self.processes.items() if proc.alive()]

    def run(self, ext_id: str, command: str, context: Optional[dict] = None) -> dict:
        """The author clicked one of the extension's items: run it. The answer
        arrives later as a notice (``done``)."""
        module = self._module(ext_id)
        if module is None or not self.store.state(ext_id)["on"]:
            return self._refusal(Refused("error.ext.notOn", name=module.name if module else ext_id))
        items = [*module.manifest.get("menu", []), *module.manifest.get("block_actions", [])]
        item = next((i for i in items if i.get("id") == command), None)
        if item is None:
            return self._refusal(Refused("error.ext.unknownCommand", name=module.name, command=command))
        proc = self.processes.get(ext_id)
        if proc is not None and proc.command is not None:
            return self._refusal(Refused("error.ext.busy", name=module.name))
        proc = self._ensure(module)
        self._number += 1
        proc.command = Command(self._number, item, self.session)
        if self.session.adventure is not None:
            adventure = self.session.adventure
            proc.command.texts = {i: adventure.chapter_text(p) for i, p in enumerate(adventure.chapters)}
        context = dict(context or {})
        if self.session.adventure is not None:
            context.setdefault("readOnly", self.session.read_only)
        if not proc.send({"type": "command", "id": self._number, "command": command, "context": context}):
            proc.command = None
            self._failed(proc, "error.ext.crashed")
            return {"ok": False, "error": self._t("error.ext.crashed", name=module.name), "key": "error.ext.crashed"}
        return {"ok": True, "id": self._number}

    def findings(self) -> list:
        return list(self.findings_shown.values())

    def pump(self) -> None:
        """Handle what the running extensions sent, and notice a crash or a
        command that took too long. The bridge calls this on a timer, on the
        window's thread, so every call into the core happens there."""
        for proc in list(self.processes.values()):
            while True:
                try:
                    message = proc.messages.get_nowait()
                except Empty:
                    break
                if message is None:
                    if not proc.stopping:
                        self._failed(proc, "error.ext.crashed")
                    break
                self._handle(proc, message)
            if proc.command is not None and time.monotonic() - proc.command.started > self.time_limit \
                    and self.processes.get(proc.id) is proc:
                self._failed(proc, "error.ext.timeLimit", seconds=int(self.time_limit))

    def _failed(self, proc: ExtensionProcess, key: str, **details) -> None:
        """F25.14: say so plainly; the app keeps working. Three in one session
        switch the extension off."""
        name = proc.module.name
        command = proc.command
        proc.command = None
        if self.processes.get(proc.id) is proc:
            self.processes.pop(proc.id, None)
        proc.stop()
        count = self.failures.get(proc.id, 0) + 1
        self.failures[proc.id] = count
        notice = {"kind": "failed", "id": proc.id, "name": name, "message": self._t(key, name=name, **details)}
        if command is not None:
            notice.update(self._wrote(proc, command))
        self._notify(notice)
        if count >= CRASH_LIMIT:
            self.store.set_on(proc.id, False)
            self._notify({"kind": "switchedOff", "id": proc.id, "name": name,
                          "message": self._t("error.ext.switchedOff", name=name, count=count)})

    def _wrote(self, proc: ExtensionProcess, command: Command) -> dict:
        if not command.wrote:
            return {"wrote": False}
        return {"wrote": True, "undoName": f"{proc.module.name}: {command.item.get('label', '')}",
                "chapters": sorted(command.chapters_written)}

    def _handle(self, proc: ExtensionProcess, message: dict) -> None:
        kind = message.get("type")
        if kind == "ready":
            proc.ready = True
        elif kind == "failed":
            self._failed(proc, "error.ext.failedToStart", error=str(message.get("error", ""))[:300])
        elif kind == "busy":
            if proc.command is not None and message.get("id") == proc.command.number:
                proc.command.started = time.monotonic()
        elif kind == "findings":
            self._findings(proc, message)
        elif kind == "call":
            self._call(proc, message)
        elif kind == "done":
            command = proc.command
            if command is None or message.get("id") != command.number:
                return
            proc.command = None
            result = message.get("result") if isinstance(message.get("result"), dict) else {}
            notice = {"kind": "done", "id": proc.id, "name": proc.module.name, "command": command.item.get("id"),
                      "label": command.item.get("label", ""), "ok": bool(message.get("ok")),
                      "message": str(result.get("message", ""))[:MESSAGE_LIMIT] if message.get("ok")
                      else self._t("error.ext.commandFailed", name=proc.module.name,
                                   error=str(message.get("error", ""))[:300])}
            notice.update(self._wrote(proc, command))
            self._notify(notice)

    def _findings(self, proc: ExtensionProcess, message: dict) -> None:
        panel_id = message.get("panel")
        panel = next((p for p in proc.manifest.get("panels", []) if p.get("id") == panel_id), None)
        if panel is None or panel.get("type") != "findings":
            return
        items = []
        for item in (message.get("items") or [])[:500]:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                continue
            entry = {"text": item["text"][:500]}
            for key in ("chapter", "line"):
                if isinstance(item.get(key), int) and item[key] >= 0:
                    entry[key] = item[key]
            items.append(entry)
        shown = {"id": proc.id, "name": proc.module.name, "panel": panel_id,
                 "title": panel.get("title", panel.get("label", "")), "items": items}
        self.findings_shown[f"{proc.id}/{panel_id}"] = shown
        self.activity[proc.id] = time.time()
        self._notify({"kind": "findings", **shown})

    # --- the calls an extension makes (F25.13) -------------------------------------------------------
    def _reply(self, proc: ExtensionProcess, call_id, result=None, error: Optional[Exception] = None) -> None:
        if error is None:
            proc.send({"type": "reply", "id": call_id, "ok": True, "result": result})
            return
        if isinstance(error, Refused):
            text = self._t(error.key, **error.details)
        else:
            text = self.api.error(error).get("error", str(error))
        proc.send({"type": "reply", "id": call_id, "ok": False, "error": text})

    def _call(self, proc: ExtensionProcess, message: dict) -> None:
        call_id = message.get("id")
        op = message.get("op")
        args = message.get("args") if isinstance(message.get("args"), dict) else {}
        name = proc.module.name
        try:
            if op == "settings.get":
                return self._reply(proc, call_id, self._plain_settings(proc.module))
            if op == "net.request":
                return self._network(proc, call_id, args)
            if op == "adventure.set_chapter_text":
                return self._reply(proc, call_id, self._write(proc, args))
            if op in ("suggest.replace", "suggest.add"):
                return self._reply(proc, call_id, self._suggest(proc, op, args))
            if op == "picture.show":
                return self._reply(proc, call_id, self._picture(proc, args))
            need = READS.get(op)
            if need is None:
                raise Refused("error.ext.unknownOp", name=name, op=str(op))
            if need not in proc.needs.get("reads", []):
                raise Refused("error.ext.notDeclared", name=name, op=str(op))
            if self.session.adventure is None:
                raise Refused("error.ext.noAdventure", name=name)
            self._reply(proc, call_id, self._read(op, args))
        except Exception as exc:  # noqa: BLE001 - refused plainly, never a raw exception
            self._reply(proc, call_id, error=exc)

    def _read(self, op: str, args: dict):
        if op == "adventure.info":
            info = self.api.adventure.info()
            return {k: info[k] for k in ("title", "readOnly", "chapters", "gameSystem", "theme") if k in info}
        if op == "adventure.chapter":
            index = int(args.get("index", 0))
            chapter = self.session.chapter(index)
            return {"index": index, "text": chapter["text"], "outline": chapter.get("outline", [])}
        if op == "adventure.blocks":
            return {"index": int(args.get("index", 0)), "blocks": blocks_of(self.session, int(args.get("index", 0)))}
        if op == "codex.codex":
            return self.api.codex.codex()
        if op == "codex.entry":
            return self.api.codex.entry(str(args.get("entry_id", args.get("id", ""))))
        return self.api.adventure.settings()

    def _write(self, proc: ExtensionProcess, args: dict) -> dict:
        """F25.12: writes go straight into the adventure as one undo step,
        only while a command the author started runs."""
        name = proc.module.name
        if proc.needs.get("changes", "none") != "writes":
            raise Refused("error.ext.notDeclared", name=name, op="adventure.set_chapter_text")
        command = proc.command
        if command is None:
            raise Refused("error.ext.notAsked", name=name)
        session = command.session
        if session.adventure is None:
            raise Refused("error.ext.noAdventure", name=name)
        if session.read_only:
            raise Refused("error.scav.readOnly")
        index = args.get("index")
        text = args.get("text")
        chapters = session.adventure.chapters
        if not isinstance(index, int) or not 0 <= index < len(chapters) or not isinstance(text, str):
            raise Refused("error.ext.badCall", name=name, op="adventure.set_chapter_text")
        # The text as it was when the author asked (or as this command last
        # wrote it); anything else means the author changed it meanwhile.
        current = session.adventure.chapter_text(chapters[index])
        if current != command.texts.get(index):
            raise Refused("error.ext.textChanged", name=name)
        if not command.wrote:
            session._world_change()   # one undo step for everything this command writes
            command.wrote = True
        session.set_chapter_text(index, text)
        command.texts[index] = text
        command.chapters_written.add(index)
        self.api.emit("text.changed", tab=session.id)
        return {"ok": True}

    def _network(self, proc: ExtensionProcess, call_id, args: dict) -> None:
        """F25.16: through the gate, to a declared host only; the answer comes
        from a thread, so the window never waits for the network."""
        name = proc.module.name
        url = str(args.get("url", ""))
        if self.api.app.connections_blocked():
            raise Refused("error.ext.blocked", name=name)
        declared = ext_core.network_needs(proc.manifest)
        if not declared:
            raise Refused("error.ext.notDeclared", name=name, op="net.request")
        host = net.host_of(url)
        allowed = set()
        settings = self.store.state(proc.id)["settings"]
        for item in declared:
            if "host" in item:
                allowed.add(item["host"])
            else:
                allowed.add(net.host_of(str(settings.get(item["setting"], ""))))
        if not host or host not in allowed or not net.extension_address_ok(url):
            raise Refused("error.ext.hostRefused", name=name, host=host or url)

        def fill(value: str) -> str:
            return SECRET.sub(lambda m: self.store.secret(proc.id, m.group(1)) or "", value)

        headers = {str(k): fill(str(v)) for k, v in (args.get("headers") or {}).items()}
        body = args.get("body")
        data = fill(body).encode("utf-8") if isinstance(body, str) else None
        if data is None and isinstance(args.get("bodyBase64"), str):
            data = base64.b64decode(args["bodyBase64"])
        method = str(args.get("method", "GET"))
        gate = self.api.net

        def work():
            try:
                result = gate.request(url, method, headers, data)
                self._reply(proc, call_id, result)
            except net.ConnectionsBlocked:
                self._reply(proc, call_id, error=Refused("error.ext.blocked", name=name))
            except Exception as exc:  # noqa: BLE001 - unreachable, said plainly
                self._reply(proc, call_id, error=Refused("error.ext.network", name=name, error=str(exc)[:200]))

        threading.Thread(target=work, daemon=True).start()

    # --- events (F25.15) -----------------------------------------------------------------------------
    def _on_event(self, name: str, details: dict) -> None:
        need = EVENT_NEEDS.get(name)
        if need is None:
            return
        for proc in list(self.processes.values()):
            if proc.alive() and need in proc.needs.get("reads", []):
                proc.send({"type": "event", "name": name, "details": details})


# --- suggestions and pictures (F25, decided 19 November 2026, 0.7.5) ------------------------------

def _walk(doc: dict, path: list, out: list) -> None:
    from scriptorum.core import source
    for i, block in enumerate(doc.get("blocks", [])):
        here = path + [i]
        kind = block.get("kind") if block.get("type") == "element" else block.get("type")
        text = ""
        if isinstance(block.get("text"), (str, list)):
            try:
                text = source.inline_to_plain(block["text"])
            except Exception:  # noqa: BLE001
                text = ""
        out.append({"path": here, "kind": kind, "line": block.get("line"), "source": block.get("raw", ""),
                    "text": text})
        if isinstance(block.get("body"), dict):
            _walk(block["body"], here, out)


def blocks_of(session, index: int) -> list:
    """Every block of a chapter, nested ones too, with its path, kind, line
    and exact source text, for an extension that reads the text."""
    from scriptorum.core import source
    text = session.chapter(index)["text"]
    out: list = []
    _walk(source.parse(text, session.kinds()), [], out)
    return out


def _find(session, index: int, path: list):
    """The block at ``path`` and where its source starts in the chapter's text."""
    from scriptorum.core import source
    chapters = session.adventure.chapters
    if not isinstance(index, int) or not 0 <= index < len(chapters) or not isinstance(path, list) or not path:
        return None
    text = session.adventure.chapter_text(chapters[index])
    doc = source.parse(text, session.kinds())
    block = None
    for step in path:
        blocks = (doc or {}).get("blocks", []) if block is None else (block.get("body") or {}).get("blocks", [])
        if not isinstance(step, int) or not 0 <= step < len(blocks):
            return None
        block = blocks[step]
        doc = None
    raw = block.get("raw", "")
    line_start = 0
    for _ in range(int(block.get("line", 1)) - 1):
        line_start = text.index("\n", line_start) + 1
    position = text.find(raw, line_start)
    if position < 0 or text.count("\n", line_start, position) > 0:
        return None
    return text, block, position


def _word_changes(old: str, new: str) -> list:
    """The new text in pieces, each marked changed or not, for the window."""
    import difflib
    a, b = old.split(" "), new.split(" ")
    pieces = []
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if j2 > j1:
            pieces.append({"text": " ".join(b[j1:j2]), "changed": tag != "equal"})
    return pieces


def _suggest(self, proc, op: str, args: dict) -> dict:
    from scriptorum.core import source
    name = proc.module.name
    if proc.needs.get("changes", "none") not in ("suggests", "writes"):
        raise Refused("error.ext.notDeclared", name=name, op=op)
    session = self.session
    if session.adventure is None:
        raise Refused("error.ext.noAdventure", name=name)
    index, path, new = args.get("chapter", 0), args.get("path"), args.get("source")
    found = _find(session, index, path)
    if found is None or not isinstance(new, str) or not new.strip():
        raise Refused("error.ext.badCall", name=name, op=op)
    parsed = source.parse(new.strip("\n"), session.kinds())
    if not parsed["blocks"] or any(b.get("type") == "locked" for b in parsed["blocks"]):
        raise Refused("error.ext.badSource", name=name)
    _text, block, _position = found
    self._number += 1
    suggestion_id = f"s{self._number}"
    old_plain = " ".join(b["text"] for b in [*_flat(block)] if b["text"]) or block.get("raw", "")
    new_plain = " ".join(x["text"] for x in _flat_doc(parsed) if x["text"]) or new
    suggestion = {
        "id": suggestion_id, "ext": proc.id, "name": name, "tab": session.id, "chapter": index, "path": path,
        "kind": "replace" if op == "suggest.replace" else "add", "original": block.get("raw", ""),
        "line": block.get("line"), "source": new.strip("\n"), "label": str(args.get("label", ""))[:200],
        "old": old_plain, "pieces": _word_changes(old_plain, new_plain) if op == "suggest.replace"
        else [{"text": new_plain, "changed": True}],
    }
    self.suggestions[suggestion_id] = suggestion
    self.activity[proc.id] = time.time()
    self._notify({"kind": "suggestion", "suggestion": suggestion})
    return {"id": suggestion_id}


def _flat(block: dict) -> list:
    out: list = []
    _walk({"blocks": [block]}, [], out)
    return out


def _flat_doc(doc: dict) -> list:
    out: list = []
    _walk(doc, [], out)
    return out


def _forget_shown(self, ext_id: str) -> None:
    for store in (self.suggestions, self.pictures):
        for key in [k for k, v in store.items() if v["ext"] == ext_id]:
            store.pop(key)
    self.activity.pop(ext_id, None)


def suggestions_open(self) -> list:
    """The open suggestions, for the editor and the Extensions tab."""
    return list(self.suggestions.values())


def _apply(self, session, index: int, path: list, original: str, change) -> None:
    """Splice one block's source: everything else stays byte-identical. The
    change is one undo step (F25.12, F4.12)."""
    if session.read_only:
        raise Refused("error.scav.readOnly")
    found = _find(session, index, path)
    if found is None or found[1].get("raw", "") != original:
        raise Refused("error.ext.suggestionStale")
    text, block, position = found
    end = position + len(original)
    updated = change(text, block, position, end)
    session._world_change()
    session.set_chapter_text(index, updated)
    self.api.emit("text.changed", tab=session.id)


def accept_suggestion(self, suggestion_id: str) -> dict:
    s = self.suggestions.get(suggestion_id)
    if s is None:
        return self._refusal(Refused("error.ext.noSuggestion"))
    session = next((x for x in self.api.sessions if x.id == s["tab"]), None)
    if session is None or session.adventure is None:
        return self._refusal(Refused("error.ext.suggestionStale"))

    def change(text, block, position, end):
        if s["kind"] == "replace":
            return text[:position] + s["source"] + text[end:]
        sep = block.get("sep") or "\n\n"
        if "\n" not in sep:
            sep = "\n\n"
        return text[:end] + sep + s["source"] + text[end:]
    try:
        self._apply(session, s["chapter"], s["path"], s["original"], change)
    except Refused as exc:
        return self._refusal(exc)
    self.suggestions.pop(suggestion_id, None)
    # The other suggestions of that chapter may now point at moved blocks.
    for other in list(self.suggestions.values()):
        if other["tab"] == s["tab"] and other["chapter"] == s["chapter"]:
            self._repath(session, other)
    return {"ok": True, "undoName": f"{s['name']}: {s['label'] or self._t('ext.suggestionLabel')}"}


def _repath(self, session, s: dict) -> None:
    """Find a suggestion's block again by its source after another change."""
    for item in blocks_of(session, s["chapter"]):
        if item["source"] == s["original"]:
            s["path"], s["line"] = item["path"], item["line"]
            return


def reject_suggestion(self, suggestion_id: str) -> dict:
    self.suggestions.pop(suggestion_id, None)
    return {"ok": True}


def _picture(self, proc, args: dict) -> dict:
    import base64 as b64
    from scriptorum.core import world as world_mod
    name = proc.module.name
    try:
        data = b64.b64decode(str(args.get("base64", "")), validate=True)
    except ValueError:
        data = b""
    size = world_mod.image_size(data) if data else None
    if size is None or size[0] not in ("png", "jpeg", "jpg"):
        raise Refused("error.ext.notPicture", name=name)
    command = proc.command
    self._number += 1
    picture_id = f"p{self._number}"
    context = dict(args.get("context") or {})
    picture = {
        "id": picture_id, "ext": proc.id, "name": name, "tab": self.session.id if self.session.adventure else "",
        "chapter": args.get("chapter"), "path": args.get("path"), "description": str(args.get("description", ""))[:1000],
        "format": "png" if size[0] == "png" else "jpg", "width": size[1], "height": size[2],
        "base64": b64.b64encode(data).decode("ascii"), "command": command.item.get("id") if command else args.get("command"),
        "context": context, "blockKind": None,
    }
    session = self.session
    if session.adventure is not None and isinstance(picture["chapter"], int) and isinstance(picture["path"], list):
        found = _find(session, picture["chapter"], picture["path"])
        if found is not None:
            block = found[1]
            picture["blockKind"] = block.get("kind") if block.get("type") == "element" else block.get("type")
            picture["original"] = block.get("raw", "")
    self.pictures[picture_id] = picture
    self.activity[proc.id] = time.time()
    self._notify({"kind": "picture", "picture": {k: v for k, v in picture.items() if k != "original"}})
    return {"id": picture_id}


def pictures_waiting(self) -> list:
    return [{k: v for k, v in p.items() if k != "original"} for p in self.pictures.values()]


def use_picture(self, picture_id: str, as_portrait: bool = False) -> dict:
    """Use: the picture goes into the adventure's images (F4.6) and an image
    block with its description (F17.3) after the block it was made for;
    from a person card, Set as portrait (11.4). One undo step."""
    import base64 as b64
    from scriptorum.core import source
    p = self.pictures.get(picture_id)
    if p is None:
        return self._refusal(Refused("error.ext.noPicture"))
    session = next((x for x in self.api.sessions if x.id == p["tab"]), None)
    if session is None or session.adventure is None or session.read_only:
        return self._refusal(Refused("error.scav.readOnly") if session and session.read_only
                             else Refused("error.ext.noAdventure", name=p["name"]))
    data = b64.b64decode(p["base64"])
    file_name = f"{p['ext'].split('.')[-1]}-{picture_id}.{p['format']}"
    try:
        if as_portrait:
            if p.get("blockKind") not in ("person", "card"):
                return self._refusal(Refused("error.ext.notPortrait"))
            found = _find(session, p["chapter"], p["path"])
            if found is None or found[1].get("raw", "") != p.get("original"):
                raise Refused("error.ext.suggestionStale")
            block = found[1]
            fields = block.get("fields") or {}
            if block.get("kind") == "card":
                stored = session.add_portrait(file_name, data)
                session.update_entry(fields.get("entry", ""), {"fields": {
                    "portrait": stored, "portrait-description": p["description"]}})
                self.api.emit("codex.changed", tab=session.id)
            else:
                stored = session.add_portrait(file_name, data)

                def change(text, blk, position, end):
                    updated = dict(blk)
                    updated["fields"] = {**(blk.get("fields") or {}), "portrait": stored,
                                         "portrait-description": p["description"]}
                    updated.pop("raw", None)
                    updated.pop("head_raw", None)   # the head is written again with the new fields
                    return text[:position] + source.block_text(updated, session.kinds()) + text[end:]
                self._apply(session, p["chapter"], p["path"], p["original"], change)
        else:
            stored = session.add_image(file_name, data)
            image = "#image(" + source.quote_string(stored) + ", alt: " + source.quote_string(p["description"]) + ")"
            found = _find(session, p["chapter"], p["path"]) if isinstance(p.get("path"), list) else None
            if found is not None and found[1].get("raw", "") == p.get("original"):
                def change(text, blk, position, end):
                    sep = blk.get("sep") or "\n\n"
                    if "\n" not in sep:
                        sep = "\n\n"
                    return text[:end] + sep + image + text[end:]
                self._apply(session, p["chapter"], p["path"], p["original"], change)
            else:
                index = p["chapter"] if isinstance(p.get("chapter"), int) else 0
                text = session.adventure.chapter_text(session.adventure.chapters[index])
                session._world_change()
                session.set_chapter_text(index, text.rstrip("\n") + "\n\n" + image + "\n")
                self.api.emit("text.changed", tab=session.id)
    except Refused as exc:
        return self._refusal(exc)
    except Exception as exc:  # noqa: BLE001 - refused plainly (not JPEG or PNG, a read-only adventure)
        return self.api.error(exc)
    self.pictures.pop(picture_id, None)
    return {"ok": True, "portrait": bool(as_portrait), "undoName": f"{p['name']}: {self._t('ext.pictureLabel')}"}


def regenerate_picture(self, picture_id: str) -> dict:
    """Regenerate: the extension is asked again, with the same command."""
    p = self.pictures.pop(picture_id, None)
    if p is None or not p.get("command"):
        return self._refusal(Refused("error.ext.noPicture"))
    context = {**p.get("context", {}), "regenerate": True, "chapter": p.get("chapter"), "path": p.get("path")}
    return self.run(p["ext"], p["command"], context)


def cancel_picture(self, picture_id: str) -> dict:
    self.pictures.pop(picture_id, None)
    return {"ok": True}


def tab_info(self) -> dict:
    """The Extensions tab in the left pane: one section per switched-on
    extension, most recently active first, with its findings, pictures,
    open suggestions and settings (F25, 0.7.5)."""
    rows = self.list()
    sections = []
    for info in rows["extensions"]:
        if not info["on"]:
            continue
        ext_id = info["id"]
        sections.append({
            "id": ext_id, "name": info["name"], "settings": info["settings"], "keychain": rows["keychain"],
            "findings": [f for f in self.findings_shown.values() if f["id"] == ext_id],
            "pictures": [p for p in self.pictures_waiting() if p["ext"] == ext_id],
            "suggestions": [s for s in self.suggestions.values() if s["ext"] == ext_id],
            "active": self.activity.get(ext_id, 0.0),
        })
    sections.sort(key=lambda s: -s["active"])
    return {"ok": True, "show": bool(sections), "sections": sections}


for _f in (_suggest, _forget_shown, suggestions_open, _apply, accept_suggestion, _repath, reject_suggestion,
           _picture, pictures_waiting, use_picture, regenerate_picture, cancel_picture, tab_info):
    setattr(ExtensionsArea, _f.__name__, _f)
