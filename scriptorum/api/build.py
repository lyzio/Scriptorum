"""The API's build area (design document F23.1): the live preview's build
(F7.1, F7.2), its problems and pages, and exports to a given file (F7.6).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Tuple

from scriptorum.core.build import BuildResult, Problem


class BuildArea:
    def __init__(self, api):
        self.api = api

    @property
    def session(self):
        return self.api.session

    def _run(self, session, player: bool = False, show_breaks: bool = False) -> Tuple[BuildResult, list]:
        """One preview build of a tab, as SVG pages (vector, four times faster
        than PNG on long adventures). Takes a moment: the bridge runs it off
        the window's thread. Never raises: a failure is a failed result."""
        element_map: list = []
        try:
            result = session.build("svg", player=player, show_breaks=show_breaks and not player)
            if result.ok and not player:
                element_map = session.element_map()
        except Exception as exc:  # never leave the interface waiting
            result = BuildResult(False, errors=[Problem("error.build.typst", message=str(exc))])
        return result, element_map

    def _finish(self, session, result: BuildResult, element_map: list, seq: int) -> dict:
        """Write a finished build's pages into the tab's preview folder and
        describe it in plain data; announce ``build.finished``."""
        if result.ok:
            folder = session.work_dir / "preview"
            shutil.rmtree(folder, ignore_errors=True)
            folder.mkdir(parents=True, exist_ok=True)
            files = []
            for number, page in enumerate(result.output, start=1):
                file = folder / f"page-{seq}-{number}.svg"
                file.write_bytes(page if isinstance(page, bytes) else page.encode("utf-8"))
                files.append(str(file))
            payload = {
                "ok": True, "files": files,
                "warnings": [session.problem_json(w) for w in result.warnings],
                "seconds": result.seconds,
                "elements": element_map,
            }
        else:
            payload = {"ok": False, "errors": [session.problem_json(e) for e in result.errors]}
        self.api.emit("build.finished", tab=session.id, ok=payload["ok"], pages=len(payload.get("files", [])),
                      errors=len(payload.get("errors", [])), warnings=len(payload.get("warnings", [])))
        return payload

    def preview(self, player: bool = False, show_breaks: bool = False) -> dict:
        """Build the active adventure's preview now and describe it: its page
        files, warnings or errors. The bridge does the same in two halves,
        off the window's thread (``_run``, then ``_finish``)."""
        session = self.session
        if session.adventure is None:
            return {"ok": False, "errors": []}
        self._seq = getattr(self, "_seq", 0) + 1
        result, element_map = self._run(session, player, show_breaks)
        return self._finish(session, result, element_map, self._seq)

    def export(self, path: str, variant: str = "full") -> dict:
        """Export the active adventure to the given file (F7.6): the adventure
        PDF ("full"), the handouts PDF ("handouts"), or another variant."""
        try:
            if variant == "full":
                return self.session.export_pdf(Path(path))
            return self.session.export_pdf(Path(path), variant=variant)
        except OSError as exc:
            return {"ok": False, "error": self.session.t("error.export.failed", message=str(exc)), "key": "error.export.failed"}
