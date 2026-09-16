"""Utility di analisi dei risultati Vinted con pandas."""
from __future__ import annotations

import pandas as pd

from .scraper import Item


def items_to_dataframe(items: list[Item]) -> pd.DataFrame:
    """Converte una lista di Item in un DataFrame pandas."""
    df = pd.DataFrame([it.to_dict() for it in items])
    if not df.empty:
        df = df.drop_duplicates(subset="id")
        for col in ("price", "total_price"):
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def summarize(df: pd.DataFrame) -> str:
    """Ritorna un riepilogo testuale (prezzi, condizioni, brand, top economici)."""
    if df.empty:
        return "Nessun annuncio trovato."
    out = [f"=== ANALISI SU {len(df)} ANNUNCI ==="]

    prices = df["price"].dropna() if "price" in df else pd.Series(dtype=float)
    if not prices.empty:
        out += [
            "\nPREZZO (€):",
            f"  medio    : {prices.mean():.2f}",
            f"  mediano  : {prices.median():.2f}",
            f"  minimo   : {prices.min():.2f}",
            f"  massimo  : {prices.max():.2f}",
            f"  dev.std  : {prices.std():.2f}",
        ]
    if "condition" in df:
        out.append("\nCONDIZIONE:")
        out.append(df["condition"].value_counts(dropna=True).to_string())
    if "brand" in df:
        out.append("\nTOP 5 BRAND:")
        out.append(df["brand"].value_counts(dropna=True).head().to_string())

    if "price" in df:
        out.append("\n5 PIU' ECONOMICI:")
        eco = df.dropna(subset=["price"]).sort_values("price").head()
        for _, r in eco.iterrows():
            out.append(f"  {r['price']:.2f} € - {str(r['title'])[:45]} -> {r['url']}")
    return "\n".join(out)
