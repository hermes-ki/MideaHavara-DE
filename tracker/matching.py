"""Produktabgleich und Geo-Distanz."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from .config import Location, Product
from .models import CHANNEL_STORE, CONDITION_USED, Offer


def matches_product(offer: Offer, product: Product) -> bool:
    """Stellt sicher, dass das Angebot wirklich das gesuchte Gerät ist.

    Bevorzugt EAN-Abgleich; fehlt die EAN, greift ein strikter Titelabgleich
    (alle Pflicht-Schlüsselwörter vorhanden, kein Ausschluss-Wort).
    """
    if offer.ean and product.eans:
        return offer.ean in product.eans

    title = (offer.title or "").lower()
    if not title:
        return False
    if any(bad in title for bad in product.title_must_exclude):
        return False
    return all(req in title for req in product.title_must_include)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def is_buyable(offer: Offer, product: Product, location: Location) -> bool:
    """Der zentrale "nur wirklich bestellbar"-Filter.

    Ein Angebot zählt nur, wenn ALLE Bedingungen erfüllt sind:
      1. richtiges Produkt (EAN/Titel),
      2. tatsächlich auf Lager,
      3. Preis <= Obergrenze,
      4. Zustand erlaubt (gebraucht nur wenn konfiguriert),
      5. Filialen: innerhalb des Radius.
    """
    if not matches_product(offer, product):
        return False
    if not offer.in_stock:
        return False
    if offer.price is None or offer.price > product.max_price:
        return False
    if offer.condition == CONDITION_USED and not product.allow_used:
        return False

    if offer.channel == CHANNEL_STORE:
        if offer.distance_km is None:
            # Ohne Distanz können wir den Radius nicht garantieren -> ausschließen.
            return False
        if offer.distance_km > location.radius_km:
            return False

    return True
