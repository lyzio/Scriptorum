"""The bridge between the interface (TypeScript) and the internal API (3.1, F23).

Every slot returns JSON text. From 0.7.0 (F23.5) the bridge keeps only what
needs Qt: dialogs and file pickers, windows, timers, the clipboard, local
file addresses for the web view, and the WebChannel signals. Everything else
is passed to the internal API (``scriptorum/api``), the one versioned layer
between the core and everything that uses it. The interface calls the
bridge by the same names as before.

Several adventures can be open at the same time, each in its own tab (F2.2);
every slot works on the active tab.
"""

from __future__ import annotations

import json
import threading
import time
from typing import List, Optional

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

from scriptorum.api import Api
from scriptorum.api import net

BUILD_DELAY_MS = 300  # F7.1.1: about 0.3 seconds after typing stops
SNAPSHOT_TICK_MS = 30_000  # F2.6: how often to ask whether a snapshot is due


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _url(path: str) -> str:
    """A local file as an address the web view can show."""
    return QUrl.fromLocalFile(str(path)).toString()


class Bridge(QObject):
    buildStarted = Signal()
    buildFinished = Signal(str)
    documentChanged = Signal()
    spellReady = Signal()
    suggestions = Signal(str)
    appearanceChanged = Signal(str)  # F16: the computer switched light/dark
    fullScreenChanged = Signal(bool)  # F9 (M6): the window entered or left full screen
    selfTestFinished = Signal(str)   # F9: the theme self-test of Help ▸ Check installation
    updateChecked = Signal(str)      # F21 (M6 part C): the result of an update check
    updateInstalled = Signal(str)    # F22 (M6 part C5): the result of Download and install
    _buildDone = Signal(object, object, int)
    _suggestDone = Signal(str)
    _selfTestDone = Signal(str)
    _updateDone = Signal(str)
    _installDone = Signal(str)

    def __init__(self, session, window=None, spelling=None):
        super().__init__()
        self.window = window
        self.api = Api(session, spelling, headless=bool(getattr(window, "headless_test", False)))
        self.api.events.subscribe(self._on_event)
        self.ui_ready = False
        self.on_ui_ready = None
        self.confirm_discard = self._ask_discard  # tests replace this
        self.pick_portrait = None  # tests may stand in for the portrait's file dialog
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(BUILD_DELAY_MS)
        self._timer.timeout.connect(self._start_build)
        self._build_seq = 0
        self.player_preview = False  # F6.4: the "Handouts only" toggle
        self.show_breaks = False     # F7.2 (M5): View ▸ Show breaks
        self._building = False
        self._rebuild = False
        self.last_request_time = 0.0  # when typing last paused (T-BUILD-06)
        self.last_build_start = 0.0
        self.element_map: list = []
        self._buildDone.connect(self._finish_build)
        self._suggestDone.connect(self.suggestions.emit)
        self._updateDone.connect(self.updateChecked.emit)
        self._installDone.connect(self.updateInstalled.emit)
        self.opened_downloads: List[str] = []
        self.opened_sites: List[str] = []
        # F21.4: the question at first start; test windows skip it unless a
        # test asks for it, so the other window tests are not interrupted.
        self.ask_updates_at_start = not getattr(window, "headless_test", False)
        self._snapshots = QTimer(self)
        self._snapshots.setInterval(SNAPSHOT_TICK_MS)
        self._snapshots.timeout.connect(self.snapshot_tick)
        self._snapshots.start()
        self._selfTestDone.connect(self.selfTestFinished.emit)
        self._spell_watch = QTimer(self)
        self._spell_watch.setInterval(250)
        self._spell_watch.timeout.connect(self._check_spell_ready)
        self.spelling.start()
        self._spell_watch.start()
        self.closed = False

    def shutdown(self) -> None:
        """The window is closing: stop every timer and ignore results that
        arrive later from background work, so nothing reaches a page that
        Qt has already deleted."""
        self.closed = True
        for timer in (self._timer, self._snapshots, self._spell_watch):
            timer.stop()

    # --- the API's state, as the tests and the window know it ------------------------
    @property
    def sessions(self):
        return self.api.sessions

    @property
    def active(self) -> int:
        return self.api.active

    @active.setter
    def active(self, value: int) -> None:
        self.api.active = value

    @property
    def session(self):
        return self.api.session

    def _tab_for_new_document(self):
        return self.api.tab_for_new_document()

    def _forward(name, owner="app"):  # noqa: N805 - a small helper for the properties below
        def get(self):
            return getattr(getattr(self.api, owner), name)

        def put(self, value):
            setattr(getattr(self.api, owner), name, value)
        return property(get, put)

    spelling = _forward("spelling")
    system_dark = _forward("system_dark")
    skip_css = _forward("skip_css")
    startup_results = _forward("startup_results")
    open_problem = _forward("open_problem")
    view_state = _forward("view_state")
    start_notice = _forward("start_notice")
    versions = _forward("versions")
    update_url = _forward("update_url")
    update_key = _forward("update_key")
    update_runtime = _forward("update_runtime")
    update_pack = _forward("update_pack")
    update_version = _forward("update_version")
    update_moved = _forward("update_moved")
    update_download = _forward("update_download")
    del _forward

    @property
    def crash_folder(self):
        return self.api.crash_folder

    @crash_folder.setter
    def crash_folder(self, value) -> None:
        self.api.crash_folder = value

    @property
    def last_crash_log(self):
        return getattr(self.api, "last_crash_log", None)

    @property
    def update_requests(self) -> List[str]:
        """Every address the network gate was asked for (F23.6), in order."""
        return self.api.net.requests

    @property
    def update_opener(self):
        return self.api.net.readers.get(net.UPDATE_FILE)

    @update_opener.setter
    def update_opener(self, reader) -> None:
        self._set_reader(net.UPDATE_FILE, reader)

    @property
    def update_downloader(self):
        return self.api.net.readers.get(net.UPDATE_PACK)

    @update_downloader.setter
    def update_downloader(self, reader) -> None:
        self._set_reader(net.UPDATE_PACK, reader)

    def _set_reader(self, purpose: str, reader) -> None:
        if reader is None:
            self.api.net.readers.pop(purpose, None)
        else:
            self.api.net.readers[purpose] = reader

    # --- what the API announces (F23.3) ----------------------------------------------
    def _on_event(self, name: str, details: dict) -> None:
        if self.closed:
            return
        if name in ("text.changed", "codex.changed") or (name == "modules.changed" and details.get("rebuild")):
            self._changed()
        elif name.startswith("adventure."):
            self._title_changed()

    def _changed(self) -> None:
        self._title_changed()
        self.requestBuild()

    def _title_changed(self) -> None:
        if self.window is not None:
            self.window.update_title()

    def _reply(self, data, show_error=False) -> str:
        """The API's reply as JSON; a refusal is also shown in a message box
        where the app always did so: any refusal to open, and a save or an
        export that could not be written (``show_error`` names its key)."""
        if (show_error and isinstance(data, dict) and data.get("ok") is False and data.get("error")
                and (show_error is True or data.get("key") == show_error)):
            self._show_error(data["error"])
        return _json(data)

    # --- closing ------------------------------------------------------------------------
    def _ask_discard(self) -> bool:
        """Unsaved changes before closing: Save, Don't save or Cancel."""
        if not self.api.adventure.unsaved():
            return True
        t = self.api.app.text
        box = QMessageBox(self.window)
        box.setWindowTitle(t("dialog.unsavedTitle"))
        box.setText(t("dialog.unsavedText", title=self.api.adventure.title()))
        save = box.addButton(t("dialog.save"), QMessageBox.AcceptRole)
        discard = box.addButton(t("dialog.discard"), QMessageBox.DestructiveRole)
        box.addButton(t("dialog.cancel"), QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return json.loads(self.save())["ok"]
        return clicked is discard

    def confirm_close_all(self) -> bool:
        """Before quitting: every tab with unsaved changes asks in turn."""
        for index, tab in enumerate(self.api.adventure.tabs()):
            self.active = index
            if tab["dirty"] and not self.confirm_discard():
                return False
        self.api.adventure.close_all()
        return True

    # --- start-up ---------------------------------------------------------------------
    @Slot(result=str)
    def strings(self) -> str:
        return _json(self.api.app.strings())

    @Slot(result=str)
    def uiReady(self) -> str:
        self.ui_ready = True
        reply = self.api.app.ui_ready()
        if self.on_ui_ready:
            self.on_ui_ready()
        return _json(reply)

    @Slot(result=str)
    def info(self) -> str:
        return _json(self.api.adventure.info())

    @Slot(result=str)
    def editorInfo(self) -> str:
        return _json(self.api.adventure.editor_info())

    @Slot(result=str)
    def gameSystems(self) -> str:
        return _json(self.api.modules.game_systems())

    # --- app settings (F18) and palettes (F16) ------------------------------------------
    def _app_info(self) -> dict:
        return self.api.app.settings()

    @Slot(result=str)
    def appSettings(self) -> str:
        return _json(self.api.app.settings())

    @Slot(str, result=str)
    def setAppSettings(self, data: str) -> str:
        return _json(self.api.app.set_settings(json.loads(data)))

    @Slot(str, result=str)
    def savePalette(self, data: str) -> str:
        return _json(self.api.app.save_palette(json.loads(data)))

    @Slot(result=str)
    def resetPalette(self) -> str:
        return _json(self.api.app.reset_palette())

    # --- Help ▸ About Scriptorum (F9) -------------------------------------------------
    @Slot(result=str)
    def aboutInfo(self) -> str:
        return _json(self.api.app.about())

    @Slot(str, result=str)
    def aboutText(self, ref: str) -> str:
        return _json(self.api.app.about_text(ref))

    def _open_in_browser(self, address: QUrl) -> None:
        from PySide6.QtGui import QDesktopServices
        if not getattr(self.window, "headless_test", False):
            QDesktopServices.openUrl(address)

    @Slot(result=str)
    def openIdeaSite(self) -> str:
        """lyzio.net opens in the computer's own web browser; Scriptorum
        itself makes no network request (D9). Only this one address."""
        site = self.api.app.idea_site()
        self.opened_sites.append(site)
        self._open_in_browser(QUrl(site))
        return _json({"ok": True})

    # --- the update check (F21) and installing updates (F22) ------------------------------
    def update_address(self) -> str:
        return self.api.app.update_address()

    def _in_background(self, work, done: Signal) -> None:
        """Work that takes a while runs off the window's thread; its reply
        arrives through a signal."""
        def run():
            reply = _json(work())
            if not self.closed:
                done.emit(reply)
        threading.Thread(target=run, daemon=True).start()

    def _run_update_check(self, auto: bool) -> None:
        self._in_background(lambda: self.api.app.check_updates(auto), self._updateDone)

    @Slot(result=str)
    def checkForUpdates(self) -> str:
        """Help ▸ Check for updates…: with Download and install, the only
        network requests the app makes (D9), through the API's gate (F23.6)."""
        self._run_update_check(auto=False)
        return _json({"ok": True})

    @Slot(result=str)
    def installUpdate(self) -> str:
        """F22: Download and install, only when the author clicks it; the
        result arrives through ``updateInstalled``."""
        if not self.api.app.can_install():
            return _json({"ok": False})
        self._in_background(self.api.app.install_update, self._installDone)
        return _json({"ok": True})

    @Slot(result=str)
    def useMovedAddress(self) -> str:
        return _json(self.api.app.use_moved_address())

    @Slot(str, result=str)
    def setUpdateAddress(self, address: str) -> str:
        return _json(self.api.app.set_update_address(address))

    @Slot(result=str)
    def versionInfo(self) -> str:
        return _json(self.api.app.version_info())

    @Slot(result=str)
    def goBack(self) -> str:
        return _json(self.api.app.go_back())

    @Slot(result=str)
    def weeklyUpdateCheck(self) -> str:
        due = self.api.app.weekly_check_due()
        if due:
            self._run_update_check(auto=True)
        return _json({"ok": True, "started": due})

    @Slot(result=str)
    def updatePrompt(self) -> str:
        return _json(self.api.app.update_prompt(self.ask_updates_at_start))

    @Slot(bool, result=str)
    def answerUpdatePrompt(self, weekly: bool) -> str:
        return _json(self.api.app.answer_update_prompt(weekly))

    @Slot(result=str)
    def openDownloadPage(self) -> str:
        """The download page from the last update file opens in the computer's
        own web browser; Scriptorum downloads nothing (F21.3)."""
        page = self.api.app.download_page()
        if not page:
            return _json({"ok": False})
        self.opened_downloads.append(page)
        self._open_in_browser(QUrl(page))
        return _json({"ok": True})

    # --- the window's zoom (F9, issue #16) and full screen (F9) -------------------------
    @Slot(result=str)
    def appZoom(self) -> str:
        return _json(self.api.app.zoom())

    @Slot(int, result=str)
    def setAppZoom(self, percent: int) -> str:
        """Store the window's zoom (one of the steps, F18) and show it."""
        reply = self.api.app.set_zoom(percent)
        if self.window is not None and hasattr(self.window, "apply_app_zoom"):
            reply = {"zoom": self.window.apply_app_zoom()}
        return _json(reply)

    @Slot(bool, result=str)
    def setFullScreen(self, on: bool) -> str:
        if self.window is not None and hasattr(self.window, "set_full_screen"):
            self.window.set_full_screen(bool(on))
        return _json({"ok": True, "fullScreen": self.is_full_screen()})

    @Slot(result=bool)
    def isFullScreen(self) -> bool:
        return self.is_full_screen()

    def is_full_screen(self) -> bool:
        return bool(self.window is not None and self.window.isFullScreen())

    def full_screen_changed(self, on: bool) -> None:
        if not self.closed:
            self.fullScreenChanged.emit(bool(on))

    @Slot(result=str)
    def openCrashLogFolder(self) -> str:
        """F18: the button that opens the crash-log folder (on this computer)."""
        folder = self.api.app.crash_log_folder()
        self._open_in_browser(QUrl.fromLocalFile(folder))
        return _json({"ok": True, "path": folder})

    def set_system_dark(self, dark: bool) -> None:
        self.system_dark = bool(dark)
        if not self.closed:
            self.appearanceChanged.emit(_json({"systemDark": self.system_dark}))

    @Slot(result=str)
    def openExample(self) -> str:
        return _json(self.api.adventure.open_example())

    @Slot(str, result=str)
    def setTheme(self, theme_id: str) -> str:
        return _json(self.api.adventure.set_theme(theme_id))

    # --- the module manager (F14) ---------------------------------------------------------
    @Slot(result=str)
    def installModuleDialog(self) -> str:
        """Settings ▸ Modules ▸ Install module…: choose a .scmod file."""
        t = self.api.app.text
        path, _ = QFileDialog.getOpenFileName(self.window, t("dialog.installModuleTitle"), "", t("dialog.scmodFilter"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.installModulePath(path)

    @Slot(str, result=str)
    def installModulePath(self, path: str) -> str:
        return _json(self.api.modules.install(path))

    @Slot(str, str, bool, result=str)
    def setModuleDisabled(self, module_id: str, version: str, disabled: bool) -> str:
        return _json(self.api.modules.set_disabled(module_id, version, disabled))

    @Slot(str, str, result=str)
    def removeModule(self, module_id: str, version: str) -> str:
        return _json(self.api.modules.remove(module_id, version))

    @Slot(str, str, result=str)
    def saveModuleDialog(self, module_id: str, version: str) -> str:
        """Save as .scmod file…: one file to send along with an adventure."""
        t = self.api.app.text
        suggested = self.api.modules.file_name(module_id, version)
        path, _ = QFileDialog.getSaveFileName(self.window, t("dialog.saveModuleTitle"), suggested, t("dialog.scmodFilter"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.saveModuleTo(module_id, version, path)

    @Slot(str, str, str, result=str)
    def saveModuleTo(self, module_id: str, version: str, path: str) -> str:
        return _json(self.api.modules.save_to(module_id, version, path))

    @Slot(str, str, result=str)
    def previewVersion(self, which: str, version: str) -> str:
        return _json(self.api.modules.preview_version(which, version))

    @Slot(result=str)
    def applyVersion(self) -> str:
        return _json(self.api.modules.apply_version())

    @Slot(str, str, result=str)
    def gameSystemFit(self, gs_id: str, version: str) -> str:
        return _json(self.api.modules.game_system_fit(gs_id, version))

    @Slot(str, result=str)
    def previewGameSystem(self, request: str) -> str:
        return _json(self.api.modules.preview_game_system(json.loads(request)))

    @Slot(result=str)
    def cancelVersion(self) -> str:
        return _json(self.api.modules.cancel_version())

    # --- tabs (F2.2) -----------------------------------------------------------------------
    @Slot(result=str)
    def tabs(self) -> str:
        return _json(self.api.adventure.tabs())

    @Slot(str, result=str)
    def switchTab(self, tab_id: str) -> str:
        reply = self.api.adventure.switch_tab(tab_id)
        if reply["ok"]:
            self.requestBuild()
        return _json(reply)

    @Slot(str, result=str)
    def closeTab(self, tab_id: str) -> str:
        previous = self.active
        if not self.api.adventure.switch_tab(tab_id)["ok"]:
            return _json({"ok": False})
        if not self.confirm_discard():
            self.active = previous
            return _json({"ok": False, "cancelled": True})
        closing = self.active
        single = len(self.sessions) == 1
        self.api.adventure.close_active_tab()
        if not single:
            if previous > closing:
                previous -= 1
            elif previous == closing:
                previous = max(0, closing - 1)
            self.active = min(previous, len(self.sessions) - 1)
        self._title_changed()
        self.requestBuild()
        return _json({"ok": True})

    # --- files ---------------------------------------------------------------------------------
    @Slot(str, result=str)
    def newAdventure(self, request: str) -> str:
        return _json(self.api.adventure.new(json.loads(request)))

    @Slot(result=str)
    def openDialog(self) -> str:
        t = self.api.app.text
        path, _ = QFileDialog.getOpenFileName(self.window, t("dialog.openTitle"), "", t("dialog.scavFilter"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.openPath(path)

    @Slot(result=str)
    def openFolderDialog(self) -> str:
        """F2.4: open an unpacked adventure folder."""
        path = QFileDialog.getExistingDirectory(self.window, self.api.app.text("dialog.openFolderTitle"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.openPath(path)

    @Slot(str, result=str)
    def openPath(self, path: str) -> str:
        return self._reply(self.api.adventure.open(path), show_error=True)

    @Slot(result=str)
    def save(self) -> str:
        if not self.api.adventure.is_open():
            return _json({"ok": False})
        if self.api.adventure.needs_file_name():
            return self.saveAs()
        return self.saveTo(self.api.adventure.path())

    @Slot(result=str)
    def saveAs(self) -> str:
        t = self.api.app.text
        path, _ = QFileDialog.getSaveFileName(self.window, t("dialog.saveTitle"), self.api.adventure.save_suggestion(),
                                              t("dialog.scavFilter"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.saveTo(path)

    @Slot(result=str)
    def saveAsFolderDialog(self) -> str:
        """F2.4: save as an unpacked folder, for authors who use Git."""
        path = QFileDialog.getExistingDirectory(self.window, self.api.app.text("dialog.saveFolderTitle"))
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.saveToFolder(path)

    @Slot(str, result=str)
    def saveTo(self, path: str) -> str:
        return self._reply(self.api.adventure.save_to(path, None), show_error="error.save.failed")

    @Slot(str, result=str)
    def saveToFolder(self, path: str) -> str:
        return self._reply(self.api.adventure.save_to(path, True), show_error="error.save.failed")

    # --- work protection (F2.5–F2.8) ---------------------------------------------------------
    @Slot(result=str)
    def recoveries(self) -> str:
        return _json(self.api.adventure.recoveries())

    @Slot(str, result=str)
    def restoreRecovery(self, session_id: str) -> str:
        return _json(self.api.adventure.restore_recovery(session_id))

    @Slot(str, result=str)
    def discardRecovery(self, session_id: str) -> str:
        return _json(self.api.adventure.discard_recovery(session_id))

    def snapshot_tick(self) -> None:
        if not self.closed:
            self.api.adventure.snapshot_tick()

    @Slot(result=str)
    def snapshots(self) -> str:
        return _json(self.api.adventure.snapshots())

    @Slot(str, result=str)
    def revertTo(self, snapshot_id: str) -> str:
        return _json(self.api.adventure.revert_to(snapshot_id))

    # --- chapters ----------------------------------------------------------------------------
    @Slot(int, result=str)
    def chapter(self, index: int) -> str:
        return _json(self.api.adventure.chapter(index))

    @Slot(int, str, result=str)
    def setChapterText(self, index: int, text: str) -> str:
        return _json(self.api.adventure.set_chapter_text(index, text))

    @Slot(int, str, result=str)
    def setChapterDoc(self, index: int, doc: str) -> str:
        return _json(self.api.adventure.set_chapter_doc(index, json.loads(doc)))

    @Slot(str, result=str)
    def blockSource(self, block: str) -> str:
        return _json(self.api.adventure.block_source(json.loads(block)))

    # --- the settings page (F7.3, F7.9) ---------------------------------------------------
    @Slot(result=str)
    def settings(self) -> str:
        return _json(self.api.adventure.settings())

    @Slot(str, result=str)
    def setSettings(self, data: str) -> str:
        return _json(self.api.adventure.set_settings(json.loads(data)))

    # --- find and replace (F4.7) ------------------------------------------------------------
    @Slot(str, result=str)
    def find(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.adventure.find(data.get("query", ""), bool(data.get("matchCase"))))

    @Slot(str, result=str)
    def replaceAll(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.adventure.replace_all(data.get("query", ""), data.get("replacement", ""),
                                                    bool(data.get("matchCase"))))

    # --- images, portraits and fonts (F4.6, 11.4, F11) -----------------------------------------
    @Slot(str, str, result=str)
    def addImageData(self, name: str, data: str) -> str:
        return _json(self.api.adventure.add_image(name, data))

    def _pick_file(self, title_key: str, filter_key: str) -> str:
        t = self.api.app.text
        path, _ = QFileDialog.getOpenFileName(self.window, t(title_key), "", t(filter_key))
        return path

    @Slot(result=str)
    def addImageDialog(self) -> str:
        path = self._pick_file("dialog.imageTitle", "dialog.imageFilter")
        if not path:
            return _json({"ok": False, "cancelled": True})
        return _json(self.api.adventure.add_image_file(path))

    @Slot(result=str)
    def addPortraitDialog(self) -> str:
        """11.4: choose a person's portrait, JPEG or PNG only."""
        if self.pick_portrait is not None:  # the scenario tests stand in for the file dialog
            path = self.pick_portrait()
        else:
            path = self._pick_file("dialog.portraitTitle", "dialog.portraitFilter")
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.addPortraitPath(path)

    @Slot(str, result=str)
    def addPortraitPath(self, path: str) -> str:
        return _json(self.api.adventure.add_portrait_file(path))

    @Slot(result=str)
    def addFontDialog(self) -> str:
        path = self._pick_file("dialog.fontTitle", "dialog.fontFilter")
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.addFontPath(path)

    @Slot(str, result=str)
    def addFontPath(self, path: str) -> str:
        return _json(self.api.adventure.add_font_file(path))

    @Slot(result=str)
    def fonts(self) -> str:
        return _json(self.api.adventure.fonts())

    @Slot(str, result=str)
    def imageUrl(self, path: str) -> str:
        """A local address for showing an adventure image in the editor."""
        file = self.api.adventure.image_file(path)
        if file is None:
            return _json({"ok": False})
        return _json({"ok": True, "url": _url(file)})

    # --- spell check (F4.8) -----------------------------------------------------------------
    def _check_spell_ready(self) -> None:
        if self.closed:
            return
        if self.spelling.ready:
            self._spell_watch.stop()
            self.spellReady.emit()

    @Slot(str, result=str)
    def spell(self, words: str) -> str:
        return _json(self.api.app.spell(json.loads(words)))

    @Slot(str, result=str)
    def suggest(self, word: str) -> str:
        """Suggestions arrive later through the ``suggestions`` signal."""
        self._in_background(lambda: self.api.app.suggest(word), self._suggestDone)
        return _json({"ok": True})

    # --- the start-up checks in the main window (F9) -----------------------------------------
    @Slot(result=str)
    def startupReport(self) -> str:
        return _json(self.api.app.startup_report())

    @Slot(result=str)
    def checkInstallation(self) -> str:
        return _json(self.api.app.check_installation())

    @Slot(result=str)
    def themeSelfTest(self) -> str:
        """The slower theme self-test (9.7.5); the result arrives later
        through the ``selfTestFinished`` signal."""
        tab = self.api.adventure.tabs()[self.active]["id"]
        self._in_background(lambda: self.api.app.theme_self_test(tab), self._selfTestDone)
        return _json({"ok": True})

    @Slot(str, result=str)
    def copyText(self, text: str) -> str:
        """Copy details: the results as text on the clipboard."""
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(text)
        return _json({"ok": True})

    # --- the preview's zoom, kept for each adventure (F7.2) -------------------------------------
    @Slot(result=str)
    def previewZoom(self) -> str:
        return _json(self.api.app.preview_zoom())

    @Slot(str, result=str)
    def setPreviewZoom(self, value: str) -> str:
        try:
            wanted = json.loads(value)
        except json.JSONDecodeError:
            wanted = value
        return _json(self.api.app.set_preview_zoom(wanted))

    # --- building and export ---------------------------------------------------------------
    @Slot(result=str)
    def requestBuild(self) -> str:
        """Restart the 0.3 s timer; the build runs when typing pauses."""
        if self.api.adventure.is_open():
            self.last_request_time = time.monotonic()
            self._timer.start()
        return _json({"ok": True})

    def _start_build(self) -> None:
        if self.closed:
            return
        if self._building:
            self._rebuild = True
            return
        self._building = True
        self.last_build_start = time.monotonic()
        self._build_seq += 1
        seq = self._build_seq
        self.buildStarted.emit()
        session = self.session
        player, breaks = self.player_preview, self.show_breaks

        def work():
            result, element_map = self.api.build._run(session, player, breaks)
            self._buildDone.emit(result, (session, element_map), seq)

        threading.Thread(target=work, daemon=True).start()

    def _finish_build(self, result, extra, seq: int) -> None:
        self._building = False
        if self.closed:
            return
        built_for, element_map = extra
        if self._rebuild or built_for is not self.session:
            self._rebuild = False
            self._start_build()
            return
        payload = self.api.build._finish(self.session, result, element_map, seq)
        if payload["ok"]:
            self.element_map = element_map
            payload = {"ok": True, "pages": [_url(f) for f in payload.pop("files")], **payload}
        self.last_build_payload = payload  # F7.2 (M5): for the separate preview window
        self.buildFinished.emit(_json(payload))

    def _save_dialog(self, title_key: str, suggestion: str) -> str:
        t = self.api.app.text
        path, _ = QFileDialog.getSaveFileName(self.window, t(title_key), suggestion, t("dialog.pdfFilter"))
        return path

    @Slot(result=str)
    def exportDialog(self) -> str:
        suggestion = self.api.adventure.export_suggestion("adventure")
        if suggestion is None:
            return _json({"ok": False})
        path = self._save_dialog("dialog.exportTitle", suggestion["path"])
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.exportTo(path)

    @Slot(str, result=str)
    def exportTo(self, path: str) -> str:
        return self._reply(self.api.build.export(path, "full"), show_error="error.export.failed")

    @Slot(result=str)
    def exportHandoutsDialog(self) -> str:
        """F7.6.2: the player PDF, with only the handouts (F6.2)."""
        suggestion = self.api.adventure.export_suggestion("handouts")
        if suggestion is None:
            return _json({"ok": False})
        path = self._save_dialog("dialog.exportHandoutsTitle", suggestion["path"])
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.exportHandoutsTo(path)

    @Slot(str, result=str)
    def exportHandoutsTo(self, path: str) -> str:
        return self._reply(self.api.build.export(path, "handouts"), show_error="error.export.failed")

    @Slot(str, result=str)
    def exportVariantDialog(self, variant: str) -> str:
        """F7.6 (M5): File ▸ Export ▸ Booklet PDF… and Print-shop PDF…"""
        suggestion = self.api.adventure.export_suggestion("variant", variant)
        if suggestion is None:
            return _json({"ok": False})
        path = self._save_dialog(f"export.title.{variant}", suggestion["path"])
        if not path:
            return _json({"ok": False, "cancelled": True})
        return self.exportVariantTo(path, variant)

    @Slot(str, str, result=str)
    def exportVariantTo(self, path: str, variant: str) -> str:
        return self._reply(self.api.build.export(path, variant), show_error="error.export.failed")

    # --- the codex, maps and the chart (F3, F5, F6) ---------------------------------------------
    @Slot(result=str)
    def codex(self) -> str:
        return _json(self.api.codex.codex())

    @Slot(str, result=str)
    def entry(self, entry_id: str) -> str:
        return _json(self.api.codex.entry(entry_id))

    @Slot(str, result=str)
    def convertInfo(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.codex.convert_info(data.get("chapter", 0), data.get("path", [])))

    @Slot(str, result=str)
    def convertToEntry(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.codex.convert_to_entry(data.get("chapter", 0), data.get("path", []),
                                                     data.get("type", ""), data.get("link")))

    @Slot(str, result=str)
    def createEntry(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.codex.create_entry(data.get("type", ""), data.get("title", ""), data.get("fields"),
                                                 data.get("folder", "")))

    @Slot(str, result=str)
    def updateEntry(self, request: str) -> str:
        data = json.loads(request)
        return _json(self.api.codex.update_entry(data["id"], data.get("data", {})))

    @Slot(str, result=str)
    def deleteEntry(self, entry_id: str) -> str:
        return _json(self.api.codex.delete_entry(entry_id))

    @Slot(str, result=str)
    def saveCodexType(self, request: str) -> str:
        return _json(self.api.codex.save_type(json.loads(request)))

    @Slot(int, int, result=str)
    def sceneEntries(self, chapter: int, line: int) -> str:
        return _json(self.api.codex.scene_entries(chapter, line))

    @Slot(result=str)
    def worldUndo(self) -> str:
        return _json(self.api.codex.undo())

    @Slot(str, result=str)
    def mapInfo(self, map_id: str) -> str:
        reply = self.api.codex.map_info(map_id)
        if reply.get("ok"):
            file = reply.pop("file")
            reply["url"] = _url(file) if file else None
        return _json(reply)

    @Slot(str, result=str)
    def createMapDialog(self, title: str) -> str:
        """F5.7: a map's base image is a JPEG or PNG file."""
        path = self._pick_file("dialog.mapImageTitle", "dialog.mapImageFilter")
        if not path:
            return _json({"ok": False, "cancelled": True})
        return _json(self.api.codex.create_map_file(title, path))

    @Slot(str, str, str, result=str)
    def createMapData(self, title: str, name: str, data: str) -> str:
        return _json(self.api.codex.create_map(title, name, data))

    @Slot(str, result=str)
    def updateMap(self, request: str) -> str:
        return _json(self.api.codex.update_map(json.loads(request)))

    @Slot(str, result=str)
    def deleteMap(self, map_id: str) -> str:
        return _json(self.api.codex.delete_map(map_id))

    @Slot(result=str)
    def chart(self) -> str:
        return _json(self.api.codex.chart())

    @Slot(str, result=str)
    def setChartPositions(self, request: str) -> str:
        return _json(self.api.codex.set_chart_positions(json.loads(request)))

    @Slot(result=str)
    def upgradeOffer(self) -> str:
        return _json(self.api.codex.upgrade_offer())

    @Slot(str, result=str)
    def applyUpgrade(self, request: str) -> str:
        return _json(self.api.codex.apply_upgrade(json.loads(request)))

    # --- the preview window and the preview's options (F7.2, F6.4) ------------------------------
    @Slot(result=str)
    def lastBuild(self) -> str:
        """F7.2 (M5): the last build's pages, for a newly opened preview window."""
        return _json(getattr(self, "last_build_payload", None))

    @Slot(result=str)
    def previewWindowTitle(self) -> str:
        return _json({"title": self.api.app.text("app.previewWindowTitle", title=self.api.adventure.title())})

    @Slot(result=str)
    def openPreviewWindow(self) -> str:
        """F7.2 (M5): the preview in a window of its own, with the same zoom bar."""
        if self.window is None or not hasattr(self.window, "open_preview_window"):
            return _json({"ok": False})
        self.window.open_preview_window()
        return _json({"ok": True})

    @Slot(bool, result=str)
    def setShowBreaks(self, on: bool) -> str:
        """F7.2 (M5): View ▸ Show breaks marks page and column breaks in the
        preview. Exported PDFs never show them."""
        self.show_breaks = bool(on)
        self.requestBuild()
        return _json({"ok": True, "on": self.show_breaks})

    @Slot(bool, result=str)
    def setHandoutsOnly(self, on: bool) -> str:
        """F6.4: the preview shows exactly what the players will receive."""
        self.player_preview = bool(on)
        self.requestBuild()
        return _json({"ok": True, "on": self.player_preview})

    @Slot(result=str)
    def quit(self) -> str:
        if self.window is not None:
            self.window.close()
        return _json({"ok": True})

    # --- messages -------------------------------------------------------------------------------
    def _show_error(self, text: str) -> None:
        if self.window is None or getattr(self.window, "headless_test", False):
            return
        QMessageBox.warning(self.window, self.api.app.text("dialog.errorTitle"), text)
