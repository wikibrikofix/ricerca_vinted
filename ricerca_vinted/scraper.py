#!/usr/bin/env python3
"""
Scraper Vinted basato su browser reale (Playwright).

PERCHE' PLAYWRIGHT E NON L'API
------------------------------
L'endpoint JSON di Vinted (`/api/v2/catalog/items`) e' protetto da Datadome
(anti-bot). Le chiamate programmatiche dirette (requests/httpx e persino
curl-cffi con fingerprint TLS di Chrome) ricevono una risposta 404/403 con una
pagina di errore mascherata, soprattutto da IP datacenter/hosting.

Un browser reale, invece, carica regolarmente le pagine del catalogo: esegue il
JavaScript, supera la sfida anti-bot e mostra gli annunci. Estraiamo quindi i
dati direttamente dal DOM.

DA DOVE VENGONO I DATI
----------------------
Ogni card annuncio nel catalogo espone un link `<a href="/items/ID">` con un
attributo `title` gia' strutturato, ad esempio:

    "Maglia Nike, Brand: Nike, Condizioni: Ottime, Taglia: M, 15.00 €, 16.45 €"

Da questa stringa ricaviamo titolo, marca, condizione, taglia, prezzo e prezzo
totale (con protezione acquisti). L'ID annuncio viene dall'URL.

NOTE LEGALI / USO RESPONSABILE
------------------------------
- Solo uso personale. Scraping automatizzato viola i ToS di Vinted.
- Non salvare PII (username, email, dati venditore).
- Usa un rate limiting cortese (default: pausa + jitter tra le pagine).
- Il layout puo' cambiare: se l'estrazione si svuota, aggiorna LABELS/selettori.
"""
from __future__ import annotations

import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from playwright.sync_api import sync_playwright

# User-agent di un Chrome desktop reale.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Etichette usate da Vinted nell'attributo `title` della card.
# Dipendono dalla lingua del dominio: qui per vinted.it (italiano).
# Per altri domini aggiorna queste stringhe (es. FR: "Marque:", "État:", "Taille:").
LABELS = {
    "brand": "Brand:",
    "condition": "Condizioni:",
    "size": "Taglia:",
}

# Categorie utili (secondo livello) del dominio .it.
CATEGORIES = {
    "computer": "2994",  # Elettronica > Computer e informatica
}

_PRICE_RE = re.compile(r"(\d+[.,]\d{2})\s*€")
_ITEM_ID_RE = re.compile(r"/items/(\d+)")


@dataclass
class Item:
    """Un annuncio Vinted estratto dal catalogo."""
    id: str
    title: Optional[str] = None
    brand: Optional[str] = None
    condition: Optional[str] = None
    size: Optional[str] = None
    price: Optional[float] = None
    total_price: Optional[float] = None
    url: Optional[str] = None
    # popolati da fetch_details()
    description: Optional[str] = None
    favourites: Optional[int] = None
    seller_last_seen: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("extra", None)
        return d


def _norm_price(s: str) -> float:
    """Converte '1.234,56' o '15.00' in float."""
    if "," in s:
        # formato europeo: punto = migliaia, virgola = decimali
        return float(s.replace(".", "").replace(",", "."))
    return float(s)


def parse_title(raw: str, labels: dict = LABELS) -> dict:
    """Estrae i campi strutturati dall'attributo `title` di una card."""
    if not raw:
        return {}
    parts = [p.strip() for p in raw.split(",")]
    out = {
        "title": parts[0] if parts else None,
        "brand": None,
        "condition": None,
        "size": None,
    }
    for p in parts:
        if p.startswith(labels["brand"]):
            out["brand"] = p[len(labels["brand"]):].strip()
        elif p.startswith(labels["condition"]):
            out["condition"] = p[len(labels["condition"]):].strip()
        elif p.startswith(labels["size"]):
            out["size"] = p[len(labels["size"]):].strip()
    prices = _PRICE_RE.findall(raw)
    if prices:
        out["price"] = _norm_price(prices[0])
    if len(prices) > 1:
        out["total_price"] = _norm_price(prices[1])
    return out


class VintedScraper:
    """
    Scraper del catalogo Vinted tramite Playwright.

    Esempio:
        scraper = VintedScraper(base="https://www.vinted.it")
        items = scraper.search("nas synology", pages=2, catalog="2994")
        for it in items:
            print(it.title, it.price)
    """

    def __init__(
        self,
        base: str = "https://www.vinted.it",
        locale: str = "it-IT",
        user_agent: str = USER_AGENT,
        labels: dict = None,
        headless: bool = True,
        pause: float = 1.5,
        scrolls: int = 4,
    ):
        self.base = base.rstrip("/")
        self.locale = locale
        self.user_agent = user_agent
        self.labels = labels or LABELS
        self.headless = headless
        self.pause = pause
        self.scrolls = scrolls

    def search(
        self,
        query: str,
        pages: int = 2,
        catalog: Optional[str] = None,
        verbose: bool = True,
    ) -> list[Item]:
        """Cerca annunci e restituisce una lista di Item deduplicati."""
        cat_q = f"&catalog[]={catalog}" if catalog else ""
        results: dict[str, Item] = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless, args=["--no-sandbox"]
            )
            ctx = browser.new_context(
                locale=self.locale,
                user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
            )
            page = ctx.new_page()
            try:
                for pagina in range(1, pages + 1):
                    q = query.replace(" ", "%20")
                    url = f"{self.base}/catalog?search_text={q}{cat_q}&page={pagina}"
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(1500)
                    # scroll per innescare il lazy-load
                    for _ in range(self.scrolls):
                        page.mouse.wheel(0, 4000)
                        page.wait_for_timeout(500)

                    links = page.locator('a[href*="/items/"]')
                    n = links.count()
                    nuovi = 0
                    for i in range(n):
                        el = links.nth(i)
                        href = el.get_attribute("href") or ""
                        m = _ITEM_ID_RE.search(href)
                        if not m:
                            continue
                        item_id = m.group(1)
                        if item_id in results:
                            continue
                        title_attr = el.get_attribute("title")
                        if not title_attr:
                            continue
                        parsed = parse_title(title_attr, self.labels)
                        results[item_id] = Item(
                            id=item_id,
                            url=self.base + href.split("?")[0],
                            **parsed,
                        )
                        nuovi += 1
                    if verbose:
                        print(f"  pagina {pagina}: {nuovi} nuovi annunci",
                              file=sys.stderr)
                    if nuovi == 0:
                        break
                    time.sleep(self.pause + random.uniform(0, 1.0))  # jitter
            finally:
                browser.close()
        return list(results.values())

    def fetch_details(self, items, verbose: bool = True):
        """
        Apre la pagina di ogni annuncio e ne arricchisce i dati con la
        DESCRIZIONE (e alcuni dettagli: condizione precisa, n. preferiti,
        ultimo accesso venditore).

        ATTENZIONE: apre una pagina per annuncio -> molto piu' lento della
        search. Usalo su un sottoinsieme gia' filtrato.

        Accetta un singolo Item o una lista di Item; ritorna la lista arricchita.
        """
        single = isinstance(items, Item)
        lst = [items] if single else list(items)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            ctx = browser.new_context(
                locale=self.locale, user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
            )
            page = ctx.new_page()
            try:
                for i, it in enumerate(lst, 1):
                    if not it.url:
                        continue
                    try:
                        page.goto(it.url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(1200)
                        it.description = self._safe_text(page, '[itemprop="description"]')
                        # condizione precisa dalla pagina (piu' affidabile della card)
                        status = self._safe_text(page, '[data-testid="item-attributes-status"]')
                        if status:
                            it.condition = status.replace("Condizioni", "").strip() or it.condition
                        fav = self._safe_text(page, '[data-testid="favourite-button"]')
                        if fav:
                            m = re.search(r"\d+", fav)
                            it.favourites = int(m.group()) if m else it.favourites
                        it.seller_last_seen = self._safe_text(
                            page, '[data-testid="seller-last-logged-in"]')
                    except Exception as e:
                        it.extra["detail_error"] = str(e)[:120]
                    if verbose:
                        print(f"  dettaglio {i}/{len(lst)}: {str(it.title)[:40]}",
                              file=sys.stderr)
                    time.sleep(self.pause + random.uniform(0, 0.8))  # rate limiting
            finally:
                browser.close()
        return lst[0] if single else lst

    @staticmethod
    def _safe_text(page, selector: str) -> Optional[str]:
        try:
            return page.locator(selector).first.inner_text(timeout=1500).strip()
        except Exception:
            return None
