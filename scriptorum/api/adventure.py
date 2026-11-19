"""The API's adventure area (design document F23.1): tabs (F2.2), making,
opening and saving adventures (F1, F2), recovery and snapshots (F2.5–F2.8),
chapters and blocks (F4), the settings page (F7.3, F7.9), find and replace
(F4.7), images, portraits and fonts (F4.6, 11.4, F11).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

from scriptorum.api.errors import ApiError
from scriptorum.core.fonts import FontRefused
from scriptorum.core.modules import ModuleError
from scriptorum.core.scav import ScavError


class AdventureArea:
    def __init__(self, api):
        self.api = api

    @property
    def session(self):
        return self.api.session

    def _opened(self) -> None:
        tab = self.session
        self.api.emit("adventure.opened", tab=tab.id,
                      title=tab.adventure.title if tab.adventure else None, readOnly=tab.read_only)

    # --- what the interface shows -----------------------------------------------------
    def info(self) -> dict:
        return self.session.info()

    def editor_info(self) -> dict:
        return self.session.editor_info()

    def is_open(self) -> bool:
        """Whether the active tab holds an adventure."""
        return self.session.adventure is not None

    def unsaved(self, tab: str = "") -> bool:
        """Whether a tab (the active one by default) has unsaved changes."""
        session = next((s for s in self.api.sessions if s.id == tab), self.session)
        return session.adventure is not None and bool(session.dirty)

    def title(self) -> str:
        """The active adventure's title, or "Untitled adventure" (F15)."""
        adventure = self.session.adventure
        return (adventure.title if adventure else "") or self.session.t("app.untitled")

    # --- tabs (F2.2) -------------------------------------------------------------------
    def tabs(self) -> list:
        return [
            {"id": s.id, "title": s.adventure.title if s.adventure else None, "dirty": s.dirty,
             "readOnly": s.read_only, "active": i == self.api.active}
            for i, s in enumerate(self.api.sessions)
        ]

    def switch_tab(self, tab_id: str) -> dict:
        for index, tab in enumerate(self.api.sessions):
            if tab.id == tab_id:
                self.api.active = index
                self._opened()
                return {"ok": True}
        return {"ok": False}

    def close_active_tab(self) -> dict:
        """Close the active tab (the bridge asked about unsaved changes first);
        the tab before it becomes active, and a last tab is kept empty."""
        tab = self.session
        closing = self.api.active
        tab.close()
        if len(self.api.sessions) == 1:
            self.api.sessions[0] = tab.sibling(tab.work_dir)
            self.api.active = 0
        else:
            self.api.sessions.pop(closing)
        self.api.emit("adventure.closed", tab=tab.id)
        return {"ok": True, "closed": closing}

    def close_all(self) -> None:
        for tab in self.api.sessions:
            tab.close()

    # --- making, opening and saving (F1, F2) ------------------------------------------------
    def new(self, data: dict) -> dict:
        reuse = self.session.adventure is None
        tab = self.api.tab_for_new_document()
        try:
            tab.new(data["title"], data["gameSystem"]["id"], data["gameSystem"]["version"],
                    data["theme"]["id"], data["theme"]["version"])
        except (ScavError, ModuleError) as exc:
            self.api.drop_new_tab(reuse)
            return self.api.error(exc)
        self._opened()
        return {"ok": True}

    def open(self, path: str) -> dict:
        wanted = Path(path).resolve()
        for index, tab in enumerate(self.api.sessions):
            if tab.adventure is not None and tab.adventure.path is not None and Path(tab.adventure.path).resolve() == wanted:
                self.api.active = index  # already open in this window: show its tab
                self._opened()
                return {"ok": True, "switched": True}
        reuse = self.session.adventure is None
        tab = self.api.tab_for_new_document()
        try:
            tab.open(Path(path))
        except (ScavError, ModuleError) as exc:
            self.api.drop_new_tab(reuse)
            return self.api.error(exc)
        except OSError as exc:   # F23.2: a missing or unreadable file, said plainly
            self.api.drop_new_tab(reuse)
            return self.api.error(ApiError("error.scav.cannotRead", path=str(path), message=exc.strerror or str(exc)))
        self._opened()
        return {"ok": True, "readOnly": tab.read_only}

    def open_example(self) -> dict:
        """F20: the example adventure, as a copy in the user's documents."""
        tab = self.api.tab_for_new_document()
        try:
            path = tab.open_example()
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        tab.recent.add(path)
        self._opened()
        self.api.emit("text.changed", tab=tab.id)
        return {"ok": True, "path": str(path)}

    def needs_file_name(self) -> bool:
        """Save goes through Save as when the adventure has no file yet or is read-only."""
        adventure = self.session.adventure
        return adventure is not None and (adventure.path is None or self.session.read_only)

    def path(self) -> Optional[str]:
        adventure = self.session.adventure
        return str(adventure.path) if adventure is not None and adventure.path is not None else None

    def save_to(self, path: str, as_folder: Optional[bool] = None) -> dict:
        try:
            target = self.session.save(Path(path), as_folder=as_folder)
        except (ScavError, OSError) as exc:
            detail = self.session.t(exc.key, **exc.details) if isinstance(exc, ScavError) else str(exc)
            return {"ok": False, "error": self.session.t("error.save.failed", message=detail), "key": "error.save.failed"}
        self.api.emit("adventure.saved", tab=self.session.id, path=str(target))
        return {"ok": True, "path": str(target)}

    # --- work protection (F2.5–F2.8) ------------------------------------------------------
    def recoveries(self) -> list:
        return self.session.recovery.orphans()

    def restore_recovery(self, session_id: str) -> dict:
        meta = next((m for m in self.session.recovery.orphans() if m["session"] == session_id), None)
        if meta is None:
            return {"ok": False}
        tab = self.api.tab_for_new_document()
        tab.restore_recovery(meta)
        self._opened()
        return {"ok": True}

    def discard_recovery(self, session_id: str) -> dict:
        self.session.recovery.remove(session_id)
        return {"ok": True}

    def snapshot_tick(self) -> None:
        for tab in self.api.sessions:
            tab.maybe_snapshot()

    def snapshots(self) -> list:
        return self.session.snapshot_list()

    def revert_to(self, snapshot_id: str) -> dict:
        try:
            self.session.revert(snapshot_id)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        self.api.emit("text.changed", tab=self.session.id)
        return {"ok": True}

    # --- chapters (F4) ----------------------------------------------------------------------
    def chapter(self, index: int) -> dict:
        return self.session.chapter(index)

    def set_chapter_text(self, index: int, text: str) -> dict:
        reply = self.session.set_chapter_text(index, text)
        self.api.emit("text.changed", tab=self.session.id)
        return reply

    def set_chapter_doc(self, index: int, doc: dict) -> dict:
        reply = self.session.set_chapter_doc(index, doc)
        self.api.emit("text.changed", tab=self.session.id)
        return reply

    def block_source(self, block: dict) -> dict:
        """F4.1 Hybrid mode: the source of one block, as Source mode shows it."""
        from scriptorum.core import source
        return {"text": source.block_text(block, self.session.kinds())}

    # --- the settings page (F7.3, F7.9) and the theme (F8) ------------------------------------
    def settings(self) -> dict:
        return self.session.settings_info()

    def set_settings(self, data: dict) -> dict:
        reply = self.session.set_settings(data)
        self.api.emit("text.changed", tab=self.session.id)
        return reply

    def set_theme(self, theme_id: str) -> dict:
        """F8: the theme is chosen on the adventure settings page."""
        try:
            info = self.session.set_theme(theme_id)
        except ValueError as exc:
            return self.api.error(exc)
        self.api.emit("text.changed", tab=self.session.id)
        return info

    # --- find and replace (F4.7) -------------------------------------------------------------
    def find(self, query: str, match_case: bool = False) -> list:
        # F23.1: plain data only; the core gives some places as tuples.
        return json.loads(json.dumps(self.session.find(query, bool(match_case))))

    def replace_all(self, query: str, replacement: str, match_case: bool = False) -> dict:
        count = self.session.replace_all(query, replacement, bool(match_case))
        if count:
            self.api.emit("text.changed", tab=self.session.id)
        return {"ok": True, "count": count}

    # --- images, portraits and fonts (F4.6, 11.4, F11) ----------------------------------------
    def _edited(self) -> None:
        self.api.emit("adventure.edited", tab=self.session.id)

    def add_image(self, name: str, data_base64: str) -> dict:
        """An image dropped into the editor, as base64."""
        try:
            path = self.session.add_image(name, base64.b64decode(data_base64.split(",", 1)[-1]))
        except (ScavError, ValueError) as exc:
            return self.api.error(exc)
        self._edited()
        return {"ok": True, "path": path}

    def add_image_file(self, path: str) -> dict:
        try:
            stored = self.session.add_image(Path(path).name, Path(path).read_bytes())
        except (ScavError, OSError) as exc:
            return self.api.error(exc)
        self._edited()
        return {"ok": True, "path": stored}

    def add_portrait_file(self, path: str) -> dict:
        try:
            stored = self.session.add_portrait(Path(path).name, Path(path).read_bytes())
        except (ScavError, OSError) as exc:
            return self.api.error(exc)
        self._edited()
        return {"ok": True, "path": stored}

    def add_font_file(self, path: str) -> dict:
        try:
            result = self.session.add_font(Path(path))
        except FontRefused as exc:
            return self.api.error(exc)
        self._edited()
        return {"ok": True, **result}

    def fonts(self) -> list:
        return self.session.font_list()

    def image_file(self, path: str) -> Optional[str]:
        """A local copy of an adventure image for the editor to show; None
        when the adventure has no such file."""
        data = self.session.adventure.files.get(path.lstrip("/")) if self.session.adventure else None
        if data is None:
            return None
        folder = self.session.work_dir / "editor-images"
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / Path(path).name
        if not file.is_file() or file.read_bytes() != data:
            file.write_bytes(data)
        return str(file)

    def export_suggestion(self, kind: str = "adventure", variant: str = "") -> Optional[dict]:
        """The file name an export dialog suggests (F7.6): beside the
        adventure's file, or its title."""
        adventure = self.session.adventure
        if adventure is None:
            return None
        t = self.session.t
        base = adventure.path
        if kind == "adventure":
            return {"path": str(base.with_suffix(".pdf")) if base else (adventure.title or "adventure") + ".pdf"}
        suffix = t("export.handoutsSuffix") if kind == "handouts" else t(f"export.suffix.{variant}")
        name = (base.stem if base else (adventure.title or "adventure")) + " - " + suffix + ".pdf"
        return {"path": str(base.with_name(name)) if base else name}

    def save_suggestion(self) -> str:
        adventure = self.session.adventure
        return (adventure.title if adventure and adventure.title else self.session.t("app.untitled")) + ".scav"
