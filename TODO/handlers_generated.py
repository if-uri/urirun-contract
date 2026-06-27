# WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE.
# Przegeneruj: `make gen`. Bramą jest ci/regen_check.py.
from typing import Any

# from .conn import conn, _ok  # zapewnione przez pakiet connectora

@conn.handler("window/command/close", isolated=True, meta={"label": "TODO: window/command/close"})
def close(id: str = "") -> dict[str, Any]:
    """WYGENEROWANE Z KONTRAKTU v1. Sygnatura i kształt koperty pochodzą z
    contracts.py — NIE edytuj ich ręcznie (build odrzuci dryf). Uzupełnij tylko ciało."""
    raise NotImplementedError("ciało window/command/close")  # noqa: F841 — uzupełnij logikę, potem:
    return _ok(action='window-close', reversible=True, snapshot={}, inverse={"path": 'window/command/restore', "args": {"snapshot": {}}})

@conn.handler("window/command/restore", isolated=True, meta={"label": "TODO: window/command/restore"})
def restore(snapshot: dict | None = None) -> dict[str, Any]:
    """WYGENEROWANE Z KONTRAKTU v1. Sygnatura i kształt koperty pochodzą z
    contracts.py — NIE edytuj ich ręcznie (build odrzuci dryf). Uzupełnij tylko ciało."""
    raise NotImplementedError("ciało window/command/restore")  # noqa: F841 — uzupełnij logikę, potem:
    return _ok(action='window-restore', reversible=True, inverse={"path": 'window/command/close', "args": {"id": ""}})
