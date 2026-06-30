"""Geizhals-Adapter (Preisvergleich).

Geizhals bettet (anders als die meisten Shops) KEIN schema.org-JSON-LD ein.
Daher lesen wir den Bestpreis aus dem ``og:title`` ("… ab €&nbsp;X,XX …") –
Geizhals' offiziell berechneter günstigster Preis über alle gelisteten Shops –
und als Fallback den niedrigsten Preis aus den ``gh_price``-Angebotszeilen.
Sollte Geizhals doch einmal JSON-LD liefern, wird das bevorzugt. Bei Block
(403) greift der Browser-Fallback.
"""

from __future__ import annotations

import logging
import re

from ..config import Config, Product
from ..models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .base import fetch_page
from .jsonld import extract_products

log = logging.getLogger(__name__)

SOURCE = "geizhals"

# "Midea Comfee PortaSplit ab €&nbsp;1.799,00 (2026) | Preisvergleich …"
_OG_TITLE_RE = re.compile(r'property="og:title"\s+content="([^"]+)"', re.I)
# Bestpreis im og:title bzw. Angebotszeilen-Preise (deutsches Format).
_AB_PRICE_RE = re.compile(r"ab\s+€\s*([\d.\s ]*\d,\d{2})", re.I)
_GH_PRICE_RE = re.compile(r'class="gh_price"[^>]*>\s*€\s*([\d.\s ]*\d,\d{2})')


def _de_price(text: str) -> float | None:
    """Deutsches Preisformat -> float ('1.799,00' und auch '1799,00')."""
    cleaned = text.replace(" ", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_best_offer(html: str, fallback_name: str) -> tuple[str, float | None]:
    """Produktname + Geizhals-Bestpreis aus dem HTML (ohne JSON-LD)."""
    name = fallback_name
    title_txt = ""
    m = _OG_TITLE_RE.search(html)
    if m:
        title_txt = m.group(1).replace("&nbsp;", " ").replace(" ", " ")
        # Name = alles vor " ab €".
        name = re.split(r"\s+ab\s+€", title_txt, maxsplit=1)[0].strip() or fallback_name

    price = None
    pm = _AB_PRICE_RE.search(title_txt)
    if pm:
        price = _de_price(pm.group(1))
    if price is None:
        prices = [p for p in (_de_price(x) for x in _GH_PRICE_RE.findall(html)) if p is not None]
        if prices:
            price = min(prices)
    return name, price


def fetch_offers(cfg: Config, product: Product) -> list[Offer]:
    url = product.url_for(SOURCE)
    if not url:
        log.info("Geizhals: keine Produkt-URL für '%s' konfiguriert – übersprungen.", product.name)
        return []

    html, how = fetch_page(url, wait_selector="body")
    if how == "blocked" or not html:
        log.info("Geizhals: Seite nicht erreichbar (geblockt).")
        return []

    offers: list[Offer] = []

    # 1) Falls Geizhals doch JSON-LD liefert: bevorzugt nutzen (mit EAN/Titel).
    #    Kein Fallback-Stempel der Produkt-EAN -> der Titelabgleich entscheidet.
    for prod in extract_products(html):
        if prod["price"] is None:
            continue
        offers.append(
            Offer(
                source=SOURCE,
                title=prod["title"] or product.name,
                price=prod["price"],
                url=url,
                in_stock=prod["in_stock"],
                condition=CONDITION_NEW,
                channel=CHANNEL_ONLINE,
                ean=prod["ean"],
                merchant="Geizhals (Bestpreis)",
            )
        )

    # 2) Sonst: Bestpreis aus og:title / gh_price-Zeilen. Ein gelistetes Angebot
    #    mit Preis gilt als bestellbar; der strikte Preis-/Titelfilter
    #    (matching.is_buyable) entscheidet anschließend endgültig.
    if not offers:
        name, price = _parse_best_offer(html, product.name)
        if price is not None:
            offers.append(
                Offer(
                    source=SOURCE,
                    title=name,
                    price=price,
                    url=url,
                    in_stock=True,
                    condition=CONDITION_NEW,
                    channel=CHANNEL_ONLINE,
                    ean=None,  # Geizhals zeigt hier keine EAN → Titelabgleich greift
                    merchant="Geizhals (Bestpreis)",
                )
            )

    log.info("Geizhals: %d Angebote extrahiert.", len(offers))
    return offers
