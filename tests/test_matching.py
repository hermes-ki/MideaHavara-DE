"""Tests für den 'nur wirklich bestellbar'-Filter und Produktabgleich."""

from tracker.config import Config, Location, Product
from tracker.matching import haversine_km, is_buyable, matches_product
from tracker.models import (
    CHANNEL_ONLINE,
    CHANNEL_STORE,
    CONDITION_NEW,
    CONDITION_USED,
    Offer,
)


def make_config(allow_used: bool = True, max_price: float = 800.0) -> Config:
    return Config(
        products=[
            Product(
                name="Midea PortaSplit 12.000 BTU",
                eans=["4048164116478"],
                title_must_include=["portasplit"],
                title_must_exclude=[],
                max_price=max_price,
                allow_used=allow_used,
            )
        ],
        location=Location("74321", "Bietigheim-Bissingen", 48.9543, 9.1316, 25.0),
        sources={},
        stores={},
    )


def buyable(o: Offer, cfg: Config) -> bool:
    """Test-Hilfe: prüft ein Angebot gegen das (einzige) Config-Produkt."""
    return is_buyable(o, cfg.product, cfg.location)


def offer(**kw) -> Offer:
    base = dict(
        source="test",
        title="Midea PortaSplit 12000 BTU",
        price=699.0,
        url="https://example.com/x",
        in_stock=True,
        condition=CONDITION_NEW,
        channel=CHANNEL_ONLINE,
        ean="4048164116478",
    )
    base.update(kw)
    return Offer(**base)


def test_valid_offer_passes():
    assert buyable(offer(), make_config())


def test_rejects_over_price():
    assert not buyable(offer(price=899.0), make_config())


def test_rejects_out_of_stock():
    assert not buyable(offer(in_stock=False), make_config())


def test_rejects_wrong_ean():
    assert not buyable(offer(ean="0000000000000"), make_config())


def test_comfee_branded_product_matches_by_title():
    # Das Zielgerät IST Comfee-gebrandet -> "Midea Comfee PortaSplit" muss
    # per Titel matchen (kein comfee-Ausschluss).
    o = offer(ean=None, title="Midea Comfee PortaSplit Mobile", price=699.0)
    assert matches_product(o, make_config().product)
    assert buyable(o, make_config())


def test_comfee_branded_rejected_only_by_price():
    # Dasselbe Gerät über Budget -> nur der Preisfilter lehnt ab, nicht der Titel.
    o = offer(ean=None, title="Midea Comfee PortaSplit Mobile", price=1599.0)
    assert matches_product(o, make_config().product)
    assert not buyable(o, make_config())


def test_non_portasplit_rejected_by_title():
    # Anderes Gerät ohne "portasplit" im Titel -> kein Match.
    o = offer(ean=None, title="Midea Klimaanlage Mobil 9000 BTU", price=499.0)
    assert not matches_product(o, make_config().product)


def test_used_allowed_when_configured():
    assert buyable(offer(condition=CONDITION_USED, price=650.0), make_config(allow_used=True))


def test_used_rejected_when_not_allowed():
    assert not buyable(offer(condition=CONDITION_USED), make_config(allow_used=False))


def test_store_within_radius_passes():
    o = offer(channel=CHANNEL_STORE, store_name="Ludwigsburg", distance_km=12.0)
    assert buyable(o, make_config())


def test_store_outside_radius_rejected():
    o = offer(channel=CHANNEL_STORE, store_name="Karlsruhe", distance_km=60.0)
    assert not buyable(o, make_config())


def test_store_without_distance_rejected():
    o = offer(channel=CHANNEL_STORE, store_name="Unbekannt", distance_km=None)
    assert not buyable(o, make_config())


def test_haversine_known_distance():
    # Bietigheim-Bissingen -> Ludwigsburg ca. 7-9 km.
    d = haversine_km(48.9543, 9.1316, 48.8974, 9.1916)
    assert 5 < d < 12
