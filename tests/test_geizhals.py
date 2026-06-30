"""Tests für den Geizhals-Bestpreis-Parser (kein JSON-LD, og:title/gh_price)."""

from tracker.sources.geizhals import _de_price, _parse_best_offer

# Realer Ausschnitt: Bestpreis im og:title (deutsches Format mit &nbsp;).
OG_TITLE = (
    '<meta property="og:title" '
    'content="Midea Comfee PortaSplit ab €&nbsp;1.799,00 (2026) | Preisvergleich Geizhals">'
)

# Bestpreis < 800 im og:title – soll als Treffer extrahiert werden.
OG_TITLE_CHEAP = (
    '<meta property="og:title" '
    'content="Midea Comfee PortaSplit ab €&nbsp;749,00 (2026) | Preisvergleich Geizhals">'
)

# Kein og:title-Bestpreis -> Fallback auf die gh_price-Angebotszeilen.
GH_PRICE_ROWS = (
    '<span class="price"><span class="gh_price">€ 2.499,00</span></span>'
    '<span class="price"><span class="gh_price">€ 1.299,00</span></span>'
)


def test_de_price_with_and_without_thousands_dot():
    assert _de_price("1.799,00") == 1799.0
    assert _de_price("1799,00") == 1799.0
    assert _de_price("749,00") == 749.0


def test_parses_best_price_from_og_title():
    name, price = _parse_best_offer(OG_TITLE, "Fallback")
    assert name == "Midea Comfee PortaSplit"
    assert price == 1799.0


def test_parses_cheap_best_price():
    _, price = _parse_best_offer(OG_TITLE_CHEAP, "Fallback")
    assert price == 749.0


def test_falls_back_to_lowest_gh_price():
    name, price = _parse_best_offer(GH_PRICE_ROWS, "Fallback-Name")
    assert name == "Fallback-Name"  # kein og:title vorhanden
    assert price == 1299.0  # niedrigster gh_price


def test_no_price_returns_none():
    _, price = _parse_best_offer("<html><body>nichts</body></html>", "X")
    assert price is None
