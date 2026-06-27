"""Tests für die JSON-LD-Extraktion und State/Diff-Logik."""

from tracker.sources.jsonld import extract_products
from tracker.state import diff_new
from tracker.models import Offer

PRODUCT_JSONLD = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Midea PortaSplit 12.000 BTU",
  "gtin13": "4048164116478",
  "offers": {
    "@type": "Offer",
    "price": "699.00",
    "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock"
  }
}
</script></head><body></body></html>
"""

OUT_OF_STOCK_JSONLD = PRODUCT_JSONLD.replace("InStock", "OutOfStock")

GRAPH_JSONLD = """
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"BreadcrumbList"},
  {"@type":"Product","name":"Midea PortaSplit","gtin":"4048164116478",
   "offers":{"@type":"AggregateOffer","lowPrice":"729.00","priceCurrency":"EUR",
   "availability":"InStock"}}
]}
</script>
"""


def test_extract_basic_product():
    products = extract_products(PRODUCT_JSONLD)
    assert len(products) == 1
    p = products[0]
    assert p["ean"] == "4048164116478"
    assert p["price"] == 699.0
    assert p["in_stock"] is True


def test_extract_out_of_stock():
    p = extract_products(OUT_OF_STOCK_JSONLD)[0]
    assert p["in_stock"] is False


def test_extract_from_graph_and_aggregate_offer():
    p = extract_products(GRAPH_JSONLD)[0]
    assert p["price"] == 729.0
    assert p["in_stock"] is True


def test_no_jsonld_returns_empty():
    assert extract_products("<html><body>nichts</body></html>") == []


def _offer(key_url: str) -> Offer:
    return Offer(source="s", title="t", price=699.0, url=key_url, in_stock=True)


def test_diff_reports_only_new():
    a = _offer("https://shop/a")
    b = _offer("https://shop/b")
    seen = {a.key()}
    new, current = diff_new([a, b], seen)
    assert [o.url for o in new] == ["https://shop/b"]
    assert current == {a.key(), b.key()}


def test_diff_no_new_when_all_seen():
    a = _offer("https://shop/a")
    new, current = diff_new([a], {a.key()})
    assert new == []
    assert current == {a.key()}
