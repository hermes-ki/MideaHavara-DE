"""Geizhals-Adapter (Preisvergleich).

Geizhals listet pro Produkt mehrere Händlerangebote. Wir lesen primär die
JSON-LD-Angebotsdaten der Produktseite; zusätzlich versuchen wir die
Händler-Angebotszeilen aus dem HTML zu parsen. Bei Block (403) greift der
Browser-Fallback.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from ..config import Config
from ..models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .base import fetch_html_via_browser, http_get, parse_price
from .jsonld import extract_products

log = logging.getLogger(__name__)

SOURCE = "geizhals"


def _html(url: str) -> str | None:
    resp = http_get(url)
    if resp is not None:
        return resp.text
    log.info("Geizhals direkt geblockt – versuche Browser-Fallback.")
    return fetch_html_via_browser(url, wait_selector="script[type='application/ld+json']")


def fetch_offers(cfg: Config) -> list[Offer]:
    url = cfg.url_for(SOURCE)
    if not url:
        log.info("Geizhals: keine Produkt-URL konfiguriert – übersprungen.")
        return []

    html = _html(url)
    if not html:
        return []

    offers: list[Offer] = []
    product_ean = cfg.product.eans[0] if cfg.product.eans else None

    # 1) Strukturierte Daten (Preis/Verfügbarkeit/Titel).
    for prod in extract_products(html):
        if prod["price"] is None:
            continue
        offers.append(
            Offer(
                source=SOURCE,
                title=prod["title"] or cfg.product.name,
                price=prod["price"],
                url=url,
                in_stock=prod["in_stock"],
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=prod["ean"] or product_ean,
                merchant="Geizhals (Bestpreis)",
            )
        )

    # 2) Händler-Angebotszeilen (best effort – Selektoren ggf. nachzuziehen).
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("div.offer__price, .productlist__price, [class*='price']"):
        price = parse_price(row.get_text(" ", strip=True))
        if price is None:
            continue
        merchant_el = row.find_parent().select_one("[class*='merchant'], [class*='shop']")
        merchant = merchant_el.get_text(strip=True) if merchant_el else "Geizhals-Händler"
        offers.append(
            Offer(
                source=SOURCE,
                title=cfg.product.name,
                price=price,
                url=url,
                in_stock=True,  # gelistete Händlerangebote gelten als bestellbar
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=product_ean,
                merchant=merchant[:60],
            )
        )

    log.info("Geizhals: %d Angebote extrahiert.", len(offers))
    return offers
