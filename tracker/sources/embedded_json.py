"""Extraktion von Angeboten aus eingebettetem JSON (SPA-Shops).

MediaMarkt/Saturn liefern kein `<script type="application/ld+json">`, betten
aber im Seiten-JSON einen schema.org-artigen Offer ein, dessen ``url`` die
Produkt-ID enthält. So lässt sich Preis + Verfügbarkeit eindeutig DEM
gesuchten Produkt zuordnen (statt versehentlich einem Empfehlungs-Artikel).

Beispiel (aus Live-Diagnose, Saturn):
    "price":2589.99,"priceCurrency":"EUR","itemCondition":".../NewCondition",
    "availability":"https://schema.org/InStock",
    "url":"https://www.saturn.de/de/product/_…-142245268.html"
→ Marketplace-Angebot zu 2589,99 € (fällt durch den <800-€-Filter raus).
"""

from __future__ import annotations

import re

from .jsonld import availability_in_stock


def extract_offers_for_product(html: str, product_id: str) -> list[dict]:
    """Findet eingebettete Offer-Blöcke, deren ``url`` die Produkt-ID enthält.

    Returns Liste von ``{price, availability_raw, in_stock}``. ``[^{}]`` hält
    die Suche innerhalb eines flachen Offer-Objekts (kein Übergreifen).
    """
    if not product_id:
        return []

    pattern = re.compile(
        r'"price"\s*:\s*"?(?P<price>\d+(?:\.\d+)?)"?'
        r'[^{}]{0,400}?"availability"\s*:\s*"(?P<avail>[^"]+)"'
        r'[^{}]{0,400}?"url"\s*:\s*"(?P<url>[^"]*' + re.escape(product_id) + r'[^"]*)"',
        re.DOTALL,
    )

    results: list[dict] = []
    seen: set[tuple[float, str]] = set()
    for m in pattern.finditer(html):
        try:
            price = float(m.group("price"))
        except ValueError:
            continue
        avail = m.group("avail")
        dedup = (price, avail)
        if dedup in seen:
            continue
        seen.add(dedup)
        results.append(
            {
                "price": price,
                "availability_raw": avail,
                "in_stock": availability_in_stock(avail),
            }
        )
    return results
