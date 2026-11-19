"""Make the documentation website's pages (design document F24, 0.7.3, issue #34).

The site is built from text that already lives in the repository, so there is
one master copy of each text and the site is never edited by hand:

    docs/site/zensical.toml   the site's configuration (F24.6)
    docs/site/index.md        the home page
    scriptorum.en strings     the author guides, the same text Help shows (F19)
    docs/API.md               the API reference (F23)
    CHANGELOG.md              the changelog
    open GitHub issues        the Status page (a JSON file the workflow fetches)
    Claret & Ink palette      the site's colours (F16), light and dark
    scriptorum/ui/logo.png    the logo in the header (F9)

Everything is written into a build folder (build/site/ by default), which is
never committed. Zensical then builds the site there:

    python tools/build_site.py --issues issues.json
    zensical build -f build/site/zensical.toml

This script makes no network request: the workflow fetches the issues with
the GitHub API and passes them in as a file. Without --issues the Status page
says the list was not available. Zensical runs only on GitHub, so nothing is
added to the app or its dependencies (F24.6).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "docs" / "site"
STRINGS = ROOT / "scriptorum" / "bundled" / "scriptorum.en" / "strings"
PALETTE = ROOT / "scriptorum" / "bundled" / "scriptorum.claret-and-ink" / "palette.json"
LOGO = ROOT / "scriptorum" / "ui" / "logo.png"
REPOSITORY = "https://github.com/lyzio/Scriptorum"

# Interface-text area (strings/<area>.json) -> page of the site (F24.3).
# Guides in other interface languages can get their own pages later.
GUIDES = {
    "guide-theme": "guides/how-to-write-a-theme.md",
    "guide-game-system": "guides/how-to-write-a-game-system.md",
    "guide-extension": "guides/how-to-write-an-extension.md",   # F25.19 (0.7.5)
}

# Code-block language by the file name a guide gives a block ("```file: x").
LANGUAGES = {".py": "python", ".json": "json", ".css": "css", ".svg": "xml", ".md": "markdown", ".toml": "toml"}

# F24.4: the three lists of the Status page, by the labels already in use.
# An issue labelled "to test" is waiting for the project manager whatever
# else it is, so it is listed only there.
STATUS_LISTS = (
    ("Waiting to be tested", ("to test",),
     "Built and waiting for the project manager to confirm that it works."),
    ("Being looked into", ("bug", "friction"),
     "Bugs, and places where Scriptorum takes more steps than it should."),
    ("Planned features", ("feature", "enhancement"),
     "New functions that are planned or proposed."),
)


# --- the author guides (F24.3) -------------------------------------------------------------------

def guide_markdown(texts: dict) -> str:
    """One guide's interface texts as one Markdown page.

    The texts keep the plain markup the Help viewer draws (paragraphs, "- "
    lists, `code`, **bold** and code blocks), which is Markdown already; only a
    code block's "file: <name>" line becomes the block's title."""
    parts = [f"# {texts['title']}", "", _blocks(texts.get("intro", ""))]
    number = 1
    while f"s{number:02d}.title" in texts:
        parts += ["", f"## {texts[f's{number:02d}.title']}", "",
                  _blocks(texts.get(f"s{number:02d}.body", ""))]
        number += 1
    return "\n".join(parts).rstrip() + "\n"


def _blocks(body: str) -> str:
    out = []
    for line in body.splitlines():
        match = re.match(r"^```file:\s*(.+?)\s*$", line)
        if match:
            name = match.group(1)
            language = LANGUAGES.get(Path(name).suffix.lower(), "text")
            out.append(f'```{language} title="{name}"')
        elif line.strip() == "```" and (not out or not _inside_block(out)):
            out.append("```text")
        else:
            out.append(line)
    return "\n".join(out)


def _inside_block(lines: list) -> bool:
    """Whether the lines so far leave a code block open."""
    return sum(1 for line in lines if line.startswith("```")) % 2 == 1


# --- the Status page (F24.4) ---------------------------------------------------------------------

def planned_for(body: str) -> str:
    """The version or step an issue belongs to, from its status line:
    "Kind: … · Planned: 0.7.0 (step 2) · Status: to test" gives "0.7.0 (step 2)";
    "Planned for **0.7.3** (0.7.0 step 4), …" gives "0.7.3 (0.7.0 step 4)"."""
    first = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    match = re.search(r"Planned:\s*([^·\n]+)", first)
    if not match:
        match = re.search(r"Planned for\s+(.+?)(?:,|\.\s|\.$|$)", first)
    return match.group(1).replace("*", "").strip() if match else ""


def status_markdown(issues) -> str:
    """The Status page from the open issues (a list of GitHub REST issue
    objects), or a short note when the list could not be fetched."""
    lines = ["# Status", "",
             "What is planned, what is being looked into and what is waiting to be tested, "
             f"made from the open [issues on GitHub]({REPOSITORY}/issues) by their labels. "
             "The page is rebuilt whenever an issue is opened, closed, reopened or relabelled, "
             "and once a night.", ""]
    if issues is None:
        lines += ["The list of issues was not available when this page was built.", ""]
        return "\n".join(lines)
    listed = set()
    for title, labels, lead in STATUS_LISTS:
        entries = []
        for issue in sorted(issues, key=lambda item: item.get("number", 0)):
            if "pull_request" in issue or issue.get("state", "open") != "open":
                continue
            names = {(label.get("name") if isinstance(label, dict) else str(label)).lower()
                     for label in issue.get("labels", [])}
            if issue["number"] in listed or not names & set(labels):
                continue
            listed.add(issue["number"])
            text = f"- [#{issue['number']} {_escape(issue.get('title', ''))}]({issue['html_url']})"
            if "to test" in labels:
                when = planned_for(issue.get("body") or "")
                if when:
                    text += f" · {_escape(when)}"
            entries.append(text)
        lines += [f"## {title}", "", lead, ""]
        lines += entries or ["Nothing at the moment."]
        lines.append("")
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Issue text in a list item: Markdown's own characters print as written."""
    return re.sub(r"([\\`*_\[\]<>|])", r"\\\1", text)


# --- colours (F24.5) -----------------------------------------------------------------------------

def palette_css(palette: dict) -> str:
    """The site's colours from the app's palette, light and dark (F16)."""
    def block(selector: str, colours: dict, dark: bool) -> str:
        values = {
            "--md-primary-fg-color": colours["claret"],
            "--md-primary-fg-color--light": colours["claret"],
            "--md-primary-fg-color--dark": colours["claret"],
            "--md-primary-bg-color": colours["on-claret"],
            "--md-primary-bg-color--light": colours["on-claret"],
            "--md-accent-fg-color": colours["teal-text"],
            "--md-accent-fg-color--transparent": colours["teal"] + "1a",
            "--md-accent-bg-color": colours["editor"],
            "--md-default-bg-color": colours["editor"],
            "--md-default-fg-color": colours["text"],
            "--md-default-fg-color--light": colours["text-2"],
            "--md-default-fg-color--lighter": colours["muted"],
            "--md-default-fg-color--lightest": colours["line"],
            "--md-typeset-color": colours["text"],
            "--md-typeset-a-color": colours["claret-text"],
            "--md-code-bg-color": colours["input"],
            "--md-code-fg-color": colours["text-2"],
            "--md-footer-bg-color": colours["bar"],
            "--md-footer-bg-color--dark": colours["sidebar"],
            "--md-footer-fg-color": colours["text"],
            "--md-footer-fg-color--light": colours["muted"],
            # The header in the app window's own colour, as the menu bar is.
            "--scriptorum-window": colours["window"],
            "--scriptorum-text": colours["text"],
            "--scriptorum-line": colours["line"],
        }
        body = "\n".join(f"  {name}: {value};" for name, value in values.items())
        return f"{selector} {{\n{body}\n}}\n"

    return ("/* The site's colours, made by tools/build_site.py from the app's palette\n"
            "   Claret & Ink (F16, F24). Do not edit: change the palette instead. */\n\n"
            + block('[data-md-color-scheme="default"]', palette["light"], False) + "\n"
            + block('[data-md-color-scheme="slate"]', palette["dark"], True) + "\n"
            "/* The header and tabs in the app window's colour, like its menu bar (F16). */\n"
            ".md-header, .md-tabs { background-color: var(--scriptorum-window); color: var(--scriptorum-text);\n"
            "  border-bottom: 1px solid var(--scriptorum-line); }\n"
            "/* The logo is drawn straight on the header, with no card (F9). */\n"
            ".md-header__button.md-logo img { height: 2rem; width: auto; }\n")


# --- the whole site ------------------------------------------------------------------------------

def build(out: Path, issues_file: Path | None = None) -> Path:
    """Write the site's configuration and pages into out; return out."""
    if out.exists():
        shutil.rmtree(out)
    docs = out / "docs"
    (docs / "guides").mkdir(parents=True)
    (docs / "assets").mkdir()
    (docs / "stylesheets").mkdir()
    shutil.copyfile(SITE_SOURCE / "zensical.toml", out / "zensical.toml")
    shutil.copyfile(SITE_SOURCE / "index.md", docs / "index.md")
    for area, page in GUIDES.items():
        texts = json.loads((STRINGS / f"{area}.json").read_text("utf-8"))
        (docs / page).write_text(guide_markdown(texts), "utf-8")
    shutil.copyfile(ROOT / "docs" / "API.md", docs / "api.md")
    shutil.copyfile(ROOT / "CHANGELOG.md", docs / "changelog.md")
    issues = None
    if issues_file is not None:
        issues = json.loads(Path(issues_file).read_text("utf-8"))
        # `gh api --paginate --slurp` gives one list per page.
        if issues and all(isinstance(page, list) for page in issues):
            issues = [issue for page in issues for issue in page]
    (docs / "status.md").write_text(status_markdown(issues), "utf-8")
    palette = json.loads(PALETTE.read_text("utf-8"))
    (docs / "stylesheets" / "scriptorum.css").write_text(palette_css(palette), "utf-8")
    shutil.copyfile(LOGO, docs / "assets" / "logo.png")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Make the documentation website's pages (F24).")
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "site",
                        help="build folder (default build/site)")
    parser.add_argument("--issues", type=Path, default=None,
                        help="the open issues as JSON, from the GitHub REST API")
    args = parser.parse_args(argv)
    out = build(args.out, args.issues)
    print(f"Site pages written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
