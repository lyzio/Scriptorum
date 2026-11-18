"""The one network gate (design document F23.6, D9; 0.7.0 step 1).

Every network request Scriptorum makes passes through this module, and no
other module in the app opens a connection. Today there are two, both only
when the author asks: the update file (F21) and the update pack (F22). Each
is one GET over https that sends nothing but the request for the file: no
version, no identifier, no cookies. The "Block all connections outside the
app" switch of extension modules (#27) will be checked here.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Callable, List, Optional

UPDATE_FILE = "update-file"
UPDATE_PACK = "update-pack"
PURPOSES = (UPDATE_FILE, UPDATE_PACK)

TIMEOUTS = {UPDATE_FILE: 10.0, UPDATE_PACK: 60.0}
ACCEPT = {UPDATE_FILE: "application/json", UPDATE_PACK: "application/zip"}


def _https(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://") and len(url) > len("https://")


def _get(url: str, accept: str, timeout: float, limit: int) -> bytes:
    """One GET over https. Proxies set on the computer are used as for any
    program. A redirect that ends anywhere but on https is treated as
    unreachable; an answer larger than ``limit`` is refused."""
    request = urllib.request.Request(url, headers={"User-Agent": "Scriptorum", "Accept": accept})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https checked first)
        if not _https(response.geturl()):
            raise urllib.error.URLError("redirected away from https")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("answer too large")
    return data


class NetworkGate:
    """Every request goes through ``fetch``. ``requests`` records each address
    asked, in order; the tests put their own reader in ``readers`` so no test
    ever reaches the internet."""

    def __init__(self):
        self.requests: List[str] = []
        self.readers: dict = {}   # purpose -> callable(address) -> bytes

    def fetch(self, purpose: str, address: str) -> bytes:
        from scriptorum.core import updates

        if purpose not in PURPOSES:
            raise ValueError(f"not a network purpose: {purpose}")
        if not _https(address):
            raise urllib.error.URLError("not https")
        self.requests.append(address)
        reader: Optional[Callable[[str], bytes]] = self.readers.get(purpose)
        if reader is not None:
            return reader(address)
        limit = updates.MAX_BYTES if purpose == UPDATE_FILE else updates.MAX_PACK_BYTES
        return _get(address, ACCEPT[purpose], TIMEOUTS[purpose], limit)

    def reader_for(self, purpose: str) -> Callable[[str], bytes]:
        """A one-argument reader that goes through the gate, for the core's
        update check and install (F21, F22)."""
        return lambda address: self.fetch(purpose, address)
