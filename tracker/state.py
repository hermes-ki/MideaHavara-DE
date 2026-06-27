"""Persistenter Zustand zwischen den Läufen + Diff-Logik (Anti-Spam)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .config import ROOT
from .models import Offer

STATE_PATH = ROOT / "state.json"


def load_seen(path: Path = STATE_PATH) -> set[str]:
    """Lädt die Menge der beim letzten Lauf verfügbaren Angebots-Schlüssel."""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    return set(data.get("available_keys", []))


def save_seen(keys: Iterable[str], path: Path = STATE_PATH) -> None:
    payload = {"available_keys": sorted(set(keys))}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def diff_new(available: list[Offer], seen: set[str]) -> tuple[list[Offer], set[str]]:
    """Ermittelt neu verfügbar gewordene Angebote.

    Returns:
        (new_offers, current_keys)
        - new_offers: Angebote, deren Schlüssel zuvor nicht "verfügbar" war.
        - current_keys: alle aktuell verfügbaren Schlüssel (= neuer State).
    """
    current_keys = {o.key() for o in available}
    new_offers = [o for o in available if o.key() not in seen]
    return new_offers, current_keys
