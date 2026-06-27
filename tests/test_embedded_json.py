"""Tests für den Embedded-JSON-Parser (MediaMarkt/Saturn-Plattform)."""

from tracker.sources.embedded_json import extract_offers_for_product

# Realer Ausschnitt (Saturn-Diagnose): Marketplace-Angebot zu 2589,99 €,
# an die Produkt-ID 142245268 gekoppelt.
SATURN_EMBEDDED = (
    '{"@type":"Offer","price":2589.99,"priceCurrency":"EUR",'
    '"itemCondition":"https://schema.org/NewCondition",'
    '"availability":"https://schema.org/InStock",'
    '"url":"https://www.saturn.de/de/product/_midea-porta-split-142245268.html"}'
)

# Hypothetischer Direkt-Treffer < 800 € am selben Listing.
DIRECT_DEAL = (
    '{"price":"699.00","availability":"https://schema.org/InStock",'
    '"url":"https://www.mediamarkt.de/de/product/_x-142245268.html"}'
)

# Anderes Produkt (Empfehlung) – darf NICHT matchen.
OTHER_PRODUCT = (
    '{"price":499.0,"availability":"InStock",'
    '"url":"https://www.saturn.de/de/product/_anderes-999999.html"}'
)


def test_extracts_offer_for_product_id():
    offers = extract_offers_for_product(SATURN_EMBEDDED, "142245268")
    assert len(offers) == 1
    assert offers[0]["price"] == 2589.99
    assert offers[0]["in_stock"] is True


def test_ignores_other_products():
    assert extract_offers_for_product(OTHER_PRODUCT, "142245268") == []


def test_parses_direct_deal_price():
    offers = extract_offers_for_product(DIRECT_DEAL, "142245268")
    assert offers[0]["price"] == 699.0
    assert offers[0]["in_stock"] is True


def test_no_product_id_returns_empty():
    assert extract_offers_for_product(SATURN_EMBEDDED, "") == []
