"""0.7.7 (on build/0.7.0): a full-width section never covers what stands in a
column (issue #30, F7.4), pasted knowledge lines become Information in the
person card (issue #33, F4), and the Box is the only frame for the elements
in it (issue #31, 11.10). Test Plan: T-BUILD-34, T-UI-59, T-LOOK-14."""

from __future__ import annotations

import io
import json
import re
import struct
import zlib

import pytest
from pypdf import PdfReader

from tests.conftest import pack_sample
from tests.test_m6c2 import BUNDLED, _lines
from tests.test_step3 import _open, _text, ui  # noqa: F401  (the window fixture)

THEMES = ("scriptorum.vaesen", "scriptorum.plain", "scriptorum.legends-and-lattes", "scriptorum.call-of-cthulhu")


def _png(w: int, h: int, rgb=(200, 120, 120)) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _pages(pdf: bytes) -> list:
    return [_lines(page) for page in PdfReader(io.BytesIO(pdf)).pages]


# --- T-BUILD-34 a full-width section never covers a column ----------------------------------------

def _build(session, chapter: str) -> bytes:
    session.set_chapter_text(0, chapter)
    result = session.build("pdf")
    assert result.ok, result.errors
    return result.output[0]


def _not_covered(pdf: bytes, column_word: str, wide_word: str) -> int:
    """On every page that holds both, no text of the column's element lies
    within the height the full-width section takes; return how many pages
    hold both."""
    both = 0
    for runs in _pages(pdf):
        col = [y for t, x, y in runs if column_word in t]
        wide = [y for t, x, y in runs if wide_word in re.sub(r"\s", "", t)]
        if not col or not wide:
            continue
        both += 1
        top, bottom = max(wide), min(wide)
        inside = [y for y in col if bottom - 2 <= y <= top + 2]
        assert not inside, (column_word, wide_word, inside, top, bottom)
    return both


@pytest.mark.integration
@pytest.mark.parametrize("theme", THEMES)
def test_T_BUILD_34_full_width_never_covers_a_column(session, tmp_path, theme):
    """T-BUILD-34: on a two-column page a full-width section after a tall
    map in a column (with its key), holding another map or text, takes its
    own room: the column map, its key and a tall framed Box are never drawn
    under it; what does not fit beside it moves on whole (issue #30)."""
    session.open(pack_sample("m3-world", tmp_path))
    if theme != "scriptorum.vaesen":
        session.set_theme(theme)
    session.set_settings({"page": {"columns": 2, "orientation": "portrait"}})
    tall = session.create_map("Colmap", "tall.png", _png(140, 200))["id"]
    wide = session.create_map("Widemap", "wide.png", _png(220, 140, (120, 120, 200)))["id"]
    for made, word in ((tall, "Colplace"), (wide, "Wideplace")):
        pins = [{"type": "pin", "x": 0.1 + 0.15 * i, "y": 0.3, "text": f"{word}{i + 1}"} for i in range(5)]
        session.update_map({"id": made, "layers": [{"name": "L", "show_in_handout": True, "items": pins}]})
    original = session.adventure.chapter_text(session.adventure.chapters[0])

    # A map in a column, then a full-width section holding another map: the
    # case of the issue. The wide map's label and key mark its room.
    pdf = _build(session, f'#map(map: "{tall}")\n\n#full-width[\n#map(map: "{wide}")\n]\n\n' + original)
    text = "".join(t for runs in _pages(pdf) for t, _, _ in runs)
    assert all(f"Colplace{i}" in text and f"Wideplace{i}" in text for i in range(1, 6))
    _not_covered(pdf, "Colplace", "Wideplace")
    _not_covered(pdf, "Colplace", "WIDEMAP")

    # The same with text in the full-width section.
    words = " ".join(["Widewords"] * 120)
    pdf = _build(session, f'#map(map: "{tall}")\n\n#full-width[\n{words}\n]\n\n' + original)
    assert _not_covered(pdf, "Colplace", "Widewords") >= 0

    # A tall framed Box in a column (a block that measures itself) beside it.
    lines = "\n\n".join(f"Boxline{i} of the keeper's rule." for i in range(40))
    pdf = _build(session, f'#box(title: "Rule")[\n{lines}\n]\n\n#full-width[\n#map(map: "{wide}")\n]\n\n' + original)
    _not_covered(pdf, "Boxline", "Wideplace")
    assert all(f"Boxline{i} " in "".join(t + " " for runs in _pages(pdf) for t, _, _ in runs) for i in (0, 39))
    session.set_chapter_text(0, original)


@pytest.mark.unit
def test_T_BUILD_34_every_unbreakable_element_is_shielded():
    """T-BUILD-34: the core element kit sets every element a theme draws as an
    unbreakable block as one box of its measured size (F7.4, issue #30), and
    so does a never-split section."""
    core = (BUNDLED / "scriptorum.core" / "typst" / "elements.typ").read_text("utf-8")
    shield = core[core.index("#let _shield(it)"):core.index("// 11.1: scenes are numbered automatically.")]
    assert 'it.at("breakable", default: true) == false' in shield
    assert "measure(it, width: size.width).height" in shield and "box(width: size.width, height: h, it)" in shield
    assert "shielded.insert(kind, (..args) => _shield(render(..args)))" in core
    assert "_shield(block(width: 100%, breakable: false, _framed(body)))" in core


# --- T-LOOK-14 elements inside a Box ---------------------------------------------------------------

PARTS = """#information(variant: "public")[Publicin no boat has gone out.]

#information(variant: "secret")[Secretin the light is a lantern.]

#information(variant: "hint")[Hintin look under the jetty.]

#read-aloud[Readin fog lies thick over the water.]

#check(roll: "Vigilance", difficulty: "hard")[Checkin notice the bell.]

#dice(dice: "D6")[Dicein on a six the bell rings.]

#pacing[Pacingin about twenty minutes.]
"""
PERSON = '#person(name: "Personin", mood: "Calm", description: "Keeps the light.")[]\n'
KINDS = ("Public", "Secret", "Hint", "Read", "Check", "Dice", "Pacing")


def _box_chapter() -> str:
    return ('= Box test\n\n#box(title: "Inside")[\n' + PARTS + "\n" + PERSON + "]\n\n"
            + PARTS.replace("in ", "out ") + "\n" + PERSON.replace("Personin", "Personout"))


def _ys(runs, suffix: str) -> list:
    return [next(y for t, _, y in runs if t.startswith(kind + suffix)) for kind in KINDS]


@pytest.mark.integration
@pytest.mark.parametrize("theme", THEMES)
def test_T_LOOK_14_elements_inside_a_box(session, tmp_path, theme):
    """T-LOOK-14: inside a Box, Information of each variant, read-aloud,
    check, dice and pacing note lose their own frame and are separated by
    thin lines; each keeps its label; the person card keeps its frame;
    outside a Box they print as before; the accessible PDF is made (11.10)."""
    session.open(pack_sample("m4-look", tmp_path))
    if theme != "scriptorum.vaesen":
        session.set_theme(theme)
    original = session.adventure.chapter_text(session.adventure.chapters[0])
    pdf = _build(session, _box_chapter())
    runs = [r for page in _pages(pdf) for r in page if r]
    joined = re.sub(r"\s", "", "".join(t for t, _, _ in runs)).upper()
    for word in ("PUBLIC", "SECRET", "HINT", "READALOUD", "CHECK", "VIGILANCE"):
        assert joined.count(word) >= 2, word        # the label inside and outside the Box
    page = next(p for p in _pages(pdf) if any(t.startswith("Publicin") for t, _, _ in p))
    inside = _ys(page, "in")
    assert inside == sorted(inside, reverse=True)   # in the order written, top to bottom
    # Without frames the parts sit closer together than the framed elements
    # outside the Box (the secret box alone is taller than two parts).
    span_in = inside[0] - inside[-1]
    outside_pages = [p for p in _pages(pdf) if any(t.startswith("Publicout") for t, _, _ in p)]
    if len(outside_pages) == 1 and all(any(t.startswith(k + "out") for t, _, _ in outside_pages[0]) for k in KINDS):
        outside = _ys(outside_pages[0], "out")
        if outside == sorted(outside, reverse=True):
            assert span_in < outside[0] - outside[-1], (span_in, outside)
    assert any(t.startswith("Personin") or "PERSONIN" in t for t, _, _ in runs)

    # The accessible PDF is made, with the parts' labels and text as text.
    reply = session.export_pdf(tmp_path / "a.pdf", variant="accessible")
    assert reply["ok"], reply
    tagged = re.sub(r"\s", "", "".join(p.extract_text() for p in PdfReader(str(tmp_path / "a.pdf")).pages)).upper()
    for word in ("PUBLICINNOBOAT", "SECRETINTHELIGHT", "READIN", "CHECKIN", "PACINGIN"):
        assert word in tagged, word
    session.set_chapter_text(0, original)


@pytest.mark.unit
def test_T_LOOK_14_templates():
    """T-LOOK-14: in every theme the Box marks its text, the five kinds draw
    their frameless part inside it, and person and creature cards do not."""
    for theme in THEMES:
        folder = BUNDLED / theme / "templates"
        style = (folder / "_style.typ").read_text("utf-8")
        assert "#let inside-box(body)" in style and "#let in-box() = math.cases.gap == box-mark" in style, theme
        assert "#let box-part(head, body, fill: none)" in style and "#let box-pacing(body)" in style, theme
        assert "inside-box(labelize(body))" in (folder / "box.typ").read_text("utf-8"), theme
        for kind in ("information", "read-aloud", "check", "dice", "pacing"):
            assert "in-box()" in (folder / f"{kind}.typ").read_text("utf-8"), (theme, kind)
        for kind in ("person", "creature"):
            assert "in-box" not in (folder / f"{kind}.typ").read_text("utf-8"), (theme, kind)


# --- T-UI-59 pasted knowledge lines -----------------------------------------------------------------

KNOWING = """PERSON: Lovisa Berg
Mood: Restless
She knows (public): No boat has gone out since Sunday.
Hon vet (hemlig): Brodern hördes i dimman.
Knows: The bell rings at dawn.
Remember: the tide turns at noon."""


def _paste(ui, lines: str):
    ui.js("document.querySelector('#visual .el-scene .para').focus(); true")
    ui.run("window.__scriptorum.insert('paragraph')")
    ui.wait(200)
    ui.js(f"""(() => {{ const p = document.activeElement; const dt = new DataTransfer(); dt.setData('text/plain', {json.dumps(lines)});
        p.dispatchEvent(new ClipboardEvent('paste', {{clipboardData: dt, bubbles: true, cancelable: true}})); return true; }})()""")
    ui.wait(300)
    ui.run("window.__scriptorum.flush()")


def _convert(ui, start: str, kind: str):
    path = json.loads(ui.js(f"""JSON.stringify((() => {{ const walk = (blocks, path) => {{
        for (let i = 0; i < blocks.length; i++) {{ const b = blocks[i];
          if (b.type === 'paragraph' && (b.text || '').startsWith({json.dumps(start)})) return [...path, i];
          if (b.body && b.body.blocks) {{ const f = walk(b.body.blocks, [...path, i]); if (f) return f; }} }}
        return null; }}; return walk(window.__scriptorum.state().doc.blocks, []); }})())"""))
    assert path, start
    ui.js(f"window.__scriptorum.convert({json.dumps(path)}, {json.dumps(kind)}); true")
    ui.wait(250)


def _card(text: str) -> str:
    start = text.index('#person(name: "Lovisa Berg"')
    return text[start:text.index("\n]", start) + 2]


@pytest.mark.ui
def test_T_UI_59_knowledge_lines_into_the_card(ui):
    """T-UI-59: when a pasted line is converted to a person, the lines after
    it that start with "She knows", "Hon vet", "Knows" (and the others)
    become Information inside the card, with the variant from the brackets
    and the default one without; the label goes; Mood fills its field; the
    plain line after them stays; one undo brings every line back (issue #33)."""
    _open(ui, "m1-basic", "knows")
    _paste(ui, KNOWING)
    _convert(ui, "PERSON:", "person")
    text = _text(ui)
    card = _card(text)
    assert card.startswith('#person(name: "Lovisa Berg", mood: "Restless")[')
    assert '#information(variant: "public")[No boat has gone out since Sunday.]' in card
    assert '#information(variant: "secret")[Brodern hördes i dimman.]' in card
    # Without brackets: the default variant of Information (secret).
    plain = re.search(r'#information(?:\(variant: "(\w+)"\))?\[The bell rings at dawn\.\]', card)
    assert plain and plain.group(1) in (None, "secret"), card
    assert "knows" not in card.lower() and "Hon vet" not in card and "Mood:" not in text
    assert "Remember: the tide turns at noon." in text and "Remember" not in card
    # One undo brings the pasted lines back.
    ui.run("window.__scriptorum.undo()")
    text = _text(ui)
    assert "PERSON: Lovisa Berg" in text and "She knows (public): No boat has gone out since Sunday." in text
    assert "Hon vet (hemlig): Brodern hördes i dimman." in text and "Knows: The bell rings at dawn." in text


@pytest.mark.ui
def test_T_UI_59_he_knows_han_vet_vet(ui):
    """T-UI-59: "He knows", "Han vet" and "Vet" count too, a list marker
    before them goes, and "(publik)" is Public."""
    _open(ui, "m1-basic", "knows-2")
    _paste(ui, "PERSON: Lovisa Berg\n- He knows (secret): One.\nHan vet (publik): Två.\nVet: Tre.\nVetenskap: stays.")
    _convert(ui, "PERSON:", "person")
    text = _text(ui)
    card = _card(text)
    assert '#information(variant: "secret")[One.]' in card and '#information(variant: "public")[Två.]' in card
    assert re.search(r'#information(?:\(variant: "secret"\))?\[Tre\.\]', card), card
    assert "Vetenskap: stays." in text and "Vetenskap" not in card
