"""Idealo-Adapter (Preisvergleich).

Idealo bettet Angebotsdaten als JSON-LD ein. Wir lesen Titel/EAN/Preis/
Verfügbarkeit daraus; bei Block greift der Browser-Fallback.
"""

from __future__ import annotations

import logging

from ..config import Config, Product
from ..models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .base import fetch_page
from .jsonld import extract_products

log = logging.getLogger(__name__)

SOURCE = "idealo"


def _html(url: str) -> str | None:
    html, how = fetch_page(url, wait_selector="script[type='application/ld+json']")
    if how == "blocked":
        log.info("Idealo: Bot-Wall nicht überwunden (geblockt).")
    return html


def fetch_offers(cfg: Config, product: Product) -> list[Offer]:
    url = product.url_for(SOURCE)
    if not url:
        log.info("Idealo: keine Produkt-URL für '%s' konfiguriert – übersprungen.", product.name)
        return []

    html = _html(url)
    if not html:
        return []

    product_ean = product.eans[0] if product.eans else None
    offers: list[Offer] = []
    for prod in extract_products(html):
        if prod["price"] is None:
            continue
        # Ein auf Idealo gelistetes Angebot mit Preis gilt grundsätzlich als
        # bestellbar (die echte Verfügbarkeit zeigt sich erst beim Klick zum
        # Händler). Ein EXPLIZITES OutOfStock-Signal respektieren wir aber –
        # sonst löst ein klar nicht lieferbares Listing einen Fehlalarm aus.
        in_stock = prod["in_stock"] or prod.get("availability_raw") is None
        offers.append(
            Offer(
                source=SOURCE,
                title=prod["title"] or product.name,
                price=prod["price"],
                url=url,
                in_stock=in_stock,
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=prod["ean"] or product_ean,
                merchant="Idealo (Bestpreis)",
            )
        )

    log.info("Idealo: %d Angebote extrahiert.", len(offers))
    return offers
