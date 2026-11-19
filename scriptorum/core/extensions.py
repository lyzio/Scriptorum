"""Extension modules: the checks, needs, state and secrets (design document F25, 0.7.4, issue #27).

An extension is a module of kind ``extension`` (9.2) that may carry Python
code and adds functions to Scriptorum through the internal API (F23). This
module holds what needs no process: reading and checking an extension's
manifest before it is installed (F25.4 to F25.9), what it needs in plain
words, whether it is signed with the project's key, and the author's state
for each installed extension (on or off, its settings, its secrets and the
folder it may store files in, F25.10, F25.18). Running an extension is
``api/extensions.py`` (the app's side) and ``core/exthost.py`` (its own process).

The manifest's own part, beside the fields every module has (9.2):

    "main": "extension.py",                       the file whose setup(ext) is called
    "requires": [{"id": "api", "version": "1.x"}],     the internal API it was written for
    "needs": {
        "reads": ["text", "codex", "settings"],        parts of the open adventure it reads
        "changes": "none" | "suggests" | "writes",      how it changes the adventure (F25.12)
        "network": ["api.example.com", {"setting": "address"}]
    },
    "settings": [{"id": "address", "label": "…", "kind": "text" | "secret" | "choice", …}],
    "menu": [{"id": "check", "label": "…"}],
    "block_actions": [{"id": "tidy", "label": "…", "kinds": ["scene"]}],
    "panels": [{"id": "findings", "type": "findings", "title": "…"}]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Optional

from scriptorum.core.modules import ModuleError, RANGE_RE, version_matches

KIND = "extension"
SIGNATURE_FILE = "signature.json"
READS = ("text", "codex", "settings")
CHANGES = ("none", "suggests", "writes")
CHANGE_RANK = {"none": 0, "suggests": 1, "writes": 2}
SETTING_KINDS = ("text", "secret", "choice")
PANEL_TYPES = ("findings",)   # 0.7.5 adds chat, suggestion and picture (F25.17)
# F25.4: compiled code is refused in every module kind.
COMPILED_SUFFIXES = {".so", ".pyd", ".dll", ".exe", ".dylib", ".pyc", ".pyo", ".bin", ".com", ".bat", ".cmd", ".sh"}
ITEM_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
HOST = re.compile(r"^(?=.{1,253}$)[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$")

# F25.7: licences that may run with the app's GPL-3.0-or-later code.
GPL_COMPATIBLE = {
    "GPL-3.0-or-later", "GPL-3.0-only", "GPL-3.0", "GPL-3.0+", "GPL-2.0-or-later", "GPL-2.0+",
    "AGPL-3.0-or-later", "AGPL-3.0-only", "LGPL-3.0-or-later", "LGPL-3.0-only", "LGPL-2.1-or-later",
    "LGPL-2.1-only", "MIT", "MIT-0", "X11", "ISC", "0BSD", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0",
    "MPL-2.0", "Zlib", "Unlicense", "CC0-1.0", "PSF-2.0", "Python-2.0", "BSL-1.0", "WTFPL",
}


# --- the API version an extension needs (F25.9) -------------------------------------------------

def api_version() -> str:
    from scriptorum.api.workspace import API_VERSION
    return API_VERSION


def api_requirement(manifest: dict) -> Optional[str]:
    for req in manifest.get("requires", []):
        if isinstance(req, dict) and req.get("id") == "api":
            return str(req.get("version", ""))
    return None


def api_matches(wanted: str, have: Optional[str] = None) -> bool:
    """``1.x`` and ``1.1`` match API 1.1; ``2.x`` does not. A wanted minor
    number higher than the app's needs operations this app does not have."""
    have = have or api_version()
    major, minor = (int(p) for p in have.split("."))
    match = re.match(r"^(\d+)(?:\.(\d+|x))?(?:\.x)?$", (wanted or "").strip())
    if not match:
        return False
    if int(match.group(1)) != major:
        return False
    wanted_minor = match.group(2)
    return wanted_minor in (None, "x") or int(wanted_minor) <= minor


# --- licences (F25.7) ----------------------------------------------------------------------------

def licence_ok(expression: str) -> bool:
    """An SPDX expression: every part joined by AND must be compatible, and
    at least one choice joined by OR. "WITH" exceptions only add rights."""
    text = (expression or "").strip()
    if not text:
        return False
    text = re.sub(r"\s+WITH\s+[A-Za-z0-9.+-]+", "", text).replace("(", " ").replace(")", " ")
    for choice in re.split(r"\s+OR\s+", text):
        parts = [p.strip() for p in re.split(r"\s+AND\s+", choice) if p.strip()]
        if parts and all(p in GPL_COMPATIBLE for p in parts):
            return True
    return False


# --- checking an extension before it is installed (F25.4 to F25.9) -------------------------------

def check_files(folder: Path, kind: str) -> None:
    """F25.4: Python files only in an extension; compiled code in no kind."""
    for file in Path(folder).rglob("*"):
        if not file.is_file():
            continue
        suffix = file.suffix.lower()
        if suffix in COMPILED_SUFFIXES or (suffix == ".py" and kind != KIND):
            raise ModuleError("error.module.forbiddenFile", file=file.relative_to(folder).as_posix())


def network_needs(manifest: dict) -> List[dict]:
    """Each declared network need as ``{"host": …}`` or ``{"setting": …}``."""
    out = []
    for item in (manifest.get("needs") or {}).get("network") or []:
        if isinstance(item, str):
            out.append({"host": item.strip().lower()})
        elif isinstance(item, dict) and isinstance(item.get("setting"), str):
            out.append({"setting": item["setting"]})
        else:
            out.append({"bad": True})
    return out


def check_manifest(manifest: dict, folder: Path) -> None:
    """The checks of F25 that read the manifest; raises ModuleError."""
    name = manifest.get("name", manifest.get("id", ""))
    main = manifest.get("main")
    if not isinstance(main, str) or not main.endswith(".py") or ".." in Path(main).parts \
            or not (Path(folder) / main).is_file():
        raise ModuleError("error.ext.noMain", name=name)
    # F25.9: the API version it was written for.
    wanted = api_requirement(manifest)
    if wanted is None or not RANGE_RE.match(wanted):
        raise ModuleError("error.ext.noApi", name=name)
    if not api_matches(wanted):
        raise ModuleError("error.ext.apiVersion", name=name, wanted=wanted, have=api_version())
    # F25.7: a GPL-compatible licence.
    if not licence_ok(str(manifest.get("licence", ""))):
        raise ModuleError("error.ext.licence", name=name, licence=str(manifest.get("licence", "")))
    needs = manifest.get("needs")
    if not isinstance(needs, dict):
        raise ModuleError("error.ext.badNeeds", name=name)
    reads = needs.get("reads", [])
    if not isinstance(reads, list) or any(r not in READS for r in reads):
        raise ModuleError("error.ext.badNeeds", name=name)
    changes = needs.get("changes", "none")
    if changes not in CHANGES:
        raise ModuleError("error.ext.badNeeds", name=name)
    setting_ids = {s.get("id") for s in manifest.get("settings", []) if isinstance(s, dict)}
    network = network_needs(manifest)
    for item in network:
        if item.get("bad"):
            raise ModuleError("error.ext.badNeeds", name=name)
        if "host" in item and not HOST.match(item["host"]):
            raise ModuleError("error.ext.badHost", name=name, host=item["host"])
        if "setting" in item and item["setting"] not in setting_ids:
            raise ModuleError("error.ext.badNeeds", name=name)
    # F25.6: an extension that uses an outside service can only suggest changes.
    if network and changes == "writes":
        raise ModuleError("error.ext.networkWrites", name=name)
    for setting in manifest.get("settings", []):
        if not isinstance(setting, dict) or not ITEM_ID.match(str(setting.get("id", ""))) \
                or setting.get("kind", "text") not in SETTING_KINDS or not isinstance(setting.get("label"), str):
            raise ModuleError("error.ext.badSettings", name=name)
    for group in ("menu", "block_actions", "panels"):
        for item in manifest.get(group, []):
            if not isinstance(item, dict) or not ITEM_ID.match(str(item.get("id", ""))) \
                    or not isinstance(item.get("label", item.get("title")), str):
                raise ModuleError("error.ext.badItem", name=name, group=group)
            if group == "panels" and item.get("type") not in PANEL_TYPES:
                raise ModuleError("error.ext.badPanel", name=name, type=str(item.get("type")))


def need_tokens(manifest: dict) -> List[str]:
    """What an extension needs, one token each, to compare two versions (F25.5)."""
    needs = manifest.get("needs") or {}
    tokens = [f"reads:{r}" for r in needs.get("reads", [])]
    tokens.append(f"changes:{needs.get('changes', 'none')}")
    for item in network_needs(manifest):
        tokens.append(f"host:{item['host']}" if "host" in item else f"setting:{item['setting']}")
    return sorted(set(tokens))


def added_needs(old: List[str], new: List[str]) -> List[str]:
    """The needs a newer version adds: a new token, or a change that goes
    further (suggests to writes); doing less is not an addition."""
    old_change = next((t.split(":", 1)[1] for t in old if t.startswith("changes:")), "none")
    added = []
    for token in new:
        if token in old:
            continue
        if token.startswith("changes:") and CHANGE_RANK[token.split(":", 1)[1]] <= CHANGE_RANK[old_change]:
            continue
        added.append(token)
    return added


def need_texts(manifest: dict, t, only: Optional[List[str]] = None) -> List[str]:
    """F25.5: what it needs, in plain words from the interface language (F15)."""
    labels = {s["id"]: s.get("label", s["id"]) for s in manifest.get("settings", []) if isinstance(s, dict)}
    texts = []
    for token in need_tokens(manifest):
        if only is not None and token not in only:
            continue
        kind, _, value = token.partition(":")
        if kind == "reads":
            texts.append(t(f"ext.need.reads.{value}"))
        elif kind == "changes":
            texts.append(t(f"ext.need.changes.{value}"))
        elif kind == "host":
            texts.append(t("ext.need.host", host=value))
        else:
            texts.append(t("ext.need.setting", setting=labels.get(value, value)))
    return texts


# --- signed by the project (F25.8) ---------------------------------------------------------------

def file_digests(folder: Path) -> Dict[str, str]:
    folder = Path(folder)
    out = {}
    for file in sorted(folder.rglob("*")):
        if file.is_file() and file.relative_to(folder).as_posix() != SIGNATURE_FILE:
            out[file.relative_to(folder).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return out


def signed_bytes(folder: Path, manifest: dict) -> bytes:
    from scriptorum.core.signing import canonical
    return canonical({"id": manifest["id"], "version": manifest["version"], "files": file_digests(folder)})


def sign_folder(folder: Path, private_pem: bytes) -> None:
    """Write signature.json for an extension folder (tools/sign_extension.py, the tests)."""
    from scriptorum.core.signing import sign
    folder = Path(folder)
    manifest = json.loads((folder / "module.json").read_text("utf-8"))
    signature = sign(signed_bytes(folder, manifest), private_pem)
    (folder / SIGNATURE_FILE).write_text(json.dumps({"signature": signature}, indent=2) + "\n", "utf-8")


def verified(folder: Path, manifest: dict, key: Optional[str] = None) -> bool:
    """Signed with the project's key (the same Ed25519 key as updates, F22),
    over every file of the extension. Anything else is unverified."""
    from scriptorum.core.signing import SignatureError, verify
    file = Path(folder) / SIGNATURE_FILE
    try:
        signature = json.loads(file.read_text("utf-8"))["signature"]
        verify(signed_bytes(folder, manifest), signature, key)
        return True
    except (OSError, ValueError, KeyError, TypeError, SignatureError):
        return False


# --- the author's state for each extension (F25.10, F25.18) --------------------------------------

class Keychain:
    """The computer's own keychain through keyring (MIT): Keychain on macOS,
    Credential Manager on Windows, the Secret Service on Linux (F25.18)."""

    def available(self) -> bool:
        try:
            import keyring
            from keyring.backends import fail
            backend = keyring.get_keyring()
            if isinstance(backend, fail.Keyring):
                return False
            chained = getattr(backend, "backends", None)
            return chained is None or bool(chained)
        except Exception:  # noqa: BLE001 - no library or no keychain: the file is used
            return False

    def get(self, service: str, name: str) -> Optional[str]:
        import keyring
        return keyring.get_password(service, name)

    def set(self, service: str, name: str, value: str) -> None:
        import keyring
        keyring.set_password(service, name, value)

    def delete(self, service: str, name: str) -> None:
        import keyring
        try:
            keyring.delete_password(service, name)
        except Exception:  # noqa: BLE001 - nothing stored is fine
            pass


class ExtensionStore:
    """``<app data>/extensions/``: state.json (on or off, the needs agreed to,
    the settings), data/<id>/ (the folder an extension may store files in)
    and, where no keychain is available, secrets/<id>.json readable only by
    the author's user."""

    SERVICE = "Scriptorum extension {id}"

    def __init__(self, root: Path, keychain=None):
        self.root = Path(root)
        self.keychain = keychain if keychain is not None else Keychain()

    # --- state.json --------------------------------------------------------------------------------
    def _read(self) -> dict:
        try:
            data = json.loads((self.root / "state.json").read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / "state.json.tmp"
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        os.replace(tmp, self.root / "state.json")

    def state(self, ext_id: str) -> dict:
        entry = self._read().get(ext_id) or {}
        return {"on": bool(entry.get("on")), "agreed": list(entry.get("agreed", [])),
                "settings": dict(entry.get("settings", {}))}

    def _update(self, ext_id: str, **changes) -> None:
        data = self._read()
        entry = data.setdefault(ext_id, {})
        entry.update(changes)
        self._write(data)

    def set_on(self, ext_id: str, on: bool) -> None:
        self._update(ext_id, on=bool(on))

    def agree(self, ext_id: str, tokens: List[str]) -> None:
        self._update(ext_id, agreed=sorted(set(tokens)))

    def set_setting(self, ext_id: str, key: str, value: str) -> None:
        settings = self.state(ext_id)["settings"]
        settings[key] = value
        self._update(ext_id, settings=settings)

    def data_folder(self, ext_id: str) -> Path:
        folder = self.root / "data" / ext_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    # --- secrets (F25.18) ---------------------------------------------------------------------------
    def keychain_used(self) -> bool:
        return self.keychain.available()

    def _secret_file(self, ext_id: str) -> Path:
        return self.root / "secrets" / f"{ext_id}.json"

    def _read_secret_file(self, ext_id: str) -> dict:
        try:
            return json.loads(self._secret_file(ext_id).read_text("utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_secret_file(self, ext_id: str, data: dict) -> None:
        file = self._secret_file(ext_id)
        file.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(file.parent, stat.S_IRWXU)
        except OSError:
            pass
        fd = os.open(str(file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out)
        try:
            os.chmod(file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def set_secret(self, ext_id: str, key: str, value: str) -> None:
        names = set(self._read().get(ext_id, {}).get("secrets", []))
        if self.keychain_used():
            service = self.SERVICE.format(id=ext_id)
            if value:
                self.keychain.set(service, key, value)
            else:
                self.keychain.delete(service, key)
        else:
            data = self._read_secret_file(ext_id)
            if value:
                data[key] = value
            else:
                data.pop(key, None)
            self._write_secret_file(ext_id, data)
        (names.add if value else names.discard)(key)
        self._update(ext_id, secrets=sorted(names))

    def secret(self, ext_id: str, key: str) -> Optional[str]:
        if self.keychain_used():
            value = self.keychain.get(self.SERVICE.format(id=ext_id), key)
            if value is not None:
                return value
        return self._read_secret_file(ext_id).get(key)

    def has_secret(self, ext_id: str, key: str) -> bool:
        return key in self._read().get(ext_id, {}).get("secrets", [])

    # --- removal (F25.18) ----------------------------------------------------------------------------
    def forget(self, ext_id: str) -> None:
        """Everything the extension stored goes: its state and settings, its
        secrets, in the keychain and in the file, and its data folder."""
        data = self._read()
        entry = data.pop(ext_id, {}) or {}
        if self.keychain_used():
            for key in entry.get("secrets", []):
                self.keychain.delete(self.SERVICE.format(id=ext_id), key)
        self._write(data)
        shutil.rmtree(self.root / "data" / ext_id, ignore_errors=True)
        try:
            self._secret_file(ext_id).unlink()
        except OSError:
            pass


def module_info(module, store: ExtensionStore, t, key: Optional[str] = None, blocked: bool = False) -> dict:
    """One installed extension for Settings ▸ Extensions (F25.10)."""
    manifest = module.manifest
    state = store.state(module.id)
    settings = []
    for item in manifest.get("settings", []):
        kind = item.get("kind", "text")
        entry = {"id": item["id"], "label": item["label"], "kind": kind, "note": item.get("note", "")}
        if kind == "secret":
            entry["set"] = store.has_secret(module.id, item["id"])
        else:
            entry["value"] = state["settings"].get(item["id"], item.get("default", ""))
            if kind == "choice":
                entry["options"] = [str(o) for o in item.get("options", [])]
        settings.append(entry)
    return {
        "id": module.id, "version": module.version, "name": module.name,
        "description": manifest.get("description", ""), "authors": manifest.get("authors", []),
        "licence": manifest.get("licence", ""), "on": state["on"],
        "verified": verified(module.path, manifest, key),
        "needs": need_texts(manifest, t), "network": bool(network_needs(manifest)),
        "needsNetwork": blocked and bool(network_needs(manifest)),
        "changes": (manifest.get("needs") or {}).get("changes", "none"),
        "settings": settings,
        "menu": [{"id": i["id"], "label": i["label"]} for i in manifest.get("menu", [])],
        "blockActions": [{"id": i["id"], "label": i["label"], "kinds": list(i.get("kinds", []))}
                         for i in manifest.get("block_actions", [])],
        "panels": [{"id": i["id"], "type": i["type"], "title": i.get("title", i.get("label", ""))}
                   for i in manifest.get("panels", [])],
    }


__all__ = ["KIND", "ExtensionStore", "Keychain", "check_files", "check_manifest", "licence_ok", "api_matches",
           "need_tokens", "added_needs", "need_texts", "verified", "sign_folder", "module_info",
           "network_needs", "version_matches"]
