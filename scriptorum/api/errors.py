"""Errors of the internal API (design document F23.2, 0.7.0 step 1).

An operation that cannot do what it was asked returns a plain error: a
reply ``{"ok": False, "error": <text>, "key": <key>}``, where the text comes
from the interface-language module (F15). It never lets a raw exception
through. An unexpected error is written to the crash log in the app's own
folder (F2.11) and returned as a plain error too.
"""

from __future__ import annotations

from typing import Optional

from scriptorum.core.fonts import FontRefused
from scriptorum.core.modules import ModuleError
from scriptorum.core.scav import ScavError
from scriptorum.core.world import WorldError

# The core's own refusals, each with a key and its details (F15).
KNOWN = (ScavError, ModuleError, FontRefused, WorldError)


class ApiError(Exception):
    """A refusal raised inside the API: a key from the language module and
    the details its text needs."""

    def __init__(self, key: str, **details):
        super().__init__(key)
        self.key = key
        self.details = details


def places_text(session, places: list) -> str:
    """F3.8: where an entry is used, in words."""
    t = session.t
    parts = []
    for p in places:
        if p["where"] == "text":
            parts.append(t("codex.usedInScene", scene=p["scene"], line=p["line"]) if p.get("scene")
                         else t("codex.usedAtLine", line=p["line"]))
        elif p["where"] == "entry":
            parts.append(t("codex.usedInEntry", title=p["title"]))
        else:
            parts.append(t("codex.usedInMap", title=p["title"]))
    return "; ".join(parts)


def error_reply(session, exc: Exception) -> dict:
    """The plain error for a refusal (F23.2)."""
    key = getattr(exc, "key", "")
    if isinstance(exc, WorldError) and exc.key == "error.codex.inUse":
        # F3.8: the refusal lists the places that use the entry.
        text = session.t(exc.key, places=places_text(session, exc.details.get("places", [])))
    elif isinstance(exc, KNOWN + (ApiError,)):
        text = session.t(exc.key, **exc.details)
    else:
        text = str(exc)
    reply = {"ok": False, "error": text}
    if key:
        reply["key"] = key
    return reply


def unexpected_reply(session, exc: Exception, folder: Optional[str] = None,
                     key: str = "error.codex.failed") -> dict:
    """An unexpected error: its details go to the crash log in the app's own
    folder (F2.11); the reply says so plainly. Nothing is sent anywhere."""
    from scriptorum.core.crashlog import write_crash_log

    try:
        log = str(write_crash_log(type(exc), exc, exc.__traceback__, folder))
    except OSError:
        log = None
    return {"ok": False, "error": session.t(key), "key": key, "logged": log is not None, "log": log}
