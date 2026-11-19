"""Heading check: a small extension for trying extensions by hand (design
document F25, T-EXT-16). It reads the open chapter and lists its headings in
a findings list; a click on one goes to its line. It changes nothing."""


def setup(ext):
    @ext.command("list")
    def list_headings(context):
        chapter = context.get("chapter", 0)
        text = ext.call("adventure.chapter", index=chapter)["text"]
        items = [{"text": line.strip(), "chapter": chapter, "line": number}
                 for number, line in enumerate(text.splitlines(), 1) if line.lstrip().startswith("=")]
        ext.findings("headings", items)
        return {"message": f"{len(items)} headings."}
