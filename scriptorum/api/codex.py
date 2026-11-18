"""The API's codex area (design document F23.1): codex entries and types
(F3), maps (F5), the relationship chart (F3.9) and the M3 upgrade (F3.12).

F3 (M6 part C4): codex actions never fail silently. A refusal says why in
plain words; an unexpected error says so too, and its details go to the
crash log in the app's own folder (F2.11).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Callable

from scriptorum.core.modules import ModuleError
from scriptorum.core.scav import ScavError
from scriptorum.core.world import WorldError


class CodexArea:
    def __init__(self, api):
        self.api = api

    @property
    def session(self):
        return self.api.session

    def _call(self, work: Callable, changes: bool = True) -> dict:
        if self.session.adventure is None:
            return {"ok": False, "error": self.session.t("error.codex.noAdventure"), "key": "error.codex.noAdventure"}
        try:
            result = work()
        except (WorldError, ScavError, ModuleError) as exc:
            return self.api.error(exc)
        except Exception as exc:  # noqa: BLE001
            return self.api.unexpected(exc)
        if changes:
            self.api.emit("codex.changed", tab=self.session.id)
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}

    # --- entries and types (F3) ------------------------------------------------------------
    def codex(self) -> dict:
        if self.session.adventure is None:
            return {"types": [], "entries": [], "maps": [], "handouts": []}
        return self.session.codex()

    def entry(self, entry_id: str) -> dict:
        return self._call(lambda: self.session.entry_info(entry_id), changes=False)

    def convert_info(self, chapter: int, path: list) -> dict:
        """F3 (M6 part C4): what Convert to codex entry offers for a block."""
        return self._call(lambda: self.session.convert_info(int(chapter), path or []), changes=False)

    def convert_to_entry(self, chapter: int, path: list, type_id: str, link=None) -> dict:
        return self._call(lambda: self.session.convert_to_entry(int(chapter), path or [], type_id or "", link or None))

    def create_entry(self, type_id: str, title: str, fields=None, folder: str = "") -> dict:
        return self._call(lambda: self.session.create_entry(type_id or "", title or "", fields, folder or ""))

    def update_entry(self, entry_id: str, data: dict) -> dict:
        return self._call(lambda: self.session.update_entry(entry_id, data or {}))

    def delete_entry(self, entry_id: str) -> dict:
        return self._call(lambda: self.session.delete_entry(entry_id))

    def save_type(self, data: dict) -> dict:
        return self._call(lambda: self.session.save_codex_type(data))

    def scene_entries(self, chapter: int, line: int) -> dict:
        if self.session.adventure is None:
            return {"scene": None, "entries": []}
        return self.session.scene_entries(chapter, line if line > 0 else None)

    def undo(self) -> dict:
        done = self.session.world_undo()
        if done:
            self.api.emit("codex.changed", tab=self.session.id)
        return {"ok": done}

    # --- maps (F5) ------------------------------------------------------------------------------
    def map_info(self, map_id: str) -> dict:
        """The map, and a local copy of its base image for the map editor."""
        try:
            m = self.session.map_info(map_id)
        except WorldError as exc:
            return self.api.error(exc)
        data = self.session.adventure.files.get(m["image"])
        file = None
        if data is not None:
            folder = self.session.work_dir / "editor-maps"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / (m["id"] + Path(m["image"]).suffix)
            if not target.is_file() or target.read_bytes() != data:
                target.write_bytes(data)
            file = str(target)
        return {"ok": True, "map": m, "file": file}

    def create_map(self, title: str, name: str, data_base64: str) -> dict:
        raw = base64.b64decode(data_base64.split(",", 1)[-1])
        return self._call(lambda: self.session.create_map(title, name, raw))

    def create_map_file(self, title: str, path: str) -> dict:
        """F5.7: a map's base image is a JPEG or PNG file."""
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return self._call(lambda: self.session.create_map(title or Path(path).stem, Path(path).name, data))

    def update_map(self, data: dict) -> dict:
        return self._call(lambda: self.session.update_map(data))

    def delete_map(self, map_id: str) -> dict:
        return self._call(lambda: self.session.delete_map(map_id))

    # --- the relationship chart (F3.9) --------------------------------------------------------------
    def chart(self) -> dict:
        return self.session.chart() if self.session.adventure else {"nodes": [], "edges": []}

    def set_chart_positions(self, data: dict) -> dict:
        return self._call(lambda: self.session.set_chart_positions(data))

    # --- an adventure from before M3 (F3.12) ---------------------------------------------------------
    def upgrade_offer(self) -> dict:
        if self.session.adventure is None:
            return {"offer": False, "candidates": []}
        return {"offer": self.session.offers_upgrade(), "candidates": self.session.upgrade_candidates()}

    def apply_upgrade(self, data: dict) -> dict:
        return self._call(lambda: self.session.apply_upgrade(data))
