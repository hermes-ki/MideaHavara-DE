"""Einstiegspunkt: Quellen abfragen, filtern, Diff bilden, benachrichtigen.

Aufruf:
    python -m tracker.run            # echter Lauf (sendet Push, schreibt State)
    python -m tracker.run --dry-run  # nur loggen, kein Versand, kein State-Write
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace

from .config import Config, Product, Secrets, load_config
from .matching import is_buyable
from .models import CHANNEL_ONLINE, CONDITION_NEW, Offer
from .notify import format_offers, send_telegram
from .sources import get_source
from .state import diff_new, load_seen, save_seen

log = logging.getLogger(__name__)


def collect_offers_for_product(cfg: Config, product: Product) -> list[Offer]:
    """Fragt alle aktivierten Quellen für EIN Produkt ab. Fehler pro Quelle isolieren."""
    all_offers: list[Offer] = []
    for name in cfg.enabled_sources():
        fn = get_source(name)
        if fn is None:
            log.warning("Unbekannte Quelle '%s' – übersprungen.", name)
            continue
        try:
            offers = fn(cfg, product)
            # Angebote mit dem konfigurierten Produktnamen taggen (Gruppierung).
            all_offers.extend(replace(o, product_name=product.name) for o in offers)
        except Exception as exc:  # noqa: BLE001 - eine Quelle darf nicht den Lauf kippen
            log.error("Quelle '%s' (%s) fehlgeschlagen: %s", name, product.name, exc, exc_info=True)
    return all_offers


def collect_buyable(cfg: Config) -> list[Offer]:
    """Sammelt über die ganze Watchlist alle wirklich bestellbaren Angebote."""
    buyable: list[Offer] = []
    for product in cfg.products:
        offers = collect_offers_for_product(cfg, product)
        kept = [o for o in offers if is_buyable(o, product, cfg.location)]
        log.info("'%s': %d Angebote, davon %d wirklich bestellbar < %.0f €.",
                 product.name, len(offers), len(kept), product.max_price)
        buyable.extend(kept)
    return buyable


def run(dry_run: bool = False) -> int:
    cfg = load_config()
    secrets = Secrets.from_env()

    names = ", ".join(p.name for p in cfg.products)
    log.info("Starte Check für %d Produkt(e) [%s] (Quellen: %s)",
             len(cfg.products), names, ", ".join(cfg.enabled_sources()))

    buyable = collect_buyable(cfg)
    for o in buyable:
        log.info("  ✓ %s", o.describe())

    seen = load_seen()
    new_offers, current_keys = diff_new(buyable, seen)

    if new_offers:
        log.info("%d NEUE verfügbare Angebote -> Benachrichtigung.", len(new_offers))
        message = format_offers(new_offers)
        if dry_run:
            print("--- DRY RUN: Telegram-Nachricht ---")
            print(message)
        else:
            send_telegram(message, secrets)
    else:
        log.info("Keine neuen verfügbaren Angebote.")

    if not dry_run:
        save_seen(current_keys)
        log.info("State aktualisiert (%d verfügbare Angebote gemerkt).", len(current_keys))

    return 0


def run_demo() -> int:
    """Schickt einen einmaligen Beispiel-Alarm im echten Format (Funktionstest)."""
    cfg = load_config()
    secrets = Secrets.from_env()
    product = cfg.product
    demo = Offer(
        source="hornbach",
        title=f"{product.name} (BEISPIEL/Test)",
        price=699.0,
        url=product.url_for("hornbach")
        or "https://www.hornbach.de/p/klimasplitgeraet-midea-portasplit-12-000-btu-105-m-weiss/12356554/",
        in_stock=True,
        condition=CONDITION_NEW,
        channel=CHANNEL_ONLINE,
        ean=product.eans[0] if product.eans else None,
        merchant="Hornbach (Test-Alarm)",
        product_name=product.name,
    )
    message = "🔔 <b>TEST-ALARM</b> – so sieht eine echte Benachrichtigung aus:\n\n" + format_offers(
        [demo]
    )
    ok = send_telegram(message, secrets)
    log.info("Test-Alarm gesendet." if ok else "Test-Alarm fehlgeschlagen (Secrets prüfen).")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Midea PortaSplit Verfügbarkeits-Check")
    parser.add_argument("--dry-run", action="store_true", help="Nur loggen, nichts senden/schreiben")
    parser.add_argument("--demo", action="store_true", help="Einmaligen Beispiel-Alarm an Telegram senden")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-Logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.demo:
        return run_demo()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
