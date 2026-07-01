"""Greensun-Germany-Adapter (JTL-Shop, Direktvertrieb für Midea-Produkte).

Klassischer JTL-Shop: i.d.R. strukturierte Produktdaten als schema.org
JSON-LD plus sichtbare Text-/Status-Marker im Seiten-Chrome (z.B. "Momentan
nicht verfügbar" bei Vorbestellern, "Sofort verfügbar" + Warenkorb-Button bei
echtem Bestand). Wir nutzen daher dieselbe konservative Kaufbarkeitsprüfung
wie bei den Baumärkten (``buyability.assess_buyability``): negative Marker
("nicht verfügbar", "ausverkauft" …) sind IMMER ein Veto.

Für das positive Signal gilt:
  * Mit JSON-LD: das strukturierte ``availability``-Feld (wie bei OBI/Bauhaus).
  * Ohne JSON-LD (Stand der Kalibrierung: manche Produktseiten dieses Shops
    liefern keins): der Warenkorb-Button. Verifiziert per Live-Vergleich
    zweier Produktseiten – der Button fehlt bei "Momentan nicht verfügbar"
    komplett und erscheint nur bei "Sofort verfügbar". Das ist spezifisch für
    DIESEN Shop kalibriert; bei OBI war ein bloßer Cart-Button NICHT
    verlässlich (Pseudo-InStoreOnly-Fall), hier aber schon, weil der Button
    serverseitig weggelassen statt nur deaktiviert wird. Vor dem produktiven
    Einsatz trotzdem per ``python -m tracker.inspect`` gegenkalibrieren.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..config import Config, Product
from ..models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .base import fetch_page, parse_price
from .buyability import ADD_TO_CART_SELECTORS, assess_buyability
from .jsonld import extract_products

log = logging.getLogger(__name__)

SOURCE = "greensun"
_LABEL = "Greensun Germany"

# Fallback, falls kein JSON-LD vorhanden ist: entweder microdata
# (itemprop="price" content="857.00") oder die sichtbare Preisangabe
# ("857,00 €", JTL-Standardtemplate).
_PRICE_BLOCK_RE = re.compile(
    r'itemprop="price"[^>]*content="([\d.]+)"'
    r'|[\"\'>]\s*(\d{1,3}(?:[.\s]\d{3})*,\d{2})\s*€',
    re.I,
)


def _html(url: str) -> str | None:
    html, how = fetch_page(url, wait_selector="script[type='application/ld+json']")
    if how == "blocked":
        log.info("Greensun: Bot-Wall nicht überwunden (geblockt).")
    return html


def _extract_fallback_price(html: str) -> float | None:
    m = _PRICE_BLOCK_RE.search(html)
    if not m:
        return None
    if m.group(1):
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return parse_price(m.group(2))


def _has_cart_button(html: str) -> bool:
    """Greensun-spezifisches Positiv-Signal ohne JSON-LD (siehe Modul-Docstring)."""
    soup = BeautifulSoup(html, "html.parser")
    return any(soup.select(sel) for sel in ADD_TO_CART_SELECTORS)


def fetch_offers(cfg: Config, product: Product) -> list[Offer]:
    url = product.url_for(SOURCE)
    if not url:
        log.info("Greensun: keine Produkt-URL für '%s' konfiguriert – übersprungen.", product.name)
        return []

    html = _html(url)
    if not html:
        return []

    product_ean = product.eans[0] if product.eans else None
    offers: list[Offer] = []

    products = extract_products(html)
    for prod in products:
        if prod["price"] is None:
            continue
        buyable, signals = assess_buyability(html, jsonld_in_stock=prod["in_stock"])
        log.info(
            "Greensun: availability=%s -> bestellbar=%s %s",
            prod.get("availability_raw"), buyable, signals,
        )
        offers.append(
            Offer(
                source=SOURCE,
                title=prod["title"] or product.name,
                price=prod["price"],
                url=url,
                in_stock=buyable,
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=prod["ean"] or product_ean,
                merchant=_LABEL,
            )
        )

    # Kein JSON-LD gefunden -> Preis per Regex, Kaufbarkeit über den
    # Warenkorb-Button als Ersatzsignal (siehe Docstring). Negativ-Marker
    # bleiben weiterhin ein Veto.
    if not products:
        price = _extract_fallback_price(html)
        if price is not None:
            cart = _has_cart_button(html)
            buyable, signals = assess_buyability(html, jsonld_in_stock=cart)
            log.info(
                "Greensun (Fallback ohne JSON-LD): cart_button=%s -> bestellbar=%s %s",
                cart, buyable, signals,
            )
            offers.append(
                Offer(
                    source=SOURCE,
                    title=product.name,
                    price=price,
                    url=url,
                    in_stock=buyable,
                    condition=CONDITION_NEW,
                    channel=CHANNEL_ONLINE,
                    ean=product_ean,
                    merchant=_LABEL,
                )
            )

    log.info("Greensun: %d Angebote extrahiert.", len(offers))
    return offers
