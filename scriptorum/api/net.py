"""The one network gate (design document F23.6, D9; 0.7.0 step 1; F25, 0.7.4).

Every network request Scriptorum makes passes through this module, and no
other module in the app opens a connection. The update file (F21) and the
update pack (F22) are one GET over https each, only when the author asks,
sending nothing but the request for the file: no version, no identifier,
no cookies. From 0.7.4 switched-on extensions (F25.16) ask through here too,
for the hosts they declared.

F25.1, F25.3 (0.7.4): "Block all connections outside the app" is checked
here, before anything else. While it is on, which is the default, every
request of every purpose is refused and nothing is sent.
"""

from __future__ import annotations

import base64
import ipaddress
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, List, Optional

UPDATE_FILE = "update-file"
UPDATE_PACK = "update-pack"
EXTENSION = "extension"           # F25.16: a switched-on extension's request
PURPOSES = (UPDATE_FILE, UPDATE_PACK, EXTENSION)

TIMEOUTS = {UPDATE_FILE: 10.0, UPDATE_PACK: 60.0, EXTENSION: 60.0}
ACCEPT = {UPDATE_FILE: "application/json", UPDATE_PACK: "application/zip"}
EXTENSION_LIMIT = 20 * 1024 * 1024   # the largest answer an extension gets
EXTENSION_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


class ConnectionsBlocked(urllib.error.URLError):
    """F25.1: Block all connections outside the app is on; nothing was sent."""

    def __init__(self):
        super().__init__("connections outside the app are blocked")


def _https(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://") and len(url) > len("https://")


def is_local_host(host: str) -> bool:
    """F25.5: the author's own computer, the only place plain http may go."""
    host = (host or "").strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def host_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def extension_address_ok(url: str) -> bool:
    """https anywhere, plain http only to localhost (F25.5)."""
    if not isinstance(url, str):
        return False
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https":
        return bool(parts.hostname)
    return parts.scheme == "http" and is_local_host(parts.hostname or "")


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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """An extension's request never follows a redirect, so it can only ever
    reach the host that was checked (F25.16)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _extension_request(url: str, method: str, headers: dict, body: Optional[bytes]) -> dict:
    request = urllib.request.Request(url, data=body, method=method,
                                     headers={"User-Agent": "Scriptorum extension", **headers})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=TIMEOUTS[EXTENSION]) as response:  # noqa: S310 (address checked)
            status, answer_headers, data = response.status, dict(response.headers), response.read(EXTENSION_LIMIT + 1)
    except urllib.error.HTTPError as exc:
        status, answer_headers, data = exc.code, dict(exc.headers or {}), exc.read(EXTENSION_LIMIT + 1)
    if len(data) > EXTENSION_LIMIT:
        raise ValueError("answer too large")
    return {"status": status, "headers": answer_headers, "base64": base64.b64encode(data).decode("ascii")}


class NetworkGate:
    """Every request goes through ``fetch`` or ``request``. ``requests`` records
    each address asked, in order, and ``refused`` each one the switch stopped;
    the tests put their own reader in ``readers`` so no test ever reaches the
    internet. ``blocked`` tells whether Block all connections outside the app
    is on (F25.1)."""

    def __init__(self, blocked: Optional[Callable[[], bool]] = None):
        self.requests: List[str] = []
        self.refused: List[str] = []
        self.readers: dict = {}   # purpose -> callable
        self.blocked: Callable[[], bool] = blocked or (lambda: False)

    def _check_switch(self, address: str) -> None:
        if self.blocked():
            self.refused.append(address)
            raise ConnectionsBlocked()

    def fetch(self, purpose: str, address: str) -> bytes:
        from scriptorum.core import updates

        if purpose not in (UPDATE_FILE, UPDATE_PACK):
            raise ValueError(f"not a network purpose: {purpose}")
        self._check_switch(address)
        if not _https(address):
            raise urllib.error.URLError("not https")
        self.requests.append(address)
        reader: Optional[Callable[[str], bytes]] = self.readers.get(purpose)
        if reader is not None:
            return reader(address)
        limit = updates.MAX_BYTES if purpose == UPDATE_FILE else updates.MAX_PACK_BYTES
        return _get(address, ACCEPT[purpose], TIMEOUTS[purpose], limit)

    def request(self, address: str, method: str = "GET", headers: Optional[dict] = None,
                body: Optional[bytes] = None) -> dict:
        """F25.16: one request of a switched-on extension, whose host the
        caller has already checked against the extension's declared needs.
        Returns ``{"status", "headers", "base64"}``."""
        self._check_switch(address)
        method = (method or "GET").upper()
        if method not in EXTENSION_METHODS:
            raise ValueError(f"not a request method: {method}")
        if not extension_address_ok(address):
            raise urllib.error.URLError("only https, or plain http to localhost")
        self.requests.append(address)
        reader = self.readers.get(EXTENSION)
        if reader is not None:
            return reader(address, method, dict(headers or {}), body)
        return _extension_request(address, method, dict(headers or {}), body)

    def reader_for(self, purpose: str) -> Callable[[str], bytes]:
        """A one-argument reader that goes through the gate, for the core's
        update check and install (F21, F22)."""
        return lambda address: self.fetch(purpose, address)
