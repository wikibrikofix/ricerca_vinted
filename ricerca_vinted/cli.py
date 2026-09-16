#!/usr/bin/env python3
"""CLI per lo scraper Vinted."""
from __future__ import annotations

import argparse
import sys

from .scraper import VintedScraper, CATEGORIES
from .analysis import items_to_dataframe, summarize


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="vinted-scraper",
        description="Cerca e analizza annunci Vinted tramite browser reale (Playwright).",
    )
    ap.add_argument("query", help="testo di ricerca (es. 'nas synology')")
    ap.add_argument("--base", default="https://www.vinted.it",
                    help="dominio Vinted (default: vinted.it)")
    ap.add_argument("--pages", type=int, default=2, help="numero di pagine (default: 2)")
    ap.add_argument("--catalog",
                    help="ID categoria Vinted, oppure alias. "
                         f"Alias noti: {', '.join(CATEGORIES)} "
                         "(es. 'computer' = Elettronica>Computer, id 2994)")
    ap.add_argument("--pause", type=float, default=1.5,
                    help="secondi di pausa tra le pagine (default: 1.5, + jitter)")
    ap.add_argument("--csv", help="salva i dati grezzi in un file CSV")
    ap.add_argument("--show", action="store_true",
                    help="mostra il browser (non headless) per debug")
    ap.add_argument("--locale", default="it-IT", help="locale del browser")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # risolvi alias categoria
    catalog = CATEGORIES.get(args.catalog, args.catalog) if args.catalog else None

    print(f"Ricerca: {args.query!r} su {args.base}"
          + (f" [catalog={catalog}]" if catalog else ""), file=sys.stderr)

    scraper = VintedScraper(
        base=args.base,
        locale=args.locale,
        headless=not args.show,
        pause=args.pause,
    )
    items = scraper.search(args.query, pages=args.pages, catalog=catalog)
    df = items_to_dataframe(items)

    if args.csv and not df.empty:
        df.to_csv(args.csv, index=False)
        print(f"Dati salvati in {args.csv}", file=sys.stderr)

    print(summarize(df))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
