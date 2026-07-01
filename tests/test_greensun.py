"""Tests für den Greensun-Adapter (JTL-Shop): JSON-LD-Pfad + Preis-Fallback."""

from tracker.config import Config, Location, Product
from tracker.sources import greensun

URL = "https://www.greensun-germany.com/MIDEA-PortaSplit-35-kW-..."

# Realer Ausschnitt (Fetch vom 01.07.2026): kein JSON-LD gefunden, sichtbarer
# Preis "857,00 €" plus "Momentan nicht verfügbar" (Vorbesteller).
NO_JSONLD_OUT_OF_STOCK = """
<html><body>
<span class="price">857,00 €</span>
<div class="availability">Momentan nicht verfügbar (Vorbesteller)</div>
</body></html>
"""

WITH_JSONLD_IN_STOCK = """
<script type="application/ld+json">
{"@type":"Product","name":"Midea PortaSplit 3,5 kW","gtin13":"4048164116478",
 "offers":{"@type":"Offer","price":"857.00","priceCurrency":"EUR",
 "availability":"https://schema.org/InStock"}}
</script>
<body><button id="add-to-cart-button">In den Warenkorb</button></body>
"""


def _cfg() -> Config:
    return Config(
        products=[
            Product(
                name="Midea PortaSplit 12.000 BTU",
                eans=["4048164116478"],
                title_must_include=["portasplit"],
                title_must_exclude=[],
                max_price=1000.0,
                allow_used=True,
                urls={"greensun": URL},
            )
        ],
        location=Location("74321", "Bietigheim-Bissingen", 48.9543, 9.1316, 25.0),
        sources={"greensun": True},
    )


def test_no_jsonld_extracts_price_but_never_buyable(monkeypatch):
    monkeypatch.setattr(greensun, "_html", lambda url: NO_JSONLD_OUT_OF_STOCK)
    cfg = _cfg()
    offers = greensun.fetch_offers(cfg, cfg.product)
    assert len(offers) == 1
    o = offers[0]
    assert o.price == 857.0
    # Kein strukturiertes InStock -> NIE bestellbar, auch ohne Negativ-Marker-Check.
    assert o.in_stock is False


def test_jsonld_instock_is_buyable(monkeypatch):
    monkeypatch.setattr(greensun, "_html", lambda url: WITH_JSONLD_IN_STOCK)
    cfg = _cfg()
    offers = greensun.fetch_offers(cfg, cfg.product)

    assert len(offers) == 1
    o = offers[0]
    assert o.price == 857.0
    assert o.ean == "4048164116478"
    assert o.in_stock is True


def test_no_url_configured_returns_empty():
    cfg = _cfg()
    cfg.products[0].urls = {}
    assert greensun.fetch_offers(cfg, cfg.product) == []


def test_no_html_returns_empty(monkeypatch):
    monkeypatch.setattr(greensun, "_html", lambda url: None)
    cfg = _cfg()
    assert greensun.fetch_offers(cfg, cfg.product) == []
