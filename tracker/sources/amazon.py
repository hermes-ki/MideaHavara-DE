"""Amazon.de-Adapter inkl. Warehouse (gebrauchte Artikel).

Amazon hat starken Anti-Bot-Schutz und kein verlässliches JSON-LD. Daher
best effort: Produktseite (Neu-Preis/Verfügbarkeit) plus optionale
Offer-Listing-Seite für Warehouse-/Gebraucht-Angebote. Bei Block greift der
Browser-Fallback; gelingt nichts, liefert der Adapter eine leere Liste, ohne
den Gesamtlauf zu stören.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..config import Config, Product
from ..models import CHANNEL_ONLINE, CONDITION_NEW, CONDITION_USED, Offer
from .base import fetch_page, parse_price

log = logging.getLogger(__name__)

SOURCE = "amazon"

_IN_STOCK_HINTS = ("auf lager", "in stock", "lieferbar", "jetzt kaufen", "in den einkaufswagen")
_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")


def _html(url: str) -> str | None:
    html, how = fetch_page(url, wait_selector="#productTitle")
    if how == "blocked":
        log.info("Amazon: Bot-Wall/Captcha nicht überwunden (geblockt).")
    return html


def _asin(url: str) -> str | None:
    m = _ASIN_RE.search(url)
    return m.group(1) if m else None


def _parse_buybox(product: Product, html: str, url: str) -> list[Offer]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("#productTitle")
    title = title_el.get_text(strip=True) if title_el else product.name

    price = None
    for sel in ("#corePrice_feature_div .a-offscreen", "span.a-price span.a-offscreen", "#priceblock_ourprice"):
        el = soup.select_one(sel)
        if el:
            price = parse_price(el.get_text(strip=True))
            if price:
                break
    if price is None:
        return []

    avail_el = soup.select_one("#availability")
    avail_text = (avail_el.get_text(" ", strip=True).lower() if avail_el else "")
    in_stock = any(h in avail_text for h in _IN_STOCK_HINTS) or bool(soup.select_one("#add-to-cart-button"))

    return [
        Offer(
            source=SOURCE,
            title=title,
            price=price,
            url=url,
            in_stock=in_stock,
            condition=CONDITION_NEW,
            channel=CHANNEL_ONLINE,
            ean=product.eans[0] if product.eans else None,
            merchant="Amazon.de",
        )
    ]


def _parse_warehouse(product: Product, asin: str) -> list[Offer]:
    """Gebraucht-/Warehouse-Angebote aus der Offer-Listing-Seite."""
    if not product.allow_used:
        return []
    url = f"https://www.amazon.de/gp/offer-listing/{asin}/ref=olp_f_usedLikeNew?f_used=true"
    html = _html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    for row in soup.select("#aod-offer, .olpOffer, [id^='aod-offer']"):
        price_el = row.select_one(".a-offscreen, .olpOfferPrice")
        if not price_el:
            continue
        price = parse_price(price_el.get_text(strip=True))
        if price is None:
            continue
        cond_el = row.select_one("#aod-offer-heading, .olpCondition, [class*='condition']")
        cond_text = cond_el.get_text(" ", strip=True) if cond_el else "Gebraucht"
        offers.append(
            Offer(
                source=SOURCE,
                title=product.name,
                price=price,
                url=f"https://www.amazon.de/dp/{asin}",
                in_stock=True,
                condition=CONDITION_USED,
                channel=CHANNEL_ONLINE,
                ean=product.eans[0] if product.eans else None,
                merchant=f"Amazon Warehouse ({cond_text[:40]})",
            )
        )
    return offers


def fetch_offers(cfg: Config, product: Product) -> list[Offer]:
    url = product.url_for(SOURCE)
    if not url:
        log.info("Amazon: keine Produkt-URL für '%s' konfiguriert – übersprungen.", product.name)
        return []

    offers: list[Offer] = []
    html = _html(url)
    if html:
        offers.extend(_parse_buybox(product, html, url))

    asin = _asin(url)
    if asin:
        offers.extend(_parse_warehouse(product, asin))

    log.info("Amazon: %d Angebote extrahiert.", len(offers))
    return offers
