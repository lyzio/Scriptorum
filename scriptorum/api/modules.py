"""The API's modules area (design document F23.1): game systems and themes
for a new adventure (F1), the module manager (F14), module versions
(F14.3) and Change game system (F14).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from scriptorum.core import modmanager


class ModulesArea:
    def __init__(self, api):
        self.api = api

    @property
    def session(self):
        return self.api.session

    def game_systems(self) -> list:
        return self.session.game_systems()

    def _changed(self, extra: Optional[dict] = None) -> dict:
        """After a module is installed, enabled, disabled or removed: every
        open adventure checks its modules again, and the lists come back."""
        changed = False
        for tab in self.api.sessions:
            changed = tab.refresh_modules() or changed
        self.api.emit("modules.changed", rebuild=changed)
        info = self.api.app.settings()
        info["ok"] = True
        info.update(extra or {})
        return info

    # --- the module manager (F14) ---------------------------------------------------------------
    def install(self, path: str) -> dict:
        """Install a module from a .scmod file with every check of 9.7."""
        try:
            result = modmanager.install(self.session.library, Path(path), self.session.localize)
        except Exception as exc:  # noqa: BLE001 - refused, with the reason in plain words
            return self.api.error(exc)
        module = result["module"]
        return self._changed({"status": result["status"],
                              "module": {"id": module.id, "version": module.version, "name": module.name}})

    def set_disabled(self, module_id: str, version: str, disabled: bool) -> dict:
        try:
            modmanager.set_disabled(self.session.library, module_id, version, disabled, self.session.app_settings)
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        return self._changed()

    def remove(self, module_id: str, version: str) -> dict:
        try:
            modmanager.remove(self.session.library, module_id, version, self.session.app_settings)
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        return self._changed()

    def file_name(self, module_id: str, version: str) -> str:
        """The file name Save as .scmod file… suggests."""
        module = self.session.library.get(module_id, version, include_disabled=True)
        return modmanager.default_file_name(module) if module else "module.scmod"

    def save_to(self, module_id: str, version: str, path: str) -> dict:
        try:
            written = modmanager.save_as_scmod(self.session.library, module_id, version, Path(path))
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        return {"ok": True, "path": str(written)}

    # --- module versions (F14.3) and Change game system (F14) ---------------------------------
    def preview_version(self, which: str, version: str) -> dict:
        """Try another installed version in the preview; nothing changes yet."""
        try:
            info = self.session.preview_version(which, version)
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        self.api.emit("text.changed", tab=self.session.id)
        return info

    def apply_version(self) -> dict:
        info = self.session.apply_version_preview()
        self.api.emit("text.changed", tab=self.session.id)
        return info

    def cancel_version(self) -> dict:
        info = self.session.cancel_version_preview()
        self.api.emit("text.changed", tab=self.session.id)
        return info

    def game_system_fit(self, gs_id: str, version: str) -> dict:
        """What does not fit, and the themes offered for the new game system."""
        try:
            return {"ok": True, **self.session.game_system_fit(gs_id, version)}
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)

    def preview_game_system(self, data: dict) -> dict:
        try:
            info = self.session.preview_game_system(data["id"], data["version"], data.get("theme", ""),
                                                    data.get("themeVersion", ""))
        except Exception as exc:  # noqa: BLE001
            return self.api.error(exc)
        self.api.emit("text.changed", tab=self.session.id)
        return info
