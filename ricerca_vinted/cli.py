#!/usr/bin/env python3
"""CLI per lo scraper Vinted."""
from __future__ import annotations

import argparse
import sys

from .scraper import VintedScraper, CATEGORIES
from .analysis import items_to_dataframe, summarize
from .quality import analyze_item


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="ricerca-vinted",
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
    ap.add_argument("--order",
                    help="ordinamento risultati (es. 'newest_first' = più recenti)")
    ap.add_argument("--csv", help="salva i dati grezzi in un file CSV")
    ap.add_argument("--dettagli", action="store_true",
                    help="apre le pagine dei prodotti per leggere la DESCRIZIONE "
                         "e stimare la qualita' (piu' lento)")
    ap.add_argument("--top", type=int, default=15,
                    help="con --dettagli: quanti annunci (piu' economici) approfondire")
    ap.add_argument("--show", action="store_true",
                    help="mostra il browser (non headless) per debug")
    ap.add_argument("--locale", default="it-IT", help="locale del browser")
    return ap


def _print_quality(items):
    print("\n=== ANALISI QUALITA' (titolo + descrizione) ===")
    for it in items:
        rep = analyze_item(it)
        price = f"{it.price:.2f}€" if it.price is not None else "  -  "
        print(f"\n[{rep.verdict} · punteggio {rep.score}/100] {price} — {str(it.title)[:50]}")
        print(f"  {it.url}")
        if it.condition:
            print(f"  condizione dichiarata: {it.condition}")
        if rep.positives:
            print(f"  + segnali positivi: {', '.join(sorted(set(rep.positives))[:4])}")
        if rep.negatives:
            print(f"  - segnali negativi: {', '.join(sorted(set(rep.negatives))[:4])}")
        for k, v in rep.seller_notes.items():
            print(f"  · {k.replace('_',' ')}: {v[0]}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    catalog = CATEGORIES.get(args.catalog, args.catalog) if args.catalog else None

    print(f"Ricerca: {args.query!r} su {args.base}"
          + (f" [catalog={catalog}]" if catalog else ""), file=sys.stderr)

    scraper = VintedScraper(
        base=args.base, locale=args.locale,
        headless=not args.show, pause=args.pause,
    )
    items = scraper.search(args.query, pages=args.pages, catalog=catalog, order=args.order)
    df = items_to_dataframe(items)

    if args.csv and not df.empty:
        df.to_csv(args.csv, index=False)
        print(f"Dati salvati in {args.csv}", file=sys.stderr)

    print(summarize(df))

    if args.dettagli and items:
        # approfondisci solo un sottoinsieme (i piu' economici) per rate limiting
        con_prezzo = [it for it in items if it.price is not None]
        con_prezzo.sort(key=lambda x: x.price)
        target = con_prezzo[:args.top] if con_prezzo else items[:args.top]
        print(f"\nLettura descrizioni di {len(target)} annunci...", file=sys.stderr)
        scraper.fetch_details(target)
        _print_quality(target)
        if args.csv:
            items_to_dataframe(target).to_csv(
                args.csv.replace(".csv", "_dettagli.csv"), index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
