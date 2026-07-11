#!/usr/bin/env python3
"""
Wine Stock Watcher
Surveille une liste de bouteilles (config.yaml) sur des fiches produit Shopify
(Peak Wines et compatibles) et envoie un e-mail uniquement si un changement
pertinent est détecté (stock, disparition, prix).

Aucune IA / aucun raisonnement : on lit le texte affiché tel quel.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Ordre important : on teste le plus spécifique en premier.
STATUS_PATTERNS = [
    ("Sold out", re.compile(r"\bsold out\b", re.IGNORECASE)),
    ("Low stock", re.compile(r"\blow stock\b", re.IGNORECASE)),
    ("In stock", re.compile(r"\bin stock\b", re.IGNORECASE)),
]

PRICE_PATTERN = re.compile(r"Sale price\s*€\s*([\d]+[.,]\d{2})")


def fetch_bottle(name: str, url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # On cherche le texte visible dans la zone "achat" (autour du bouton
    # add-to-cart) pour limiter les faux positifs, avec repli sur toute la page.
    form = soup.find("form", attrs={"action": re.compile(r"/cart/add")})
    scope_text = form.get_text(" ", strip=True) if form else soup.get_text(" ", strip=True)

    status = "Unknown"
    for label, pattern in STATUS_PATTERNS:
        if pattern.search(scope_text):
            status = label
            break

    price = None
    price_match = PRICE_PATTERN.search(soup.get_text(" ", strip=True))
    if price_match:
        price = price_match.group(1).replace(",", ".")
    else:
        meta_price = soup.find("meta", property="product:price:amount")
        if meta_price and meta_price.get("content"):
            price = meta_price["content"].replace(",", ".")

    return {"name": name, "url": url, "status": status, "price": price}


def load_config() -> list:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("bottles", [])


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def diff(previous: dict | None, current: dict) -> list:
    """Retourne une liste de messages de changement, vide si rien à signaler."""
    if previous is None:
        # Première exécution pour cette bouteille : on enregistre sans alerter.
        return []

    messages = []
    prev_status = previous.get("status")
    cur_status = current["status"]

    if prev_status != cur_status:
        if cur_status == "Low stock" and prev_status == "In stock":
            messages.append(f"⚠️ {current['name']} est passé en LOW STOCK.")
        elif cur_status == "Sold out":
            messages.append(f"❌ {current['name']} est en RUPTURE DE STOCK.")
        elif cur_status == "In stock" and prev_status in ("Low stock", "Sold out"):
            messages.append(f"✅ {current['name']} est DE NOUVEAU EN STOCK.")
        else:
            messages.append(
                f"ℹ️ {current['name']} : statut changé de '{prev_status}' à '{cur_status}'."
            )

    prev_price = previous.get("price")
    cur_price = current["price"]
    if prev_price is not None and cur_price is not None:
        try:
            if float(cur_price) < float(prev_price):
                messages.append(
                    f"💰 {current['name']} : baisse de prix de {prev_price}€ à {cur_price}€."
                )
        except ValueError:
            pass

    return messages


def send_discord_notification(body: str) -> None:
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    # Discord limite un message à 2000 caractères.
    content = body[:1900]
    resp = requests.post(webhook_url, json={"content": content}, timeout=15)
    resp.raise_for_status()


def main() -> int:
    bottles = load_config()
    state = load_state()

    all_messages = []

    for bottle in bottles:
        name, url = bottle["name"], bottle["url"]
        try:
            current = fetch_bottle(name, url)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERREUR] {name}: {exc}", file=sys.stderr)
            continue

        previous = state.get(name)
        messages = diff(previous, current)
        all_messages.extend(messages)

        state[name] = current
        print(f"{name}: {current['status']} ({current['price']}€)")

    save_state(state)

    if all_messages:
        body = "🍷 **Changement de stock détecté**\n\n" + "\n".join(all_messages)
        send_discord_notification(body)
        print(f"Notification Discord envoyée ({len(all_messages)} changement(s)).")
    else:
        print("Aucun changement à signaler.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
