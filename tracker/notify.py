"""Telegram-Benachrichtigung."""

from __future__ import annotations

import logging
import sys

import requests

from .config import Secrets
from .models import Offer

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = 20


def send_telegram(text: str, secrets: Secrets) -> bool:
    """Sendet eine Nachricht. Gibt True bei Erfolg zurück."""
    if not secrets.telegram_configured:
        log.warning("Telegram nicht konfiguriert (Token/Chat-ID fehlen) – überspringe Versand.")
        return False
    url = TELEGRAM_API.format(token=secrets.telegram_bot_token)
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": secrets.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Telegram-Versand fehlgeschlagen: %s", exc)
        return False
    return True


def format_offers(product_name: str, offers: list[Offer]) -> str:
    """Baut eine kompakte HTML-Nachricht für eine Liste neuer Angebote."""
    n = len(offers)
    header = f"🟢 <b>{product_name}</b> verfügbar! ({n} neue{'s' if n == 1 else ''} Angebot{'e' if n != 1 else ''})"
    lines = [header, ""]
    for o in sorted(offers, key=lambda x: x.price):
        cond = "Neu" if o.condition == "new" else "Gebraucht"
        where = o.merchant or o.source.capitalize()
        loc = ""
        if o.channel == "store" and o.store_name:
            dist = f", ~{o.distance_km:.0f} km" if o.distance_km is not None else ""
            loc = f" 🏬 Filiale {o.store_name}{dist}"
        lines.append(f"• <b>{o.price:.2f} €</b> – {where} [{cond}]{loc}")
        lines.append(f"  <a href=\"{o.url}\">Zum Angebot</a>")
    return "\n".join(lines)


def _self_test() -> int:
    """`python -m tracker.notify --test` schickt eine Testnachricht."""
    logging.basicConfig(level=logging.INFO)
    secrets = Secrets.from_env()
    ok = send_telegram(
        "✅ Testnachricht vom Midea PortaSplit Tracker – Benachrichtigungen funktionieren.",
        secrets,
    )
    print("Gesendet." if ok else "Fehlgeschlagen (siehe Log / Secrets prüfen).")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--test" in sys.argv:
        raise SystemExit(_self_test())
    print("Nutze: python -m tracker.notify --test")
