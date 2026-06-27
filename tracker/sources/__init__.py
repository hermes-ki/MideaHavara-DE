"""Quellen-Adapter.

Jeder Adapter implementiert ``fetch_offers(cfg) -> list[Offer]`` und ist über
``get_source(name)`` auffindbar. Adapter sind voneinander isoliert: Fehler in
einer Quelle dürfen die anderen nicht abbrechen (siehe run.py).
"""

from __future__ import annotations

from collections.abc import Callable

from ..config import Config
from ..models import Offer
from . import amazon, baumarkt, geizhals, idealo, mediamarkt

# Registrierung: Quellenname -> Aufruf-Funktion.
# saturn/obi/bauhaus/hornbach teilen sich Code mit ihren Geschwister-Modulen.
SOURCES: dict[str, Callable[[Config], list[Offer]]] = {
    "geizhals": geizhals.fetch_offers,
    "idealo": idealo.fetch_offers,
    "mediamarkt": lambda cfg: mediamarkt.fetch_offers(cfg, chain="mediamarkt"),
    "saturn": lambda cfg: mediamarkt.fetch_offers(cfg, chain="saturn"),
    "obi": lambda cfg: baumarkt.fetch_offers(cfg, chain="obi"),
    "bauhaus": lambda cfg: baumarkt.fetch_offers(cfg, chain="bauhaus"),
    "hornbach": lambda cfg: baumarkt.fetch_offers(cfg, chain="hornbach"),
    "amazon": amazon.fetch_offers,
}


def get_source(name: str) -> Callable[[Config], list[Offer]] | None:
    return SOURCES.get(name)
