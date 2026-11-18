"""The internal API's entry point (design document F23, 0.7.0 step 1).

``Api`` holds the open adventures (one session per tab, F2.2), the events,
the network gate and the five areas of operations. Every operation takes
and returns plain JSON-safe data; refusals come back as plain errors
(``errors.py``). Nothing here needs Qt: the bridge (``app/bridge.py``) keeps
the dialogs, windows, timers and WebChannel signals and passes everything
else here.
"""

from __future__ import annotations

import time
from typing import List, Optional

from scriptorum.api.errors import error_reply, unexpected_reply
from scriptorum.api.events import EventBus
from scriptorum.api.net import NetworkGate
from scriptorum.core.session import Session

API_VERSION = "1.0"


class Api:
    VERSION = API_VERSION

    def __init__(self, session: Session, spelling=None, headless: bool = False):
        from scriptorum.api.adventure import AdventureArea
        from scriptorum.api.app import AppArea
        from scriptorum.api.build import BuildArea
        from scriptorum.api.codex import CodexArea
        from scriptorum.api.modules import ModulesArea

        self.sessions: List[Session] = [session]
        self.active = 0
        self.headless = headless
        self.crash_folder: Optional[str] = None   # tests point the crash log elsewhere
        self.events = EventBus()
        self.net = NetworkGate()
        self.app = AppArea(self, spelling)
        self.adventure = AdventureArea(self)
        self.codex = CodexArea(self)
        self.build = BuildArea(self)
        self.modules = ModulesArea(self)

    # --- the active tab -----------------------------------------------------------
    @property
    def session(self) -> Session:
        return self.sessions[self.active]

    def new_tab(self) -> Session:
        base = self.sessions[0].work_dir
        tab = self.session.sibling(base.parent / f"{base.name}-tab{len(self.sessions) + int(time.time() * 1000) % 100000}")
        self.sessions.append(tab)
        self.active = len(self.sessions) - 1
        return tab

    def tab_for_new_document(self) -> Session:
        """An empty tab is reused; otherwise a new tab opens (F2.2)."""
        if self.session.adventure is None:
            return self.session
        return self.new_tab()

    def drop_new_tab(self, reused: bool) -> None:
        """A new tab whose adventure could not be made or opened goes again."""
        if not reused:
            self.sessions.pop(self.active)
            self.active = len(self.sessions) - 1

    # --- replies ------------------------------------------------------------------
    def error(self, exc: Exception) -> dict:
        return error_reply(self.session, exc)

    def unexpected(self, exc: Exception, key: str = "error.codex.failed") -> dict:
        reply = unexpected_reply(self.session, exc, self.crash_folder, key)
        self.last_crash_log = reply.get("log")
        return reply

    def emit(self, name: str, **details) -> None:
        self.events.emit(name, **details)

    def tab_id(self) -> str:
        return self.session.id
