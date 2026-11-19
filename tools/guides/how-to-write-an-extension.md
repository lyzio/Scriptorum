# How to write an extension

An extension adds functions to Scriptorum with its own program code: a check that lists problems in the text, a helper that tidies something up, or a link to a service such as a writing assistant. It never changes how an adventure prints; that stays with game systems and themes. This guide shows how to write one in Python, step by step. You need a text editor and a little Python. You do not need to read Scriptorum's code.

## What an extension is and what it may do

An extension is a module of kind extension. Like a theme it is a folder with a module.json manifest, packed as a .scmod file to share. Unlike every other module it may hold Python files.

Scriptorum keeps the author in charge of what an extension does:

- Before it is installed, the author sees what it needs: which parts of the adventure it reads, whether it changes the adventure, and which addresses on the internet it connects to. It is installed only if the author agrees, and an update that needs more asks again.
- An installed extension does nothing until the author switches it on in Settings ▸ Extensions.
- It runs in a program of its own, not inside Scriptorum, so a mistake in it cannot freeze or break the app. If it crashes, or does not answer within 30 seconds, Scriptorum says so and carries on; after three failures in one session it is switched off.
- It reaches the adventure only through Scriptorum's internal API, and only as far as it declared.

An extension may:

- add items to an Extensions menu, and actions to a block's right-click menu
- read the text, the codex or the adventure's settings
- show findings, pictures and suggestions in its own section of the Extensions tab, at the bottom of the left pane
- suggest changes, which the author accepts or rejects
- change the text directly, when the author asks it to
- connect to the internet, to the addresses it declared, while the author allows connections

An extension may not draw its own windows or reach the app's web page: Scriptorum draws everything in its own style. It may not install anything on the computer, and it may hold no compiled code.

## The folder and its manifest

An extension is a folder with at least two files:

```
my-extension/
  module.json        the manifest
  extension.py       the code, with a setup(ext) function
```

The manifest has the fields every module has, plus what an extension needs:

```
{
  "id": "yourname.my-extension",
  "kind": "extension",
  "name": "My extension",
  "version": "1.0.0",
  "format": 1,
  "app": "1.0.0",
  "licence": "GPL-3.0-or-later",
  "authors": ["Your name"],
  "description": "One or two sentences on what it does.",
  "requires": [{"id": "api", "version": "1.x"}],
  "main": "extension.py",
  "needs": {"reads": ["text"], "changes": "none", "network": []},
  "settings": [],
  "menu": [{"id": "check", "label": "Check the text"}],
  "block_actions": [],
  "panels": [{"id": "found", "type": "findings", "title": "Found"}]
}
```

- **id** starts with your own prefix, as for every module. The prefix scriptorum is kept for the modules that come with the app.
- **requires** names the version of Scriptorum's internal API the extension was written for. Write 1.x to work with every 1.something version.
- **main** is the Python file Scriptorum starts.
- **licence** must allow the code to run together with Scriptorum's GPL licence: GPL, LGPL, MIT, BSD, Apache 2.0 and MPL 2.0 all do. Any other licence is refused.

## What it needs

The needs are what the author reads before agreeing, so declare only what the extension uses.

- **reads** lists the parts of the open adventure it reads: text, codex and settings.
- **changes** is none, suggests or writes. With suggests, every change comes to the author as a suggestion with Accept and Reject. With writes, the extension changes the text directly, but only right after the author clicked one of its items, and each change is one undo step named after the extension.
- **network** lists the addresses it connects to: a host such as api.example.com, or {"setting": "address"} for the address the author enters in one of its settings. Plain http is allowed only to the author's own computer (localhost); everything else must be https.

One rule cannot be bent: an extension that declares any network address can only suggest changes, never write them. What comes from an outside service, such as a writing assistant, always reaches the author with Accept and Reject first. Installing refuses an extension that declares both.

## The code

Scriptorum calls the setup function of the main file once, with ext, the extension's link to Scriptorum. Register what each menu item does with ext.command, using the item's id:

```
def setup(ext):
    @ext.command("check")
    def check(context):
        info = ext.call("adventure.info")
        return {"message": "Checked " + info["title"] + "."}
```

The function gets the context of the click (the chapter and line of the cursor, and for a block action the block's kind and path) and returns a short message for the status bar.

ext.call asks Scriptorum for something. Each call is checked against the needs; anything else is refused with a plain message, which reaches the code as an exception.

- adventure.info: the title, the chapters, the game system and theme, and whether it is read-only (reads text)
- adventure.chapter, with index: one chapter's text and outline (reads text)
- ext.blocks(chapter): every block of a chapter, nested ones too, each with its path, kind, line and exact source (reads text)
- codex.codex and codex.entry, with entry_id: the codex (reads codex)
- adventure.settings: the adventure's settings (reads settings)
- settings.get: the extension's own settings, never a secret

To hear what happens, register a listener: @ext.on("text.changed"). An extension that reads the text hears adventure.opened, adventure.closed, adventure.saved, text.changed and build.finished; one that reads the codex hears codex.changed.

The extension may use Python's standard library and pure-Python libraries it carries in its own folder. Anything it prints goes to its log, extension.log, in its own folder in Scriptorum's data folder, beside any files it stores in ext.data_folder.

## Showing what it found

A panel of type findings is a list the author clicks through. Send it the items, each with its text and, if it has one, its chapter and line; a click on an item goes to that place:

```
ext.findings("found", [{"text": "A heading with no text", "chapter": 0, "line": 12}])
```

The list shows in the extension's own section of the Extensions tab, at the bottom of the left pane. Sending the panel again replaces what it shows.

## Suggesting changes

An extension that declares suggests (or writes) may suggest a new text for a whole block, or a new block after one. Give the block's chapter and path, from ext.blocks, and the new source:

```
ext.suggest_replace(0, block["path"], "The new text of the paragraph.", label="Shorter")
ext.suggest_add(0, block["path"], "#read-aloud[The mist lifts over the harbour.]", label="A read-aloud text")
```

The suggestion shows under the block in the editor, with the changed words marked and Accept and Reject, and it is listed in the extension's section of the Extensions tab. Accepting is one undo step; nothing changes until the author accepts. A suggestion for a block the author has edited since cannot be accepted any more.

## Pictures

An extension may show a PNG or JPEG picture for the author to use:

```
ext.picture(png_bytes, "The old mill at dusk", chapter=0, path=block["path"])
```

The author chooses Use, which puts the picture in the adventure after that block, with the description for screen readers filled in; or, for a person card, Set as portrait. Regenerate runs the same item again, with regenerate set in the context; Cancel throws the picture away.

## Changing the text directly

An extension that declares writes may change a chapter while it runs an item the author clicked:

```
text = ext.call("adventure.chapter", index=0)["text"]
ext.call("adventure.set_chapter_text", index=0, text=text.replace(" ,", ","))
```

Everything one item changes, in one chapter or several, is one undo step named after the extension, such as "Undo Comma tidy: Fix spaces". The change is refused if the author edited the text while the extension worked, if the adventure is read-only, or when nobody asked: from an event listener, for example.

## Settings and secrets

Settings are declared in the manifest and shown in Settings ▸ Extensions and in the extension's section of the Extensions tab:

```
"settings": [
  {"id": "address", "kind": "text", "label": "Service address"},
  {"id": "model", "kind": "choice", "label": "Model", "options": ["small", "large"], "default": "small"},
  {"id": "key", "kind": "secret", "label": "API key"}
]
```

A secret, such as an API key, is kept in the computer's own keychain and never reaches the extension's code. To use it, write {secret:key} in a request's header or body; Scriptorum fills it in on the way out.

## Connecting to the internet

While Block all connections outside the app is on, which is the default, no request leaves Scriptorum, and an extension's request is refused with a plain message. Once the author allows connections, ext.request goes to the addresses the extension declared, and nowhere else:

```
answer = ext.request("https://api.example.com/v1/answer", method="POST",
                     headers={"Authorization": "Bearer {secret:key}"}, body="{}")
```

The answer has its status, its headers and its body as base64. A request never follows a redirect, so it can only reach the address that was checked. A long task can call ext.busy() now and then, so Scriptorum does not stop it after 30 seconds.

## Licence and verified extensions

Put a licence file in the folder and name the licence in the manifest. An extension signed by the Scriptorum project is shown as "from the Scriptorum project"; every other is shown as unverified, with the warning that it runs program code and should only be installed from people you trust.

## Worked example: Long read-aloud

This extension lists the read-aloud texts that are longer than the author likes to read in one breath. It only reads, so it needs no agreement beyond reading the text.

```file: module.json
{
  "id": "example.long-read-aloud",
  "kind": "extension",
  "name": "Long read-aloud",
  "version": "1.0.0",
  "format": 1,
  "app": "1.0.0",
  "licence": "GPL-3.0-or-later",
  "authors": ["Your name"],
  "description": "Lists read-aloud texts longer than you like to read in one breath.",
  "requires": [{"id": "api", "version": "1.x"}],
  "main": "extension.py",
  "needs": {"reads": ["text"], "changes": "none", "network": []},
  "settings": [{"id": "words", "kind": "choice", "label": "Longest read-aloud, in words", "options": ["60", "100", "150"], "default": "100"}],
  "menu": [{"id": "check", "label": "Find long read-aloud texts"}],
  "panels": [{"id": "long", "type": "findings", "title": "Long read-aloud texts"}]
}
```

```file: extension.py
def setup(ext):
    @ext.command("check")
    def check(context):
        limit = int(ext.call("settings.get").get("words") or 100)
        chapters = ext.call("adventure.info")["chapters"]
        found = []
        for chapter in range(len(chapters)):
            for block in ext.blocks(chapter):
                if block["kind"] == "read-aloud":
                    words = len(block["source"].split())
                    if words > limit:
                        found.append({"text": str(words) + " words", "chapter": chapter, "line": block["line"]})
        ext.findings("long", found)
        return {"message": str(len(found)) + " read-aloud texts over " + str(limit) + " words."}
```

Install it, switch it on and choose Extensions ▸ Find long read-aloud texts: the list shows in its section of the Extensions tab, and a click on a line goes to that read-aloud text. Change the limit in its settings and run it again.

## Testing your extension

1. Pack the folder as a .scmod file (see Packing it to share).
2. Open File ▸ Settings… ▸ Extensions and choose Install extension…. Read the needs, agree, and switch the extension on.
3. Open an adventure and use its items. If something goes wrong, the status bar or a message says so; the extension's own log, extension.log, is in its folder under extensions/data in Scriptorum's data folder.
4. To try a new version, raise the version number in module.json, pack it again and install it over the old one; its settings stay.

## Packing it to share

A .scmod file is the folder packed as a zip file, with module.json at the top, not inside another folder. On macOS and Linux:

```
cd my-extension
zip -r ../my-extension.scmod .
```

On Windows, select the files inside the folder (not the folder itself), right-click and choose Send to ▸ Compressed (zipped) folder, then rename the file to my-extension.scmod. Send that one file; the other person installs it in Settings ▸ Extensions.
