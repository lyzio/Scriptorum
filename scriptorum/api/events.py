"""Events of the internal API (design document F23.3, 0.7.0 step 1).

The API announces what happened, with plain JSON-safe details. Anything may
subscribe: today the bridge, later extension processes (#27). A subscriber
that fails is left out of that event; it never stops the operation.
"""

from __future__ import annotations

from typing import Callable, Dict, List

# Every event the API announces, with the details it carries (API 1.0).
EVENTS: Dict[str, List[str]] = {
    "adventure.opened": ["tab", "title", "readOnly"],   # a new or opened adventure, or a tab switched to
    "adventure.closed": ["tab"],
    "adventure.saved": ["tab", "path"],
    "adventure.edited": ["tab"],          # images, portraits or fonts added: nothing to rebuild
    "text.changed": ["tab"],              # the text, its settings or its theme changed: rebuild
    "codex.changed": ["tab"],             # a codex entry, type, map or the chart changed: rebuild
    "settings.changed": ["what"],         # "app": the app settings (F18)
    "modules.changed": ["rebuild"],       # a module was installed, enabled, disabled or removed
    "build.finished": ["tab", "ok", "pages", "errors", "warnings"],
}


class EventBus:
    def __init__(self):
        self._subscribers: List[Callable[[str, dict], None]] = []
        self.sent: List[tuple] = []   # the last events, for the tests (newest last)

    def subscribe(self, handler: Callable[[str, dict], None]) -> Callable[[], None]:
        """Hear every event; returns a function that stops listening."""
        self._subscribers.append(handler)
        return lambda: self._subscribers.remove(handler) if handler in self._subscribers else None

    def emit(self, name: str, **details) -> None:
        if name not in EVENTS:
            raise ValueError(f"not an API event: {name}")
        self.sent.append((name, details))
        del self.sent[:-200]
        for handler in list(self._subscribers):
            try:
                handler(name, dict(details))
            except Exception:  # noqa: BLE001 - one listener never stops another
                pass
