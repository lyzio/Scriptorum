"""Sign an extension as "from the Scriptorum project" (design document F25.8, 0.7.4).

Writes signature.json into an extension's folder: the project's Ed25519
signature, with the same private key as updates (F22), over the extension's
id, version and the SHA-256 of every other file. The app then shows it as
"from the Scriptorum project"; any change to a file afterwards makes it
unverified again. Pack the folder as a .scmod file afterwards.

    python tools/sign_extension.py path/to/extension-folder
    python tools/sign_extension.py path/to/extension-folder --key ~/scriptorium-update-key.pem
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scriptorum.core.extensions import sign_folder, verified  # noqa: E402
from tools.release import DEFAULT_KEY  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sign an extension folder with the project's key (F25.8).")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--key", type=Path, default=Path(DEFAULT_KEY), help=f"the private key (default {DEFAULT_KEY})")
    args = parser.parse_args(argv)
    if not (args.folder / "module.json").is_file():
        print(f"{args.folder} has no module.json", file=sys.stderr)
        return 1
    try:
        private = Path(args.key).expanduser().read_bytes()
    except OSError:
        print(f"The private key {args.key} could not be read.", file=sys.stderr)
        return 1
    sign_folder(args.folder, private)
    import json
    manifest = json.loads((args.folder / "module.json").read_text("utf-8"))
    from scriptorum.core.signing import public_of
    ok = verified(args.folder, manifest, public_of(private))
    print(f"Signed {manifest['id']} {manifest['version']}" + ("" if ok else " (but it does not check: is this the project's key?)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
