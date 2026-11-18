"""The API's app area (design document F23.1): the app settings (F18),
palettes (F16), the interface language (F15), Help ▸ About (F9), the
start-up checks (F9), spell check (F4.8), the window's and the preview's
zoom (F9, F7.2), and the update check and install (F21, F22).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from scriptorum import __version__, paths
from scriptorum.api import net
from scriptorum.core import appsettings, modmanager, updates
from scriptorum.core.spelling import SpellChecker


class AppArea:
    def __init__(self, api, spelling=None):
        from scriptorum.core.packs import Versions
        from scriptorum.core.viewstate import ViewState

        self.api = api
        self.spelling = spelling or SpellChecker()
        self.system_dark = False   # F16: whether the computer is in dark mode
        self.skip_css = False      # F16: Shift held at start skips a palette's stylesheet
        self.startup_results: list = []   # checks that failed at start-up (F9)
        self.open_problem: Optional[Exception] = None   # why the double-clicked adventure did not open
        self.view_state = ViewState(paths.app_home() / "view-state.json")  # F7.2: zoom per adventure
        # F21, F22: the update address, and what the last signed update file said.
        self.update_url = updates.UPDATE_URL
        self.update_key: Optional[str] = None       # the tests stand in for the built-in key
        self.update_runtime: Optional[dict] = None  # and for this computer's libraries
        self.update_pack: Optional[dict] = None
        self.update_version: Optional[str] = None
        self.update_moved: Optional[str] = None
        self.update_download: Optional[str] = None
        self.versions = Versions(paths.app_home())
        self.start_notice = None

    @property
    def session(self):
        return self.api.session

    # --- the interface ------------------------------------------------------------
    def text(self, key: str, **details) -> str:
        """One interface text, with its details filled in (F15)."""
        return self.session.t(key, **details)

    def strings(self) -> dict:
        """F15: every interface text of the chosen language."""
        return self.session.strings.table

    def ui_ready(self) -> dict:
        """F22.5: this version opened its window, so it has started; anything
        the start-up step has to say is kept to be shown once."""
        try:
            self.versions.started(__version__)
            if self.start_notice is None:
                self.start_notice = self.versions.take_notice()
        except OSError:
            pass
        return {"ok": True}

    # --- app settings (F18) and palettes (F16) ----------------------------------------
    def settings(self) -> dict:
        library = self.session.library
        settings = self.session.app_settings
        chosen = appsettings.chosen_palette(library, settings)
        return {
            "values": dict(settings.values),
            "systemDark": self.system_dark,
            "skipCss": self.skip_css,
            "palette": appsettings.palette_info(chosen, self.skip_css) if chosen else None,
            "palettes": [appsettings.palette_info(m, True) for m in appsettings.palettes(library)],
            "tokens": list(appsettings.TOKENS),
            "languages": [{"id": m.id, "name": m.name} for m in library.of_kind("interface-language")],
            # F14, F18 (M6): the module manager's list, disabled modules included.
            "modules": modmanager.module_list(library, self.session.recent._read(), settings),
            "crashLogs": str(paths.logs_dir()),
        }

    def set_settings(self, changes: dict) -> dict:
        """F18: every change takes effect at once, without a restart."""
        changes = dict(changes or {})
        if "palette" in changes:
            changes.setdefault("palette_version", None)
        self.session.app_settings.update(changes)
        for tab in self.api.sessions:
            tab.apply_app_settings()
        self.api.emit("settings.changed", what="app")
        return self.settings()

    def save_palette(self, request: dict) -> dict:
        """F16 New palette from this one: saved as a palette module and chosen."""
        from scriptorum.core.palettes import low_contrast

        try:
            module = appsettings.save_palette(self.session.library, request.get("name", ""),
                                              request.get("light", {}), request.get("dark", {}))
        except Exception as exc:  # noqa: BLE001 - shown to the author in plain words
            return self.api.error(exc)
        self.session.app_settings.update({"palette": module.id, "palette_version": module.version})
        info = self.settings()
        info["ok"] = True
        info["saved"] = {"id": module.id, "version": module.version, "name": module.name}
        info["warnings"] = low_contrast(request.get("light", {})) + low_contrast(request.get("dark", {}))
        self.api.emit("settings.changed", what="app")
        return info

    def reset_palette(self) -> dict:
        """F16: Reset to Claret & Ink is always offered."""
        self.session.app_settings.update({"palette": appsettings.DEFAULT_PALETTE, "palette_version": None})
        self.api.emit("settings.changed", what="app")
        return self.settings()

    def zoom(self) -> dict:
        """F9 (issue #16): the whole window's zoom, in per cent."""
        return {"zoom": int(self.session.app_settings.get("app_zoom") or 100)}

    def set_zoom(self, percent: int) -> dict:
        """Store the window's zoom; only the steps are kept (F18)."""
        self.session.app_settings.update({"app_zoom": int(percent)})
        return self.zoom()

    def preview_zoom(self) -> dict:
        """F7.2: the preview's zoom, kept for each adventure outside its file."""
        return {"zoom": self.view_state.get_zoom(self.session.snapshot_key())}

    def set_preview_zoom(self, wanted) -> dict:
        return {"zoom": self.view_state.set_zoom(self.session.snapshot_key(), wanted)}

    # --- Help ▸ About Scriptorum (F9) -------------------------------------------------
    def about(self) -> dict:
        from scriptorum.core import about
        return about.info(self.session.library)

    def about_text(self, ref: str) -> dict:
        from scriptorum.core import about
        text = about.text(ref, self.session.library)
        return {"ok": text is not None, "text": text or ""}

    def idea_site(self) -> str:
        from scriptorum.core.about import IDEA_SITE
        return IDEA_SITE

    def crash_log_folder(self) -> str:
        return str(paths.logs_dir())

    # --- the start-up checks (F9) ----------------------------------------------------
    def _check_lines(self, results) -> list:
        from scriptorum.core.startup import line_text

        table = self.session.strings.table
        return [{**r.to_json(), "text": line_text(table, r)} for r in results]

    def startup_report(self) -> dict:
        """What the start-up window found missing: the quiet bar names it."""
        problem, self.open_problem = self.open_problem, None
        return {
            "problems": self._check_lines(self.startup_results),
            "openError": self.api.error(problem)["error"] if problem is not None else "",
        }

    def check_installation(self) -> dict:
        """Help ▸ Check installation: the same list as the start-up window."""
        from scriptorum.core.startup import Startup, report_text

        startup = Startup()
        results = startup.run()
        self.startup_results = startup.failed()
        if startup.spelling is not None and not startup.spelling.unavailable and self.spelling.unavailable:
            self.spelling = startup.spelling  # the missing part was put back
        return {
            "ok": startup.ok,
            "results": self._check_lines(results),
            "report": report_text(self.session.strings.table, results, __version__),
            "version": __version__,
        }

    def theme_self_test(self, tab: str = "") -> dict:
        """The slower theme self-test (9.7.5), with the modules of the given
        tab (the active one by default). Takes a while: the bridge runs it off
        the window's thread."""
        from scriptorum.core.startup import theme_self_test

        session = next((s for s in self.api.sessions if s.id == tab), self.session)
        try:
            return {"ok": True, "lines": theme_self_test(session)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "lines": []}

    # --- spell check (F4.8) ----------------------------------------------------------
    def spell(self, words: list) -> dict:
        # F9: a part that failed never waits silently.
        if self.spelling.ready and self.spelling.unavailable:
            return {"ready": True, "wrong": [], "unavailable": self.session.t("spell.unavailable")}
        # F17.2 (M5): the adventure's document language chooses the dictionaries.
        lang = (self.session.adventure.settings.get("language") if self.session.adventure else None) or ""
        languages = {"sv": ("sv",), "en": ("en", "en-gb")}.get(lang)
        return {"ready": self.spelling.ready, "wrong": self.spelling.misspelled(words, languages)}

    def suggest(self, word: str) -> dict:
        """Suggestions for one word; takes a moment, so the bridge runs it off
        the window's thread."""
        return {"word": word, "suggestions": self.spelling.suggest(word)}

    # --- the update check (F21) and installing updates (F22) ----------------------------
    def update_address(self) -> str:
        """F22: the Update address the author entered, or the built-in one."""
        return updates.address_in_use(self.session.app_settings.get("update_address"), self.update_url)

    def check_updates(self, auto: bool = False) -> dict:
        """Ask for the update file through the network gate (F23.6). Takes up
        to a few seconds: the bridge runs it off the window's thread."""
        url = self.update_address()
        settings = self.session.app_settings
        result = updates.check(__version__, url, self.api.net.reader_for(net.UPDATE_FILE),
                               key=self.update_key, have=self.update_runtime)
        if result["state"] not in (updates.NO_ADDRESS, updates.NOT_HTTPS):
            settings.update({"update_last_check": int(time.time())})
        self.update_download = result.get("download")
        self.update_pack = result.pop("pack", None)
        self.update_version = result.get("version") if self.update_pack else None
        self.update_moved = result.get("moved")
        result["installable"] = self.update_pack is not None
        result["auto"] = auto
        result["current"] = __version__
        result["address"] = url if updates.address_set(url) else ""
        result["entered"] = bool((settings.get("update_address") or "").strip())
        return result

    def can_install(self) -> bool:
        return bool(self.update_pack)

    def install_update(self) -> dict:
        """F22: download the pack named in the last signed update file through
        the network gate, check it and unpack it into the author's folder for
        the next start. Takes a while: the bridge runs it off the window's thread."""
        pack, version = self.update_pack, self.update_version
        if not pack:
            return {"ok": False}
        try:
            installed = updates.install(pack, self.versions, self.api.net.reader_for(net.UPDATE_PACK),
                                        key=self.update_key, have=self.update_runtime,
                                        running=self._running_kept(__version__), expected=version)
            return {"ok": True, "version": installed}
        except updates.InstallError as exc:
            return {"ok": False, "reason": exc.reason}
        except Exception as exc:  # noqa: BLE001 - said plainly, details in the crash log
            from scriptorum.core import crashlog
            crashlog.write_crash_log(type(exc), exc, exc.__traceback__)
            return {"ok": False, "reason": "damaged"}

    def _running_kept(self, running: str) -> Optional[str]:
        """The version running now, when it runs from the author's folder."""
        from scriptorum.boot import ENV_FOLDER
        folder = os.environ.get(ENV_FOLDER)
        if folder and Path(folder).name == running and Path(folder).parent == self.versions.root:
            return running
        return None

    def use_moved_address(self) -> dict:
        """F22: the signed update file said the address has moved and the
        author answered Yes."""
        moved = self.update_moved
        if not updates.address_ok(moved or ""):
            return {"ok": False}
        self.session.app_settings.update({"update_address": moved})
        self.update_moved = None
        return {"ok": True, "app": self.settings()}

    def set_update_address(self, address: str) -> dict:
        """F22: only https is accepted; empty means the built-in address."""
        address = (address or "").strip()
        if address and not updates.address_ok(address):
            return {"ok": False, "error": self.session.t("update.addressRefused"), "key": "update.addressRefused"}
        self.session.app_settings.update({"update_address": address})
        return {"ok": True, "app": self.settings()}

    def version_info(self) -> dict:
        """F22: the version running, the installed app's own, the one Go back
        would run, and what the start-up step has to say (once)."""
        from scriptorum.boot import builtin_version
        builtin = builtin_version()
        try:
            back = self.versions.back_target(__version__, builtin)
        except OSError:
            back = None
        notice, self.start_notice = self.start_notice, None
        return {"running": __version__, "builtin": builtin, "back": back, "notice": notice}

    def go_back(self) -> dict:
        """F22.5: Help ▸ Go back to version X. The next start runs X."""
        from scriptorum.boot import builtin_version
        target = self.versions.go_back(__version__, builtin_version())
        return {"ok": target is not None, "version": target}

    def weekly_check_due(self) -> bool:
        """F21.4: only when the author turned on Check once a week and a week passed."""
        return updates.weekly_due(self.session.app_settings) and updates.address_set(self.update_address())

    def update_prompt(self, ask_at_start: bool) -> dict:
        """F21.4: at first start Scriptorum asks once whether to check weekly."""
        return {"ask": ask_at_start and not bool(self.session.app_settings.get("update_asked"))}

    def answer_update_prompt(self, weekly: bool) -> dict:
        self.session.app_settings.update({"update_asked": True, "update_weekly": bool(weekly)})
        return self.settings()

    def download_page(self) -> Optional[str]:
        """The download page named in the last update file (F21.3)."""
        return self.update_download
