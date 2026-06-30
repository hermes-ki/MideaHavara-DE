"""Datenmodelle für den Tracker."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Zustände eines Angebots.
CONDITION_NEW = "new"
CONDITION_USED = "used"  # z.B. Amazon Warehouse

# Vertriebskanäle.
CHANNEL_ONLINE = "online"
CHANNEL_STORE = "store"


@dataclass(frozen=True)
class Offer:
    """Ein normalisiertes Angebot aus einer beliebigen Quelle.

    Alle Quellen-Adapter geben Listen von ``Offer`` zurück, sodass Filter-
    und Diff-Logik quellenunabhängig arbeiten können.
    """

    source: str  # z.B. "mediamarkt", "geizhals"
    title: str
    price: float  # in EUR, inkl. Versand wenn ermittelbar
    url: str
    in_stock: bool
    condition: str = CONDITION_NEW
    channel: str = CHANNEL_ONLINE
    ean: str | None = None
    merchant: str | None = None  # bei Preisvergleichen der konkrete Händler
    store_name: str | None = None  # bei Filialen
    distance_km: float | None = None  # Entfernung der Filiale zum Standort
    product_name: str | None = None  # konfiguriertes Produkt (Watchlist-Gruppierung)

    def key(self) -> str:
        """Stabiler Schlüssel zur Wiedererkennung über mehrere Läufe.

        Bewusst OHNE Preis, damit eine reine Preisänderung kein neuer Alarm
        ist – ein erneuter Alarm soll nur entstehen, wenn ein Angebot von
        "nicht verfügbar" zu "verfügbar" wechselt.
        """
        parts = [
            self.source,
            self.channel,
            self.condition,
            self.merchant or "",
            self.store_name or "",
            self.url,
        ]
        raw = "|".join(parts)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def describe(self) -> str:
        """Menschlich lesbare Beschreibung für Benachrichtigungen/Logs."""
        cond = "Neu" if self.condition == CONDITION_NEW else "Gebraucht"
        where = self.merchant or self.source
        if self.channel == CHANNEL_STORE and self.store_name:
            dist = f" (~{self.distance_km:.0f} km)" if self.distance_km is not None else ""
            where = f"{where} – Filiale {self.store_name}{dist}"
        return f"{where}: {self.price:.2f} € [{cond}]"
