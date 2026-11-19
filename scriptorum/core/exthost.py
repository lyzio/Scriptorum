"""The extension host: one switched-on extension in a process of its own (design document F25.11, 0.7.4).

The app starts its own program in extension-host mode (``--scriptorum-
extension-host`` for an installed app, ``serve()`` from source) and talks to
it with one JSON message per line on the process's standard input and
output. The extension's code never runs in the app's process, so a crash or
a hang cannot freeze or break the app (F25.14).

The app sends:
    {"type": "start", "folder", "main", "id", "data", "settings"}
    {"type": "command", "id": n, "command": "<item id>", "context": {…}}
    {"type": "event", "name": "text.changed", "details": {…}}
    {"type": "reply", "id": n, "ok": true, "result": …} | {… "ok": false, "error": "…"}
    {"type": "stop"}
The host sends:
    {"type": "ready"} | {"type": "failed", "error": "…"}
    {"type": "call", "id": n, "op": "adventure.chapter", "args": {…}}
    {"type": "findings", "panel": "<id>", "items": [{"text", "chapter", "line"}]}
    {"type": "busy", "id": n}               still working on command n (resets its time limit)
    {"type": "done", "id": n, "ok": true, "result": {"message": "…"}}

An extension's ``main`` file has a ``setup(ext)`` function:

    def setup(ext):
        @ext.command("check")
        def check(context):
            info = ext.call("adventure.info")
            ext.findings("findings", [{"text": "…", "chapter": 0, "line": 3}])
            return {"message": "Checked."}

The extension may use Python's standard library and the pure-Python
libraries it bundles in its own folder (F25.4).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Callable, Dict, List


class CallRefused(Exception):
    """The app refused a call: an operation the extension's needs do not
    cover, or one that could not be done. ``str()`` is the app's plain message."""


class Extension:
    """What the extension's code gets: ``ext``."""

    def __init__(self, channel: "Channel", start: dict):
        self._channel = channel
        self.id = start.get("id", "")
        self.data_folder = Path(start.get("data", "."))
        self.settings: Dict[str, str] = dict(start.get("settings") or {})
        self.commands: Dict[str, Callable] = {}
        self.listeners: Dict[str, List[Callable]] = {}
        self._command_id = None

    def command(self, name: str):
        """Register what one menu item, block action or panel button does."""
        def register(function):
            self.commands[name] = function
            return function
        return register

    def on(self, event: str):
        """Hear an API event that the extension's needs cover (F25.15)."""
        def register(function):
            self.listeners.setdefault(event, []).append(function)
            return function
        return register

    def call(self, op: str, **args):
        """One operation of the internal API, checked against the needs (F25.13)."""
        return self._channel.call(op, args)

    def request(self, url: str, method: str = "GET", headers: dict = None, body: str = None) -> dict:
        """A network request through the app's gate (F25.16). ``{secret:<id>}``
        in a header or the body is replaced by the app with that secret, so
        the secret never enters this process."""
        return self.call("net.request", url=url, method=method, headers=headers or {}, body=body)

    def blocks(self, chapter: int = 0) -> list:
        """Every block of a chapter (nested ones too) with its path, kind,
        line and exact source text (needs reads text)."""
        return self.call("adventure.blocks", index=chapter)["blocks"]

    def suggest_replace(self, chapter: int, path: list, source: str, label: str = "") -> str:
        """Suggest a new source for a whole block; the author accepts or
        rejects it (needs changes suggests or writes, 0.7.5)."""
        return self.call("suggest.replace", chapter=chapter, path=path, source=source, label=label)["id"]

    def suggest_add(self, chapter: int, path: list, source: str, label: str = "") -> str:
        """Suggest a new block after the block at ``path``."""
        return self.call("suggest.add", chapter=chapter, path=path, source=source, label=label)["id"]

    def picture(self, data: bytes, description: str, chapter: int = None, path: list = None) -> str:
        """Show a PNG or JPEG picture for the author to Use, Regenerate or
        Cancel; ``chapter`` and ``path`` name the block it is for."""
        import base64
        return self.call("picture.show", base64=base64.b64encode(data).decode("ascii"), description=description,
                         chapter=chapter, path=path)["id"]

    def findings(self, panel: str, items: list) -> None:
        """Show findings in a findings-list panel (F25.17)."""
        self._channel.send({"type": "findings", "panel": panel, "items": list(items)})

    def busy(self) -> None:
        """Still working: tells the app not to give up on the current command."""
        if self._command_id is not None:
            self._channel.send({"type": "busy", "id": self._command_id})


class Channel:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.next_id = 0
        self.queue: List[dict] = []   # messages that arrived while waiting for a reply

    def send(self, message: dict) -> None:
        self.writer.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.writer.flush()

    def receive(self):
        line = self.reader.readline()
        if not line:
            return None
        try:
            return json.loads(line)
        except ValueError:
            return {}

    def call(self, op: str, args: dict):
        self.next_id += 1
        call_id = f"c{self.next_id}"
        self.send({"type": "call", "id": call_id, "op": op, "args": args})
        while True:
            message = self.receive()
            if message is None:
                raise SystemExit(0)
            if message.get("type") == "reply" and message.get("id") == call_id:
                if message.get("ok"):
                    return message.get("result")
                raise CallRefused(message.get("error") or "refused")
            if message.get("type") == "stop":
                raise SystemExit(0)
            self.queue.append(message)


def _load(start: dict, extension: Extension) -> None:
    folder = Path(start["folder"])
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("scriptorum_extension", folder / start["main"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    setup = getattr(module, "setup", None)
    if not callable(setup):
        raise RuntimeError("the extension has no setup(ext) function")
    setup(extension)


def _error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]


def serve(reader=None, writer=None) -> None:
    """Run one extension until the app says stop or closes the pipe."""
    reader = reader or sys.stdin
    writer = writer or sys.stdout
    # The protocol owns standard output: anything the extension prints goes
    # to standard error, which the app keeps in the extension's log.
    if writer is sys.stdout:
        sys.stdout = sys.stderr
    channel = Channel(reader, writer)
    start = channel.receive()
    if not start or start.get("type") != "start":
        return
    extension = Extension(channel, start)
    try:
        _load(start, extension)
    except BaseException as exc:  # noqa: BLE001 - the app says so plainly
        traceback.print_exc()
        channel.send({"type": "failed", "error": _error_text(exc)})
        return
    channel.send({"type": "ready"})
    while True:
        message = channel.queue.pop(0) if channel.queue else channel.receive()
        if message is None or message.get("type") == "stop":
            return
        kind = message.get("type")
        if kind == "command":
            command_id = message.get("id")
            function = extension.commands.get(message.get("command", ""))
            extension._command_id = command_id
            try:
                if function is None:
                    raise RuntimeError(f"no command {message.get('command')!r}")
                result = function(dict(message.get("context") or {}))
                channel.send({"type": "done", "id": command_id, "ok": True, "result": result or {}})
            except CallRefused as exc:
                channel.send({"type": "done", "id": command_id, "ok": False, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - one failing command never stops the host
                traceback.print_exc()
                channel.send({"type": "done", "id": command_id, "ok": False, "error": _error_text(exc)})
            finally:
                extension._command_id = None
        elif kind == "event":
            for listener in extension.listeners.get(message.get("name", ""), []):
                try:
                    listener(dict(message.get("details") or {}))
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
        elif kind == "settings":
            extension.settings = dict(message.get("settings") or {})


if __name__ == "__main__":  # pragma: no cover
    serve()
