"""The internal Scriptorum API (design document F23, 0.7.0 step 1, issue #29).

One defined, versioned and documented layer between the core
(``scriptorum/core``) and everything that uses it. The app's own interface
uses it through the bridge (``app/bridge.py``); extension modules (#27) will
use the same operations. Every operation takes and returns plain JSON-safe
data. ``docs/API.md`` describes each operation and event.

    api = Api(session)
    api.adventure.open("/path/to/adventure.scav")
    api.adventure.chapter(0)

The version follows 9.2's rule: a change that breaks a caller raises the
major number, an addition the minor number. ``surface()`` lists every
operation and event with its inputs; a test compares it with the stored
surface of this version (T-API-01).
"""

from __future__ import annotations

import inspect
from typing import Dict

from scriptorum.api.errors import ApiError
from scriptorum.api.events import EVENTS
from scriptorum.api.workspace import API_VERSION, Api

AREAS = ("app", "adventure", "codex", "build", "modules")

__all__ = ["API_VERSION", "AREAS", "Api", "ApiError", "EVENTS", "surface"]


def _area_classes() -> Dict[str, type]:
    from scriptorum.api.adventure import AdventureArea
    from scriptorum.api.app import AppArea
    from scriptorum.api.build import BuildArea
    from scriptorum.api.codex import CodexArea
    from scriptorum.api.modules import ModulesArea

    return {"app": AppArea, "adventure": AdventureArea, "codex": CodexArea, "build": BuildArea,
            "modules": ModulesArea}


def surface() -> dict:
    """The API's public surface: every operation (area.name with its inputs)
    and every event with its details."""
    operations = {}
    for area, cls in _area_classes().items():
        for name, member in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                continue
            params = [p for p in inspect.signature(member).parameters if p != "self"]
            operations[f"{area}.{name}"] = params
    return {"version": API_VERSION, "operations": dict(sorted(operations.items())),
            "events": {name: list(details) for name, details in sorted(EVENTS.items())}}
