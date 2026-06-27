"""Idealo-Adapter (Preisvergleich).

Idealo bettet Angebotsdaten als JSON-LD ein. Wir lesen Titel/EAN/Preis/
Verfügbarkeit daraus; bei Block greift der Browser-Fallback.
"""

from __future__ import annotations

import logging

from ..config import Config
from ..models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .base import fetch_html_via_browser, http_get
from .jsonld import extract_products

log = logging.getLogger(__name__)

SOURCE = "idealo"


def _html(url: str) -> str | None:
    resp = http_get(url)
    if resp is not None:
        return resp.text
    log.info("Idealo direkt geblockt – versuche Browser-Fallback.")
    return fetch_html_via_browser(url, wait_selector="script[type='application/ld+json']")


def fetch_offers(cfg: Config) -> list[Offer]:
    url = cfg.url_for(SOURCE)
    if not url:
        log.info("Idealo: keine Produkt-URL konfiguriert – übersprungen.")
        return []

    html = _html(url)
    if not html:
        return []

    product_ean = cfg.product.eans[0] if cfg.product.eans else None
    offers: list[Offer] = []
    for prod in extract_products(html):
        if prod["price"] is None:
            continue
        offers.append(
            Offer(
                source=SOURCE,
                title=prod["title"] or cfg.product.name,
                price=prod["price"],
                url=url,
                # Ein auf Idealo gelistetes Angebot mit Preis gilt als
                # bestellbar; die Verfügbarkeit wird beim Klick zum Händler real.
                in_stock=True,
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=prod["ean"] or product_ean,
                merchant="Idealo (Bestpreis)",
            )
        )

    log.info("Idealo: %d Angebote extrahiert.", len(offers))
    return offers
