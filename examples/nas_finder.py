#!/usr/bin/env python3
"""
Esempio: ricerca NAS su Vinted e filtro per modelli 2-bay con requisiti specifici.

Riproduce il flusso usato per scegliere un NAS 2-bay con:
  - RAID 1
  - backup/replica su Amazon S3
  - accensione/spegnimento programmato
  - (bonus) file system Btrfs per l'integrita' del dato

Uso:
    python examples/nas_finder.py            # cerca su piu' marchi
    python examples/nas_finder.py --pages 3
"""
import argparse
import os
import re
import sys

# Assicura che venga usato il package locale (evita conflitti con eventuali
# pacchetti 'ricerca_vinted' installati via pip).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ricerca_vinted import VintedScraper
from ricerca_vinted.analysis import items_to_dataframe

# Marchi/query da cercare (categoria Elettronica>Computer = 2994)
QUERIES = ["nas synology", "nas qnap", "nas netgear", "asustor", "terramaster"]
CATALOG_COMPUTER = "2994"

# Modelli 2-bay con file system Btrfs (self-healing) -> integrita' del dato.
BTRFS_2BAY = re.compile(
    r"DS\s?218(play|\+|\b(?!j))|DS\s?220\+|DS\s?224\+|DS\s?720\+|DS\s?223\b|"  # Synology
    r"RN\s?3120|RN31200|RN\s?4220|RN42200|RN\s?102|RN\s?202|RN\s?212|ReadyNAS",  # Netgear ReadyNAS OS6
    re.I,
)
# Modelli 2-bay validi (RAID1 + S3) ma senza Btrfs (solo ext4).
EXT4_2BAY = re.compile(
    r"DS\s?213j|DS\s?214|DS\s?218j|DS\s?220j|"           # Synology
    r"TS-231|TS-251|TS-228A|"                             # QNAP
    r"AS110\d|AS3202|F2-2\d\d",                           # Asustor / TerraMaster
    re.I,
)


def classify(title: str) -> str:
    if BTRFS_2BAY.search(title):
        return "Btrfs (integrita' ✓)"
    if EXT4_2BAY.search(title):
        return "ext4 (RAID1+S3, no self-healing)"
    return ""


def main():
    ap = argparse.ArgumentParser(description="Trova NAS 2-bay idonei su Vinted")
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--max-price", type=float, default=None,
                    help="filtra sotto questo prezzo (€)")
    args = ap.parse_args()

    scraper = VintedScraper(base="https://www.vinted.it")
    all_items = []
    for q in QUERIES:
        print(f"# Ricerca: {q}")
        all_items += scraper.search(q, pages=args.pages, catalog=CATALOG_COMPUTER)

    df = items_to_dataframe(all_items)
    if df.empty:
        print("Nessun risultato.")
        return

    df["categoria_fs"] = df["title"].astype(str).apply(classify)
    idonei = df[df["categoria_fs"] != ""].copy()
    if args.max_price is not None and "price" in idonei:
        idonei = idonei[idonei["price"].fillna(1e9) <= args.max_price]
    idonei = idonei.sort_values(["categoria_fs", "price"])

    print(f"\n=== NAS 2-BAY IDONEI (RAID1 + S3): {len(idonei)} ===\n")
    for _, r in idonei.iterrows():
        price = f"{r['price']:.2f}€" if r.get("price") == r.get("price") else "  -  "
        print(f"[{r['categoria_fs']:<34}] {price:>8} | {str(r['title'])[:46]}")
        print(f"     {r['url']}")


if __name__ == "__main__":
    main()
