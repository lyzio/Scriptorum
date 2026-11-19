"""0.7.3 (0.7.0 step 4, outcomes approved 18 November 2026).

T-UI-58     the new logo: line art on a transparent background, no card (F9)
T-DOC-01    the website's configuration: pages, look, search (F24)
T-DOC-02    the guide pages are made from the interface-language module (F24)
T-DOC-03    the Status page from the open issues (F24)
T-DOC-04    the website's workflow (F24, T-REL-15)
T-DOC-05    the whole site builds with Zensical (F24)
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scriptorum.core.i18n import Strings
from scriptorum.core.modules import Library
from scriptorum.core.recent import RecentFiles
from scriptorum.core.session import Session
from tests.test_m6c2 import BUNDLED

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
STRINGS = BUNDLED / "scriptorum.en" / "strings"
LOGO_SHA256 = "4d2c245b9ef6ac51e5c93f85d935b1d65ceca549ecd766b53eb01db2c8cbf585"


def _site_tool():
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "tools" / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _issue(number, title, labels, body="", pull=False, state="open"):
    issue = {"number": number, "title": title, "state": state, "body": body,
             "html_url": f"https://github.com/lyzio/Scriptorum/issues/{number}",
             "labels": [{"name": name} for name in labels]}
    if pull:
        issue["pull_request"] = {"url": "x"}
    return issue


# --- T-UI-58 the new logo -----------------------------------------------------------------------

@pytest.mark.unit
def test_T_UI_58_logo_files():
    """T-UI-58: docs/logo/ holds the 832 × 832 line-art original with its
    recorded checksum; the app's 512-pixel copy has an alpha channel and
    transparent corners; the README starts with it; the file icons stay."""
    from PySide6.QtGui import QImage

    original = ROOT / "docs" / "logo" / "scriptorum-logo.png"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == LOGO_SHA256
    big = QImage(str(original))
    assert (big.width(), big.height()) == (832, 832) and big.hasAlphaChannel()
    copy = QImage(str(ROOT / "scriptorum" / "ui" / "logo.png"))
    assert (copy.width(), copy.height()) == (512, 512) and copy.hasAlphaChannel()
    for x, y in ((0, 0), (511, 0), (0, 511), (511, 511)):
        assert copy.pixelColor(x, y).alpha() == 0, (x, y)
    readme = (ROOT / "README.md").read_text("utf-8")
    assert readme.startswith('<p align="center"><img src="scriptorum/ui/logo.png"')
    note = (ROOT / "docs" / "logo" / "README.md").read_text("utf-8")
    assert "832 × 832" in note and "transparent" in note and "CC BY-SA 4.0" in note
    for icon in ("scriptorum.png", "scav.png", "scmod.png"):
        assert (ROOT / "packaging" / "icons" / icon).is_file()
    css = (ROOT / "scriptorum" / "ui" / "styles.css").read_text("utf-8")
    assert "logo-card" not in css
    html = (ROOT / "scriptorum" / "ui" / "index.html").read_text("utf-8")
    assert "logo-card" not in html and html.count('src="logo.png"') == 2


@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from scriptorum.app.main import MainWindow
    from tests.test_ui_smoke import Driver

    folder = tmp_path_factory.mktemp("ui-step4")
    library = Library(folder / "library")
    library.install_bundled(BUNDLED)
    app = QApplication.instance() or QApplication([])
    session = Session(library, Strings.from_library(library), RecentFiles(folder / "recent.json"), folder / "build",
                      home=folder / "home")
    window = MainWindow(session, headless_test=True)
    window.bridge.confirm_discard = lambda: True
    window.resize(1440, 900)
    window.show()
    driver = Driver(app, window)
    driver.wait_until(lambda: window.bridge.ui_ready, 60)
    yield driver
    window.close()


def _plain(ui, selector: str) -> None:
    """The logo is drawn straight on the window: no rounding, border or shadow."""
    style = f"getComputedStyle(document.querySelector('{selector}'))"
    assert ui.js(f"parseFloat({style}.borderTopLeftRadius)") == 0
    assert ui.js(f"parseFloat({style}.borderTopWidth)") == 0
    assert ui.js(f"{style}.boxShadow") == "none"
    assert ui.js(f"{style}.backgroundColor") in ("rgba(0, 0, 0, 0)", "transparent")


@pytest.mark.ui
def test_T_UI_58_logo_in_the_windows(ui):
    """T-UI-58: the welcome screen, About (light and dark) and the start-up
    window show the line-art logo straight on the window's background, with
    the description "Scriptorum logo"."""
    logo = "#welcome .welcome-logo"
    ui.wait_until(lambda: ui.js(f"document.querySelector('{logo}').complete && "
                                f"document.querySelector('{logo}').naturalWidth") == 512, 10)
    assert ui.js(f"document.querySelector('{logo}').alt") == "Scriptorum logo"
    _plain(ui, logo)
    for mode in ("light", "dark"):
        ui.window.bridge.session.app_settings.update({"mode": mode})
        ui.run("window.__scriptorum.about.openAbout()")
        about = "#about-dialog .about-logo"
        ui.wait_until(lambda: ui.js(f"document.querySelector('{about}').naturalWidth") == 512, 10)
        assert ui.js(f"document.querySelector('{about}').alt") == "Scriptorum logo"
        _plain(ui, about)
        ui.js("document.getElementById('about-close').click(); true")
    ui.window.bridge.session.app_settings.update({"mode": "system"})
    from scriptorum.app.startup_window import LOGO_SIZE, StartupWindow, logo_pixmap
    from scriptorum.core.startup import Startup, bundled_strings
    window = StartupWindow(Startup(), bundled_strings(), "0.7.3")
    assert not window.logo.pixmap().isNull() and window.logo.accessibleName() == "Scriptorum logo"
    image = logo_pixmap(LOGO_SIZE, 1.0).toImage()
    assert image.width() == LOGO_SIZE and image.pixelColor(0, 0).alpha() == 0
    # No card: the window shows through the picture's background (the old
    # parchment card was opaque inside its rounded corners).
    see_through = sum(1 for x in range(0, LOGO_SIZE, 4) for y in range(0, LOGO_SIZE, 4)
                      if image.pixelColor(x, y).alpha() == 0)
    assert see_through > 0.2 * (LOGO_SIZE // 4) ** 2
    window.close()


# --- T-DOC-01 the site's configuration ----------------------------------------------------------

@pytest.mark.unit
def test_T_DOC_01_configuration(tmp_path):
    """T-DOC-01: the site is lyzio.github.io/Scriptorum with the guides, the API
    reference, the changelog and Status (not the design document or the test
    plan); light and dark follow the reader's system; search and a sidebar;
    the logo in the header; the colours are the app's palette."""
    tool = _site_tool()
    out = tool.build(tmp_path / "site")
    config = (out / "zensical.toml").read_text("utf-8")
    assert 'site_url = "https://lyzio.github.io/Scriptorum/"' in config
    pages = re.findall(r'= "([\w/.-]+\.md)"', config)
    # Corrected for 0.7.5: the third guide, How to write an extension (F25.19).
    assert pages == ["index.md", "guides/how-to-write-a-theme.md", "guides/how-to-write-a-game-system.md",
                     "guides/how-to-write-an-extension.md", "api.md", "changelog.md", "status.md"]
    for page in pages:
        assert (out / "docs" / page).is_file(), page
    # The page list above is the whole site: no design document or test plan.
    assert not [name for name in (out / "docs").rglob("*") if "design" in name.name or "test" in name.name]
    assert '"(prefers-color-scheme: light)"' in config and '"(prefers-color-scheme: dark)"' in config
    assert 'scheme = "slate"' in config and "navigation.sections" in config and "search.highlight" in config
    assert 'logo = "assets/logo.png"' in config
    assert (out / "docs" / "assets" / "logo.png").read_bytes() == (ROOT / "scriptorum" / "ui" / "logo.png").read_bytes()
    css = (out / "docs" / "stylesheets" / "scriptorum.css").read_text("utf-8")
    palette = json.loads((BUNDLED / "scriptorum.claret-and-ink" / "palette.json").read_text("utf-8"))
    light, dark = css.split('[data-md-color-scheme="slate"]')
    assert f"--md-primary-fg-color: {palette['light']['claret']};" in light
    assert f"--md-default-bg-color: {palette['light']['editor']};" in light
    assert f"--md-default-fg-color: {palette['dark']['text']};" in dark
    assert f"--md-typeset-a-color: {palette['dark']['claret-text']};" in dark
    assert (out / "docs" / "api.md").read_bytes() == (ROOT / "docs" / "API.md").read_bytes()
    assert (out / "docs" / "changelog.md").read_bytes() == (ROOT / "CHANGELOG.md").read_bytes()


# --- T-DOC-02 the guide pages -------------------------------------------------------------------

@pytest.mark.unit
def test_T_DOC_02_guides_from_the_language_module(tmp_path):
    """T-DOC-02: each guide page is made from its strings/<area>.json, the text
    Help shows: every section's heading and body in order; a code block's
    file name becomes its title; nothing generated is kept in the repository."""
    tool = _site_tool()
    out = tool.build(tmp_path / "site")
    for area, page in (("guide-theme", "how-to-write-a-theme"), ("guide-game-system", "how-to-write-a-game-system"),
                       ("guide-extension", "how-to-write-an-extension")):   # the third from 0.7.5
        texts = json.loads((STRINGS / f"{area}.json").read_text("utf-8"))
        markdown = (out / "docs" / "guides" / f"{page}.md").read_text("utf-8")
        assert markdown.startswith(f"# {texts['title']}\n")
        position = 0
        number = 1
        while f"s{number:02d}.title" in texts:
            heading = f"\n## {texts[f's{number:02d}.title']}\n"
            assert markdown.find(heading, position) > position, heading
            position = markdown.find(heading, position)
            number += 1
        assert number > 5
        # Every word of every body is on the page; only "file:" lines differ.
        for key, value in texts.items():
            for line in value.splitlines():
                if not line.startswith("```"):
                    assert line in markdown, (area, key, line)
        assert "```file:" not in markdown and markdown.count("```") % 2 == 0
    theme = (out / "docs" / "guides" / "how-to-write-a-theme.md").read_text("utf-8")
    assert '```json title="module.json"' in theme
    # One master copy: no generated page is in the repository.
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert not [name for name in tracked if name.startswith("build/") or name.endswith("how-to-write-a-theme.md")
                and not name.startswith("tools/guides/")]
    assert "build/" in (ROOT / ".gitignore").read_text("utf-8").split()


# --- T-DOC-03 the Status page -------------------------------------------------------------------

@pytest.mark.unit
def test_T_DOC_03_status_page():
    """T-DOC-03: three lists from the open issues by their labels: planned
    features (feature, enhancement), being looked into (bug, friction) and
    waiting to be tested (to test, with its version or step); each links to
    its issue; unlabelled issues, closed ones and pull requests are left out."""
    tool = _site_tool()
    issues = [
        _issue(1, "A wish", ["feature"]),
        _issue(2, "Another wish", ["enhancement", "accessibility"]),
        _issue(3, "Broken thing", ["bug"]),
        _issue(4, "Too many steps", ["friction"]),
        _issue(5, "Fixed, please try", ["bug", "to test"], "Kind: bug · Planned: 0.7.0 (step 2) · Status: to test"),
        _issue(6, "Older form", ["feature", "to test"], "Planned for **0.7.3** (0.7.0 step 4), on `build/0.7.0`."),
        _issue(7, "No label", []),
        _issue(8, "Only another label", ["accessibility"]),
        _issue(9, "A pull request", ["feature"], pull=True),
        _issue(10, "Closed", ["bug"], state="closed"),
        _issue(11, "Stars *and* [brackets]", ["bug"]),
    ]
    page = tool.status_markdown(issues)
    sections = dict(re.findall(r"## ([^\n]+)\n(.*?)(?=\n## |\Z)", page, re.S))
    assert set(sections) == {"Planned features", "Being looked into", "Waiting to be tested"}

    def numbers(name):
        return [int(n) for n in re.findall(r"\[#(\d+) ", sections[name])]
    assert numbers("Planned features") == [1, 2]
    assert numbers("Being looked into") == [3, 4, 11]
    assert numbers("Waiting to be tested") == [5, 6]
    assert "(https://github.com/lyzio/Scriptorum/issues/5) · 0.7.0 (step 2)" in sections["Waiting to be tested"]
    assert "(https://github.com/lyzio/Scriptorum/issues/6) · 0.7.3 (0.7.0 step 4)" in sections["Waiting to be tested"]
    assert r"Stars \*and\* \[brackets\]" in sections["Being looked into"]
    for left_out in ("No label", "Only another label", "A pull request", "Closed"):
        assert left_out not in page
    empty = tool.status_markdown([])
    assert empty.count("Nothing at the moment.") == 3
    assert "was not available" in tool.status_markdown(None)


@pytest.mark.unit
def test_T_DOC_03_issues_file(tmp_path):
    """T-DOC-03: the workflow's file (one list per page of the API) gives the
    same page as one list."""
    tool = _site_tool()
    pages = [[_issue(1, "A wish", ["feature"])], [_issue(3, "Broken", ["bug"])]]
    (tmp_path / "issues.json").write_text(json.dumps(pages), "utf-8")
    out = tool.build(tmp_path / "site", tmp_path / "issues.json")
    status = (out / "docs" / "status.md").read_text("utf-8")
    assert status == tool.status_markdown([issue for page in pages for issue in page])


# --- T-DOC-04 the workflow ----------------------------------------------------------------------

@pytest.mark.unit
def test_T_DOC_04_workflow():
    """T-DOC-04: rebuilt on every merge into main, on issues opened, closed,
    reopened or relabelled, nightly and by hand; Zensical pinned; every action
    pinned to a commit SHA; published with Pages from main only, no branch of
    built pages; only the deploy job may write, and only to Pages; nothing is
    added to the app's dependencies."""
    text = WORKFLOW.read_text("utf-8")
    top, jobs = text.split("\njobs:", 1)
    assert 'push:\n    branches: ["main"]' in top
    assert "types: [opened, closed, reopened, labeled, unlabeled]" in top
    assert "schedule:" in top and "cron:" in top and "workflow_dispatch:" in top
    assert "permissions:\n  contents: read" in top
    assert '"zensical==0.1.2"' in jobs and "tools/build_site.py --issues issues.json" in jobs
    assert "zensical build --strict -f build/site/zensical.toml" in jobs
    assert "actions/upload-pages-artifact@" in jobs and "actions/deploy-pages@" in jobs
    assert "path: build/site/site" in jobs and "if: github.ref == 'refs/heads/main'" in jobs
    assert "gh-pages" not in text and "git push" not in text and "secrets." not in text
    build, deploy = jobs.split("\n  deploy:", 1)
    assert "write" not in build and "persist-credentials: false" in build
    assert "pages: write" in deploy and "id-token: write" in deploy and "contents: write" not in deploy
    for line in text.splitlines():
        if "uses:" in line and not line.strip().startswith("#"):
            assert re.search(r"@[0-9a-f]{40}  # v\d+\.\d+\.\d+$", line), line
    pyproject = (ROOT / "pyproject.toml").read_text("utf-8")
    assert "zensical" not in pyproject.lower()
    assert not list((ROOT / "scriptorum").rglob("*zensical*"))


# --- T-DOC-05 the whole site --------------------------------------------------------------------

@pytest.mark.integration
def test_T_DOC_05_site_builds(tmp_path):
    """T-DOC-05: the site builds with Zensical in strict mode, with every page,
    the search index, the logo and the colours. Zensical runs only on GitHub
    (F24), so this test runs where it is installed and is skipped elsewhere."""
    if importlib.util.find_spec("zensical") is None:
        pytest.skip("Zensical is not installed (it runs only on GitHub, F24)")
    tool = _site_tool()
    issues = [_issue(3, "Broken thing", ["bug"])]
    (tmp_path / "issues.json").write_text(json.dumps(issues), "utf-8")
    out = tool.build(tmp_path / "site", tmp_path / "issues.json")
    result = subprocess.run([sys.executable, "-m", "zensical", "build", "--strict", "-f", str(out / "zensical.toml")],
                            cwd=out, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    site = out / "site"
    for page in ("index.html", "guides/how-to-write-a-theme/index.html", "guides/how-to-write-a-game-system/index.html",
                 "guides/how-to-write-an-extension/index.html",
                 "api/index.html", "changelog/index.html", "status/index.html"):
        assert (site / page).is_file(), page
    assert (site / "search.json").stat().st_size > 10_000
    assert (site / "assets" / "logo.png").is_file() and (site / "stylesheets" / "scriptorum.css").is_file()
    home = (site / "index.html").read_text("utf-8")
    assert "assets/logo.png" in home and "stylesheets/scriptorum.css" in home
    assert "prefers-color-scheme: dark" in home
    assert "Broken thing" in (site / "status" / "index.html").read_text("utf-8")
    assert not list(site.rglob("*design*")) and not list(site.rglob("*test-plan*"))
    # T-DOC-07 (0.7.6): the sidebar's last entry leaves the site for the newest release.
    assert f'href="{LATEST_RELEASE}"' in home
    assert not (site / "latest-release").exists() and not (site / "releases").exists()
    shutil.rmtree(out)


# --- T-DOC-07 the Latest release link -----------------------------------------------------------

LATEST_RELEASE = "https://github.com/lyzio/Scriptorum/releases/latest"


@pytest.mark.unit
def test_T_DOC_07_latest_release_link(tmp_path):
    """T-DOC-07: the sidebar ends with a link named Latest release, after
    Status, to the repository's releases/latest address; it is the only entry
    that leaves the site, and no page is made for it (F24, 0.7.6)."""
    import tomllib
    tool = _site_tool()
    out = tool.build(tmp_path / "site")
    nav = tomllib.loads((out / "zensical.toml").read_text("utf-8"))["project"]["nav"]

    def entries(items):
        for item in items:
            ((name, target),) = item.items()
            if isinstance(target, list):
                yield from entries(target)
            else:
                yield name, target
    flat = list(entries(nav))
    assert flat[-2:] == [("Status", "status.md"), ("Latest release", LATEST_RELEASE)]
    assert list(nav[-1].items()) == [("Latest release", LATEST_RELEASE)]   # at the top level, last
    leaving = [(name, target) for name, target in flat if not target.endswith(".md")]
    assert leaving == [("Latest release", LATEST_RELEASE)]
    # No page is made for it: the pages written are exactly the .md entries.
    written = sorted(p.relative_to(out / "docs").as_posix() for p in (out / "docs").rglob("*.md"))
    assert written == sorted(target for _, target in flat if target.endswith(".md"))
    # The in-app Help is unchanged: no guide text names the address.
    for area in tool.GUIDES:
        assert "releases/latest" not in (STRINGS / f"{area}.json").read_text("utf-8")
