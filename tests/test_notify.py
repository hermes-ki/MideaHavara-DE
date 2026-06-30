"""Tests für die Telegram-Nachricht: HTML-Escaping + Produkt-Gruppierung."""

from tracker.models import CHANNEL_ONLINE, CHANNEL_STORE, CONDITION_NEW, CONDITION_USED, Offer
from tracker.notify import format_offers


def _offer(**kw) -> Offer:
    base = dict(
        source="obi",
        title="Midea PortaSplit",
        price=699.0,
        url="https://example.com/x",
        in_stock=True,
        condition=CONDITION_NEW,
        channel=CHANNEL_ONLINE,
        merchant="OBI",
        product_name="Midea PortaSplit 12.000 BTU",
    )
    base.update(kw)
    return Offer(**base)


def test_escapes_html_in_merchant_and_url():
    # Titel/Händler mit Sonderzeichen dürfen die HTML-Nachricht NICHT zerstören.
    msg = format_offers([_offer(merchant="Müller & Sohn <Markt>", url="https://x/?a=1&b=2")])
    assert "Müller &amp; Sohn &lt;Markt&gt;" in msg
    assert "a=1&amp;b=2" in msg
    # Keine unescapeten gefährlichen Sequenzen im Fremdtext.
    assert "<Markt>" not in msg


def test_groups_offers_by_product():
    offers = [
        _offer(product_name="Gerät A", merchant="OBI", price=700),
        _offer(product_name="Gerät B", merchant="Idealo", price=500),
        _offer(product_name="Gerät A", merchant="Saturn", price=650),
    ]
    msg = format_offers(offers)
    assert "<b>Gerät A</b>" in msg
    assert "<b>Gerät B</b>" in msg
    # Gerät A hat 2 Angebote.
    assert "2 neue Angebote" in msg
    assert "1 neues Angebot" in msg


def test_store_offer_shows_distance():
    o = _offer(channel=CHANNEL_STORE, store_name="Ludwigsburg", distance_km=8.0, merchant="Saturn")
    msg = format_offers([o])
    assert "Filiale Ludwigsburg" in msg
    assert "~8 km" in msg


def test_used_condition_labeled():
    msg = format_offers([_offer(condition=CONDITION_USED, merchant="Amazon Warehouse")])
    assert "[Gebraucht]" in msg
